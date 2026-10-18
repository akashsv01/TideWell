"""Weekly EPDS mood check: GET /epds/questions, POST /epds, POST /epds/followup."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app import auth, db, epds, notify, store
from app.schemas_data import EpdsFollowupIn, EpdsFollowupOut, EpdsIn, EpdsOut

router = APIRouter(prefix="/epds")


@router.get("/questions")
def questions() -> dict:
    return {"citation": epds.CITATION, "followup_question": epds.FOLLOWUP_QUESTION, "questions": epds.questions()}


@router.post("", response_model=EpdsOut)
def submit(body: EpdsIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> EpdsOut:
    auth.authorize_patient(body.patient_id, user)
    try:
        total, item10 = epds.score(body.answers)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    level, followup = epds.item10_outcome(item10)
    if db.enabled() and not auth.is_demo(body.patient_id):  # the shared demo is never written to
        store.save_epds(body.patient_id, total, item10)
        if level == "emergency":
            notify.send_support_alert(body.patient_id)
    return EpdsOut(score=total, item10=item10, band=epds.band(total), level=level,
                   needs_followup=followup, response=epds.response_for(level))


@router.post("/followup", response_model=EpdsFollowupOut)
def followup(body: EpdsFollowupIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> EpdsFollowupOut:
    """Answer to "Are you thinking of ending your life or hurting yourself?" after Q10 > 0."""
    auth.authorize_patient(body.patient_id, user)
    level, response = epds.followup_outcome(body.answer)
    if level == "emergency" and db.enabled() and not auth.is_demo(body.patient_id):
        notify.send_support_alert(body.patient_id)
    return EpdsFollowupOut(level=level, response=response)
