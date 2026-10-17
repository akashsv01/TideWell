"""Profile and patient data:
POST /onboard (= PUT /profile), GET /profile, PUT /profile, GET /patients/{id}/overview,
GET /trends/{patient_id}, POST /vitals, DELETE /patients/{patient_id}.

Access: the demo patient (Maya) is open to everyone; any other patient only to the account that owns
it (app/auth.py authorize_patient). Onboarding and profile edits need a signed-in account.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app import auth, categories, db, demo_data, notify, store
from app.ai import memory, red_flags
from app.schemas import CheckinMetrics, Profile, ProfileOut, TrendPoint
from app.schemas_data import Overview, VitalsIn, VitalsOut

router = APIRouter()
log = logging.getLogger("tidewell.patients")


def _need_db() -> None:
    if not db.enabled():
        raise HTTPException(503, "this needs the database (TIGER_DATABASE_URL)")


def _save_profile(body: Profile, user: auth.User) -> ProfileOut:
    _need_db()
    if not body.consent_granted:
        raise HTTPException(422, "consent is required to store your check-ins")
    cats = categories.assign(body.delivery_method, store.derived_conditions(body),
                             body.feeding_type in ("breastfeeding", "mixed"))
    pid = store.upsert_profile(user.id, body, cats)
    return ProfileOut(**store.get_profile(pid))


@router.post("/onboard", response_model=ProfileOut)
def onboard(body: Profile, user: auth.User = Depends(auth.require_user)) -> ProfileOut:
    return _save_profile(body, user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: Profile, user: auth.User = Depends(auth.require_user)) -> ProfileOut:
    return _save_profile(body, user)


@router.get("/profile", response_model=ProfileOut)
def read_profile(patient_id: Optional[UUID] = Query(default=None),
                 user: Optional[auth.User] = Depends(auth.optional_user)) -> ProfileOut:
    """Your own profile when signed in, or the demo's with ?patient_id=<Maya>."""
    _need_db()
    pid = patient_id or (user.patient_id if user else None)
    if pid is None:
        raise HTTPException(404, "not onboarded yet")
    auth.authorize_patient(pid, user)
    prof = store.get_profile(pid)
    if not prof:
        raise HTTPException(404, "not onboarded yet")
    return ProfileOut(**prof, demo=auth.is_demo(pid))


@router.get("/patients/{patient_id}/overview", response_model=Overview)
def overview(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> Overview:
    auth.authorize_patient(patient_id, user)
    _need_db()
    prof = store.get_profile(patient_id)
    if not prof:
        raise HTTPException(404, "patient not found")
    last = store.last_epds(patient_id)
    return Overview(
        patient_id=patient_id, demo=auth.is_demo(patient_id), name=prof["name"],
        day_postpartum=prof["day_postpartum"], delivery_method=prof["delivery_method"],
        feeding_type=prof["feeding_type"], history_mental_health=prof["history_mental_health"],
        history_pregnancy_complications=prof["history_pregnancy_complications"],
        epds_due=store.epds_due(prof["day_postpartum"], last),
        last_epds_score=last["score"] if last else None,
        last_epds_date=last["time"].date() if last else None,
    )


@router.get("/trends/{patient_id}", response_model=list[TrendPoint])
def trends(patient_id: UUID, range_: str = Query("21d", alias="range", pattern=r"^\d{1,3}d$"),
           user: Optional[auth.User] = Depends(auth.optional_user)) -> list[dict]:
    auth.authorize_patient(patient_id, user)
    days = int(range_[:-1])
    if not db.enabled():
        return demo_data.trend_points(days)  # mock: Maya's series
    if not store.patient_exists(patient_id):
        raise HTTPException(404, "patient not found")
    return store.trends(patient_id, days)


@router.post("/vitals", response_model=VitalsOut)
def add_vitals(body: VitalsIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> VitalsOut:
    """Typed/manual vitals. Runs the same red-flag rules as a check-in."""
    auth.authorize_patient(body.patient_id, user)
    if body.bp_sys is None and body.bp_dia is None and body.heart_rate is None \
            and body.temp_c is None and body.glucose is None:
        raise HTTPException(422, "send at least one vital sign")
    if (body.bp_sys is None) != (body.bp_dia is None):
        raise HTTPException(422, "send bp_sys and bp_dia together")

    # Rules only: there is no transcript here, so the Gemini backup layer would have nothing to read.
    result = red_flags.check_rules("", CheckinMetrics(bp_sys=body.bp_sys, bp_dia=body.bp_dia))
    if db.enabled():
        if not store.patient_exists(body.patient_id):
            raise HTTPException(404, "patient not found")
        store.save_vitals(body)
        try:
            store.refresh_today()
        except Exception:  # noqa: BLE001 - the reading is saved; the chart catches up on the next refresh
            log.exception("could not refresh today's trend bucket")
        if result.level == "emergency":  # support-person SMS is for emergencies only
            notify.send_support_alert(body.patient_id)
    return VitalsOut(saved=db.enabled(), red_flag=result.flag, red_flag_reason=result.reason,
                     urgent_message=result.response)


@router.delete("/patients/{patient_id}", status_code=204)
def delete_my_data(patient_id: UUID, user: auth.User = Depends(auth.require_user)) -> Response:
    """Delete-my-data: every row, the Backboard memories and the account itself (which also ends
    every session). The demo patient is protected (re-run scripts/seed_maya.py to reset Maya)."""
    if auth.is_demo(patient_id):
        raise HTTPException(409, "the demo patient cannot be deleted")
    auth.authorize_patient(patient_id, user)
    _need_db()
    try:
        memory.forget(str(patient_id))  # before the row (and its Backboard ids) is gone
    except Exception:  # noqa: BLE001 - still delete our own copy of the data
        log.exception("could not reset Backboard memories")
    store.delete_patient(patient_id)
    auth.delete_user(user.id)
    try:
        store.refresh_all()  # drop the deleted rows from the daily aggregates too
    except Exception:  # noqa: BLE001
        log.exception("could not refresh aggregates after delete")
    return Response(status_code=204)
