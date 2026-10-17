"""run_checkin: one daily check-in, end to end.

    audio -> transcribe -> SAFETY CHECK (rules + Gemini backup)
        flagged -> fixed EMERGENCY/URGENT text (no AI wording), SMS support person on emergency
        safe    -> extract metrics || memory reply (in parallel)
                   -> second safety pass on the extracted metrics (BP, heavy bleeding, ...)
                   -> speak the reply
    -> save the check-in (Tiger Data, when configured)

Every external call is wrapped: a failure degrades the reply, it never skips the safety check
and never turns into a 500 once we have a transcript.
"""
import base64
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from uuid import UUID

from app import db, notify, store
from app.ai import extract, memory, red_flags, stt, tts
from app.schemas import CheckinMetrics, CheckinRequest, CheckinResponse

log = logging.getLogger("tidewell.checkin")

FALLBACK_REPLY = (
    "Thank you for checking in with me today. I've noted how you're feeling. "
    "Is there anything else on your mind?"
)
_pool = ThreadPoolExecutor(max_workers=8)


class NoSpeech(ValueError):
    """Nothing to work with: no text, or the audio had no words in it."""


class TranscriptionFailed(RuntimeError):
    pass


def _as_uuid(patient_id: str) -> Optional[UUID]:
    try:
        return UUID(patient_id)
    except (ValueError, TypeError):
        return None


def _transcript(req: CheckinRequest) -> str:
    if req.text and req.text.strip():
        return req.text.strip()
    if not req.audio_base64:
        raise NoSpeech("send text or audio")
    try:
        audio = base64.b64decode(req.audio_base64)
    except ValueError as e:
        raise NoSpeech("audio_base64 is not valid base64") from e
    try:
        text = stt.transcribe(audio, req.audio_mime)
    except Exception as e:  # noqa: BLE001
        log.warning("transcription failed: %s: %s", type(e).__name__, e)
        raise TranscriptionFailed("could not transcribe the audio") from e
    if not text:
        raise NoSpeech("no speech heard in the recording")
    return text


def _extract(text: str) -> CheckinMetrics:
    try:
        return extract.extract_metrics(text)
    except Exception as e:  # noqa: BLE001
        log.warning("extraction failed (%s: %s); continuing without metrics", type(e).__name__, e)
        return CheckinMetrics()


def _reply(patient_id: str, text: str) -> str:
    try:
        return memory.chat(patient_id, text) or FALLBACK_REPLY
    except Exception as e:  # noqa: BLE001
        log.warning("reply failed (%s: %s); using fallback", type(e).__name__, e)
        return FALLBACK_REPLY


def _speak(text: str) -> Optional[str]:
    try:
        return base64.b64encode(tts.speak(text)).decode()
    except Exception as e:  # noqa: BLE001
        log.warning("text-to-speech failed (%s: %s); returning text only", type(e).__name__, e)
        return None


def _save(pid: Optional[UUID], metrics: CheckinMetrics, red_flag: bool) -> None:
    if pid is None or not db.enabled():
        return
    try:
        store.save_checkin(pid, metrics, red_flag)
    except Exception:  # noqa: BLE001 - saving must never break the reply
        log.exception("could not save check-in")


def _flagged(pid: Optional[UUID], text: str, flag: red_flags.RedFlagResult, metrics: CheckinMetrics) -> CheckinResponse:
    alerted = False
    if flag.level == "emergency" and pid is not None:
        alerted = notify.send_support_alert(pid).get("status") == "sent"
    _save(pid, metrics, True)
    # No reply audio: the frontend shows the fixed card and stops any playback on red_flag.
    return CheckinResponse(
        reply_text=flag.response, red_flag=True, red_flag_reason=flag.reason, red_flag_level=flag.level,
        support_alerted=alerted, transcript=text, metrics=metrics,
    )


def run_checkin(req: CheckinRequest) -> CheckinResponse:
    t0 = time.perf_counter()
    pid = _as_uuid(req.patient_id)
    text = _transcript(req)
    t_stt = time.perf_counter()

    # 1. Safety first, on the words alone (rules, then the Gemini backup if rules are clean).
    flag = red_flags.check(text)
    t_safe = time.perf_counter()
    if flag.flag:
        log.info("check-in red flag (%s, %s) stt=%.1fs safety=%.1fs", flag.level, flag.source,
                 t_stt - t0, t_safe - t_stt)
        return _flagged(pid, text, flag, CheckinMetrics())

    # 2. Safe so far: extraction and the reply run in parallel.
    f_metrics = _pool.submit(_extract, text)
    f_reply = _pool.submit(_reply, req.patient_id, text)
    metrics = f_metrics.result()

    # 3. Second pass with the numbers (e.g. "my BP was 165 over 112"). The reply is discarded if it fires.
    metric_flag = red_flags.check_rules(text, metrics)
    if metric_flag.flag:
        return _flagged(pid, text, metric_flag, metrics)

    reply = f_reply.result()
    t_reply = time.perf_counter()
    audio = _speak(reply)
    _save(pid, metrics, False)
    log.info("check-in ok stt=%.1fs safety=%.1fs extract+reply=%.1fs tts=%.1fs total=%.1fs",
             t_stt - t0, t_safe - t_stt, t_reply - t_safe, time.perf_counter() - t_reply, time.perf_counter() - t0)
    return CheckinResponse(reply_text=reply, reply_audio_base64=audio, transcript=text, metrics=metrics)
