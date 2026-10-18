"""Daily mood check (EPDS): GET /epds/questions, POST /epds, POST /epds/followup.

The parent sees a mood score of 30 minus the EPDS total (lower is harder). Below 20 the support person is
texted and called with the gentle fixed message; a self-harm answer sends the urgent one instead."""
from typing import Optional
from uuid import UUID

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
    mood = epds.mood_score(total)
    alerted = False
    if db.enabled() and not auth.is_demo(body.patient_id):  # the shared demo is never written to
        store.save_epds(body.patient_id, total, item10, body.answers)
        from app.routes.agents import analyse_later

        analyse_later(body.patient_id)
        if level == "emergency":
            alerted = notify.send_support_alert(body.patient_id).get("status") == "sent"
        elif mood < epds.MOOD_ALERT_BELOW:
            alerted = notify.send_support_alert(body.patient_id, kind="mood").get("status") == "sent"
    return EpdsOut(score=total, mood_score=mood, support_alerted=alerted, item10=item10, band=epds.band(total),
                   level=level, needs_followup=followup, response=epds.response_for(level))


@router.post("/followup", response_model=EpdsFollowupOut)
def followup(body: EpdsFollowupIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> EpdsFollowupOut:
    """Answer to "Are you thinking of ending your life or hurting yourself?" after Q10 > 0."""
    auth.authorize_patient(body.patient_id, user)
    level, response = epds.followup_outcome(body.answer)
    if level == "emergency" and db.enabled() and not auth.is_demo(body.patient_id):
        notify.send_support_alert(body.patient_id)
    return EpdsFollowupOut(level=level, response=response)


@router.get("/today")
def today(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    """Today's mood check (if taken), so it can be reopened and edited. A retake replaces it."""
    auth.authorize_patient(patient_id, user)
    if not db.enabled() or auth.is_demo(patient_id):
        return {"taken": False}
    r = store.todays_epds(patient_id)
    return {"taken": bool(r), "score": r["score"] if r else None, "answers": (r or {}).get("answers")}
