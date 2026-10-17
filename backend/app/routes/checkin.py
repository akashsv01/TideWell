"""POST /checkin (Person 1). The pipeline lives in app/ai/checkin.py."""
from fastapi import APIRouter, HTTPException

from app.ai.checkin import NoSpeech, TranscriptionFailed, run_checkin
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter()


@router.post("/checkin", response_model=CheckinResponse)
def checkin(body: CheckinRequest) -> CheckinResponse:
    # Plain `def`: FastAPI runs it in a worker thread, so the blocking SDK calls don't stall the loop.
    try:
        return run_checkin(body)
    except NoSpeech as e:
        raise HTTPException(422, str(e)) from e
    except TranscriptionFailed as e:
        raise HTTPException(502, str(e)) from e
