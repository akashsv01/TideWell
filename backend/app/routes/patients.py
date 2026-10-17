"""POST /onboard, GET /trends/{patient_id}, POST /vitals."""
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query

from app import categories, db, demo_data, notify, store
from app.ai import red_flags
from app.schemas import CheckinMetrics, TrendPoint
from app.schemas_data import OnboardIn, OnboardOut, VitalsIn, VitalsOut

router = APIRouter()


def _pick_id(user_id: str | None) -> UUID:
    try:
        return UUID(user_id) if user_id else uuid4()
    except ValueError:
        return uuid4()


@router.post("/onboard", response_model=OnboardOut)
def onboard(body: OnboardIn) -> OnboardOut:
    cats = categories.assign(body.delivery_type, body.conditions, body.breastfeeding)
    patient_id = _pick_id(body.user_id)
    if db.enabled():
        store.insert_patient(patient_id, body, cats)
    return OnboardOut(patient_id=patient_id, categories=cats)


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

    flag, reason = red_flags.check("", CheckinMetrics(bp_sys=body.bp_sys, bp_dia=body.bp_dia))
    if db.enabled():
        if not store.patient_exists(body.patient_id):
            raise HTTPException(404, "patient not found")
        store.save_vitals(body)
        if flag:
            notify.send_support_alert(body.patient_id)
    return VitalsOut(
        saved=db.enabled(), red_flag=flag, red_flag_reason=reason,
        urgent_message=red_flags.URGENT_RESPONSE if flag else None,
    )
