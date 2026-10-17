"""POST /onboard, GET /me, GET /trends/{patient_id}, POST /vitals, DELETE /patients/{patient_id}."""
from uuid import UUID, uuid4

import logging

from fastapi import APIRouter, HTTPException, Query, Response

from app import categories, db, demo_data, notify, store
from app.ai import memory, red_flags
from app.schemas import CheckinMetrics, TrendPoint
from app.schemas_data import MeOut, OnboardIn, OnboardOut, VitalsIn, VitalsOut

router = APIRouter()
log = logging.getLogger("tidewell.patients")


def _pick_id(patient_id: str | None) -> UUID:
    try:
        return UUID(patient_id) if patient_id else uuid4()
    except ValueError:
        return uuid4()


@router.post("/onboard", response_model=OnboardOut)
def onboard(body: OnboardIn) -> OnboardOut:
    cats = categories.assign(body.delivery_type, body.conditions, body.breastfeeding)
    patient_id = _pick_id(body.patient_id)
    if db.enabled() and body.clerk_user_id:
        # A signed-in user who onboards again updates their own chart instead of creating a second one.
        patient_id = store.patient_id_for_clerk(body.clerk_user_id) or patient_id
    if db.enabled():
        store.insert_patient(patient_id, body, cats)
    return OnboardOut(patient_id=patient_id, categories=cats)


@router.get("/me", response_model=MeOut)
def me(clerk_user_id: str = Query(min_length=1, max_length=200)) -> MeOut:
    """Which patient belongs to this login. 404 means not onboarded yet: send them to /onboarding.
    NOTE: trusts the id the frontend sends. Verify the Clerk session token here before real use."""
    if not db.enabled():
        raise HTTPException(404, "no database configured")
    pid = store.patient_id_for_clerk(clerk_user_id)
    ctx = store.patient_context(pid) if pid else None
    if not ctx:
        raise HTTPException(404, "not onboarded")
    return MeOut(patient_id=pid, name=ctx["name"], days_postpartum=ctx["days_postpartum"],
                 delivery_type=ctx["delivery_type"])


@router.get("/trends/{patient_id}", response_model=list[TrendPoint])
def trends(patient_id: UUID, range_: str = Query("21d", alias="range", pattern=r"^\d{1,3}d$")) -> list[dict]:
    days = int(range_[:-1])
    if not db.enabled():
        return demo_data.trend_points(days)  # mock: Maya's series for any id
    if not store.patient_exists(patient_id):
        raise HTTPException(404, "patient not found")
    return store.trends(patient_id, days)


@router.post("/vitals", response_model=VitalsOut)
def add_vitals(body: VitalsIn) -> VitalsOut:
    """Typed/manual vitals. Runs the same red-flag rules as a check-in, so a typed BP of 170/115
    gets the urgent response too. Thresholds live in app/ai/red_flags.py (placeholders until verified)."""
    if body.bp_sys is None and body.bp_dia is None and body.heart_rate is None \
            and body.temp_c is None and body.glucose is None:
        raise HTTPException(422, "send at least one vital sign")
    if (body.bp_sys is None) != (body.bp_dia is None):
        raise HTTPException(422, "send bp_sys and bp_dia together")

    # Rules only: there is no transcript here, so the Gemini backup layer would have nothing to read.
    result = red_flags.check_rules("", CheckinMetrics(bp_sys=body.bp_sys, bp_dia=body.bp_dia))
    flag, reason = result.flag, result.reason
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
    return VitalsOut(
        saved=db.enabled(), red_flag=flag, red_flag_reason=reason,
        urgent_message=result.response,  # EMERGENCY or URGENT fixed text, None when not flagged
    )


@router.delete("/patients/{patient_id}", status_code=204)
def delete_my_data(patient_id: UUID) -> Response:
    """One-tap delete-my-data: database rows and Backboard memories. The demo patient is protected
    (re-run scripts/seed_maya.py to reset Maya instead)."""
    if patient_id == demo_data.MAYA_ID:
        raise HTTPException(409, "the demo patient cannot be deleted")
    if not db.enabled():
        raise HTTPException(503, "no database configured")
    try:
        memory.forget(str(patient_id))  # before the row (and its Backboard ids) is gone
    except Exception:  # noqa: BLE001 - still delete our own copy of the data
        log.exception("could not reset Backboard memories")
    if not store.delete_patient(patient_id):
        raise HTTPException(404, "patient not found")
    return Response(status_code=204)
