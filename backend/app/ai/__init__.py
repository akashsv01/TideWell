"""Public AI interface for the backend (P2). Import only from here: `from app import ai`.

All functions are synchronous and safe to call from `def` or `async def` FastAPI routes
(from `async def`, wrap slow calls in `await run_in_threadpool(...)` to keep the loop free).
Order in a check-in is fixed: transcribe -> check -> (if not flagged) extract_metrics + chat -> speak.
"""
from typing import Optional

from app.ai import extract as _extract
from app.ai import memory as _memory
from app.ai import red_flags as _red_flags
from app.ai import stt as _stt
from app.ai import tts as _tts
from app.ai.red_flags import EMERGENCY_RESPONSE, URGENT_RESPONSE, RedFlagResult  # noqa: F401 - re-exported
from app.schemas import CheckinMetrics

__all__ = ["transcribe", "check", "extract_metrics", "chat", "speak"]


def transcribe(audio_bytes: bytes) -> str:
    """Speech to text (ElevenLabs scribe_v2). Accepts mp3/webm/wav bytes. Returns "" for silence."""
    return _stt.transcribe(audio_bytes)


def check(transcript: str, metrics: Optional[CheckinMetrics] = None) -> RedFlagResult:
    """Safety check: rules, then a Gemini backup (3 s cap) that can only add a flag. Never raises.
    If result.flag: skip the agent and reply with result.response verbatim. result.level is
    "emergency" (911 card + SMS to support person) or "urgent" (call your provider now card)."""
    return _red_flags.check(transcript, metrics)


def extract_metrics(transcript: str) -> CheckinMetrics:
    """Gemini structured extraction. Only what was said; unstated fields are None/False/[]."""
    return _extract.extract_metrics(transcript)


def chat(patient_id: str, message: str) -> str:
    """Reply with Backboard memory for this patient (creates their assistant/thread on first use)."""
    return _memory.chat(patient_id, message)


def speak(text: str) -> bytes:
    """Text to speech (ElevenLabs). Returns mp3 bytes; base64 them for CheckinResponse.reply_audio_base64."""
    return _tts.speak(text)
