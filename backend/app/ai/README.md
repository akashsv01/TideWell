# `app.ai`: how to call it (for P2)

Import only from the package: `from app import ai`. Every function is synchronous.

| Function | Returns | Notes |
|---|---|---|
| `ai.transcribe(audio_bytes)` | `str` | ElevenLabs STT. Takes mp3, webm or wav bytes. |
| `ai.check(transcript, metrics=None)` | `RedFlagResult(flag, reason, source, level)` | Rules first, then a Gemini backup capped at 3 s. Never raises. `level` is `"emergency"` or `"urgent"`; `result.response` is the fixed reply text to use. |
| `ai.extract_metrics(transcript)` | `CheckinMetrics` | Fields that weren't said come back as `None`, `False` or `[]`. |
| `ai.chat(patient_id, message)` | `str` | Searches the patient's Backboard memories, stores the new message, and Gemini writes the reply. Backboard's free credit doesn't cover its own LLM replies, but it does cover memory. |
| `ai.speak(text)` | `bytes` (mp3) | ElevenLabs TTS. |

## Check-in route sketch

`run_checkin` comes in Phase 2 and lives with P1. This sketch only shows the call order and the safety rule.

```python
import base64
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from app import ai
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter()

@router.post("/checkin", response_model=CheckinResponse)
async def checkin(req: CheckinRequest) -> CheckinResponse:
    text = req.text or await run_in_threadpool(ai.transcribe, base64.b64decode(req.audio_base64))

    # 1. Safety runs BEFORE any agent or LLM reply. Never skip or reorder this.
    flag = await run_in_threadpool(ai.check, text)
    if flag.flag:
        # flag.response is the fixed text for the level: EMERGENCY (911 card) or URGENT (call provider now).
        # TODO(P2): if flag.level == "emergency", send the Twilio SMS to the support person.
        # TODO(P2): save the check-in with red_flag=True (store flag.level too).
        audio = await run_in_threadpool(ai.speak, flag.response)
        return CheckinResponse(reply_text=flag.response, red_flag=True, red_flag_reason=flag.reason,
                               red_flag_level=flag.level, reply_audio_base64=base64.b64encode(audio).decode())

    # 2. Safe path
    metrics = await run_in_threadpool(ai.extract_metrics, text)
    flag = await run_in_threadpool(ai.check, text, metrics)  # BP and other metric-based rules
    if flag.flag:
        ...  # same red-flag path as above
    reply = await run_in_threadpool(ai.chat, req.patient_id, text)
    audio = await run_in_threadpool(ai.speak, reply)
    # TODO(P2): save metrics to the checkins and vitals hypertables
    return CheckinResponse(reply_text=reply, metrics=metrics,
                           reply_audio_base64=base64.b64encode(audio).decode())
```

## Two red-flag levels

Both levels skip the agent and use a fixed, pre-written reply. Neither one uses AI wording.

| `flag.level` | Matches guidelines.json | Reply (`flag.response`) | Support-person SMS |
|---|---|---|---|
| `emergency` | RED | Call 911 or go to the ER now, plus the 988 line | Yes |
| `urgent` | AMBER | Call your doctor, midwife or clinic now; go to the ER or call 911 if you can't reach them; maternal mental health hotline | No (team decision) |

The frontend should show the two as visibly different cards, using `CheckinResponse.red_flag_level`.

## What P2 needs to add

- **Database column:** add `backboard_assistant_id TEXT` and `backboard_thread_id TEXT` to `patients`. Until then, the IDs live in `backend/.data/backboard_ids.json` (gitignored). The swap only touches `get_mapping` and `save_mapping` in `memory.py`.
- **Thresholds:** the blood pressure cutoffs in `red_flags.py` (160/110 on its own, or 140/90 with a severe headache or upper belly pain) come from `guidelines.json` (bp-02, bp-03). They still need clinician sign-off, and `thresholds.md` is empty.
- **Gemini quota:** a free-tier key allows about 5 requests per minute per model, and a check-in uses 2 to 4 calls. Use a paid key or hackathon credits for the demo.
