"""POST /checkin and POST /transcribe (Person 1). The pipeline lives in app/ai/checkin.py."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app import auth
from app.ai.checkin import NoSpeech, TranscriptionFailed, run_checkin, transcribe_only
from app.schemas import CheckinRequest, CheckinResponse, TranscribeResponse

router = APIRouter()


def _authorize(body: CheckinRequest, user: Optional[auth.User]) -> None:
    try:
        pid = UUID(body.patient_id)
    except ValueError as e:
        raise HTTPException(422, "patient_id must be a UUID") from e
    auth.authorize_patient(pid, user)


@router.post("/checkin", response_model=CheckinResponse)
def checkin(body: CheckinRequest, user: Optional[auth.User] = Depends(auth.optional_user)) -> CheckinResponse:
    # Plain `def`: FastAPI runs it in a worker thread, so the blocking SDK calls don't stall the loop.
    _authorize(body, user)
    try:
        return run_checkin(body)
    except NoSpeech as e:
        raise HTTPException(422, str(e)) from e
    except TranscriptionFailed as e:
        raise HTTPException(502, str(e)) from e


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe(body: CheckinRequest, user: Optional[auth.User] = Depends(auth.optional_user)) -> TranscribeResponse:
    """ElevenLabs speech-to-text only. The frontend shows the words, then sends them to /checkin as text."""
    _authorize(body, user)
    try:
        return TranscribeResponse(transcript=transcribe_only(body))
    except NoSpeech as e:
        raise HTTPException(422, str(e)) from e
    except TranscriptionFailed as e:
        raise HTTPException(502, str(e)) from e
