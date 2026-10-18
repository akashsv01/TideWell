"""Smartwatch data (Apple Health via the Health Auto Export iOS app).

POST /wearables/token          signed in: create (or replace) this account's phone ingest token
POST /wearables/apple-health   the phone app posts here, authenticated with that token
GET  /wearables/{patient_id}   daily watch data + nudges for the dashboard

Watch metrics never raise a red flag (see app/wearables.py). Cuff blood pressure synced through Apple
Health is a measured reading, so it is saved to vitals and checked by the same fixed BP rules as a
typed reading, including the support-person SMS on an emergency.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query

from app import auth, db, demo_data, notify, store
from app.ai import red_flags
from app.schemas import CheckinMetrics
from app.schemas_data import WearableIngestOut, WearablesOut, WearableTokenOut
from app.wearables import nudges, parse_health_auto_export

router = APIRouter(prefix="/wearables", tags=["wearables"])
log = logging.getLogger("tidewell.wearables")

INGEST_PATH = "/wearables/apple-health"
MAX_POINTS = 50_000  # a sane cap per request; set the app's aggregation to "Hours" to stay far below it
_RANK = {None: 0, "urgent": 1, "emergency": 2}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/token", response_model=WearableTokenOut)
def create_token(user: auth.User = Depends(auth.require_user)) -> WearableTokenOut:
    """The token is shown once. Generating a new one disconnects the old phone setup."""
    if not db.enabled():
        raise HTTPException(503, "this needs the database (TIGER_DATABASE_URL)")
    if user.patient_id is None:
        raise HTTPException(409, "finish onboarding before connecting a watch")
    token = "tw_" + secrets.token_urlsafe(32)
    store.set_wearable_token(user.patient_id, _hash(token))
    return WearableTokenOut(token=token, ingest_path=INGEST_PATH, header_value=f"Bearer {token}")


def _token_from(authorization: Optional[str], x_token: Optional[str], query_token: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return (x_token or query_token or "").strip() or None


@router.post(INGEST_PATH.removeprefix("/wearables"), response_model=WearableIngestOut)
def ingest_apple_health(
    payload: Any = Body(...),
    authorization: Optional[str] = Header(default=None),
    x_tidewell_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None, description="Fallback if the app cannot send headers"),
) -> WearableIngestOut:
    parsed = parse_health_auto_export(payload)
    total = len(parsed.samples) + len(parsed.bp)
    if total > MAX_POINTS:
        raise HTTPException(413, f"too many data points ({total}); set the export's aggregation to Hours")

    if not db.enabled():
        # Local parse check with no database: nothing is stored, so no token is needed.
        return WearableIngestOut(saved=False, recognized=parsed.recognized, ignored=parsed.ignored,
                                 rejected=parsed.rejected)

    raw = _token_from(authorization, x_tidewell_token, token)
    patient_id = store.patient_for_wearable_token(_hash(raw)) if raw else None
    if patient_id is None:
        raise HTTPException(401, "missing or unknown TideWell watch token", headers={"WWW-Authenticate": "Bearer"})

    store.upsert_wearables(patient_id, parsed.samples)
    new_bp = store.insert_cuff_bp(patient_id, parsed.bp)

    # Fixed BP rules on the new, recent cuff readings (old back-filled readings can't need urgent care now).
    worst = red_flags.SAFE
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for r in new_bp:
        if r.time >= cutoff:
            res = red_flags.check_rules("", CheckinMetrics(bp_sys=r.sys, bp_dia=r.dia))
            if _RANK[res.level] > _RANK[worst.level]:
                worst = res
    if worst.level == "emergency":
        notify.send_support_alert(patient_id)
    if new_bp:
        try:
            store.refresh_today()
        except Exception:  # noqa: BLE001 - the readings are saved; the chart catches up on the next refresh
            log.exception("could not refresh today's trend bucket")

    log.info("apple health sync for %s: %s, %d new BP, %d rejected",
             patient_id, parsed.recognized, len(new_bp), parsed.rejected)
    return WearableIngestOut(
        saved=True, recognized=parsed.recognized, ignored=parsed.ignored, rejected=parsed.rejected,
        new_bp_readings=len(new_bp), red_flag=worst.flag, red_flag_level=worst.level,
        red_flag_reason=worst.reason, urgent_message=worst.response,
    )


@router.get("/{patient_id}", response_model=WearablesOut)
def daily(patient_id: UUID, range_: str = Query("21d", alias="range", pattern=r"^\d{1,3}d$"),
          user: Optional[auth.User] = Depends(auth.optional_user)) -> WearablesOut:
    auth.authorize_patient(patient_id, user)
    span = int(range_[:-1])
    if auth.is_demo(patient_id) and not db.enabled():
        days = demo_data.wearable_days(span)
        return WearablesOut(connected=True, synthetic=True, days=days, nudges=nudges(days))
    if not db.enabled():
        return WearablesOut(connected=False, days=[], nudges=[])
    if not store.patient_exists(patient_id):
        raise HTTPException(404, "patient not found")
    days = store.wearable_daily(patient_id, span)
    for d in days:
        if d.get("steps") is not None:
            d["steps"] = int(d["steps"])
    status = store.wearable_status(patient_id)
    demo = auth.is_demo(patient_id)
    return WearablesOut(connected=status["connected"] or (demo and bool(days)), synthetic=demo,
                        last_sync=status["last_sync"], days=days, nudges=nudges(days))
