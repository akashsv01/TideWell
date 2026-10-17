# `app.ai`: how to call it (for P2)

Import only from the package: `from app import ai`. Every function is synchronous.

| Function | Returns | Notes |
|---|---|---|
| `ai.transcribe(audio_bytes)` | `str` | ElevenLabs STT. Takes mp3, webm or wav bytes. |
| `ai.check(transcript, metrics=None)` | `RedFlagResult(flag, reason, source)` | Rules first, then a Gemini backup capped at 3 s. Never raises. |
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
from app.ai import URGENT_RESPONSE
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter()

@router.post("/checkin", response_model=CheckinResponse)
async def checkin(req: CheckinRequest) -> CheckinResponse:
    text = req.text or await run_in_threadpool(ai.transcribe, base64.b64decode(req.audio_base64))

    # 1. Safety runs BEFORE any agent or LLM reply. Never skip or reorder this.
    flag = await run_in_threadpool(ai.check, text)
    if flag.flag:
        # TODO(P2): send the Twilio SMS to the support person, save the check-in with red_flag=True
        audio = await run_in_threadpool(ai.speak, URGENT_RESPONSE)
        return CheckinResponse(reply_text=URGENT_RESPONSE, red_flag=True, red_flag_reason=flag.reason,
                               reply_audio_base64=base64.b64encode(audio).decode())

    # 2. Safe path
    metrics = await run_in_threadpool(ai.extract_metrics, text)
    flag = await run_in_threadpool(ai.check, text, metrics)  # BP and other metric-based rules
    if flag.flag:
        ...  # same urgent path as above
    reply = await run_in_threadpool(ai.chat, req.patient_id, text)
    audio = await run_in_threadpool(ai.speak, reply)
    # TODO(P2): save metrics to the checkins and vitals hypertables
    return CheckinResponse(reply_text=reply, metrics=metrics,
                           reply_audio_base64=base64.b64encode(audio).decode())
```

## What P2 needs to add

- **Database column:** add `backboard_assistant_id TEXT` and `backboard_thread_id TEXT` to `patients`. Until then, the IDs live in `backend/.data/backboard_ids.json` (gitignored). The swap only touches `get_mapping` and `save_mapping` in `memory.py`.
- **Thresholds:** `SEVERE_BP_SYS` and `SEVERE_BP_DIA` in `red_flags.py` are placeholders until P4 verifies them.
- **Gemini quota:** a free-tier key allows about 5 requests per minute per model, and a check-in uses 2 to 4 calls. Use a paid key or hackathon credits for the demo.
