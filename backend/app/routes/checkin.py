"""POST /checkin (Person 1). The pipeline lives in app/ai/checkin.py."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app import auth
from app.ai.checkin import NoSpeech, TranscriptionFailed, run_checkin
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter()


@router.post("/checkin", response_model=CheckinResponse)
def checkin(body: CheckinRequest, user: Optional[auth.User] = Depends(auth.optional_user)) -> CheckinResponse:
    # Plain `def`: FastAPI runs it in a worker thread, so the blocking SDK calls don't stall the loop.
    try:
        pid = UUID(body.patient_id)
    except ValueError as e:
        raise HTTPException(422, "patient_id must be a UUID") from e
    auth.authorize_patient(pid, user)
    try:
        return run_checkin(body)
    except NoSpeech as e:
        raise HTTPException(422, str(e)) from e
    except TranscriptionFailed as e:
        raise HTTPException(502, str(e)) from e
