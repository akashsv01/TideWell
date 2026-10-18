"""Apple Health, through the Health Auto Export iPhone app (its Premium "REST API" automation).

Phone side
POST   /wearables/apple-health     the iPhone app posts here every hour or so, with the patient's code
                                   (Authorization: Bearer tw_...). Data is staged in wearable_metrics.
                                   INSTANT CHECK: a new cuff BP from the last 24 h goes through the same
                                   fixed BP rules as a typed reading right away; an unsafe one is saved to
                                   vitals, recorded as an alert (the website shows the urgent card) and,
                                   for an emergency, texts the support person (if they agreed and Twilio
                                   is set up).
Website side
POST   /wearables/token            create (or replace) this account's connection code; shown once
DELETE /wearables/token            disconnect the iPhone
GET    /wearables/status           connected? last sync? sample data present?
GET    /wearables/guide.pdf        step-by-step iPhone setup guide (no code inside; it is a secret)
POST   /wearables/import           the "Get my Apple Health data" button: copy the last 7 days into the
                                   tide (sleep, BP, resting heart rate). No phone data yet -> a week of
                                   clearly labelled SAMPLE data in normal ranges instead.
DELETE /wearables/sample           remove that sample data
GET    /wearables/alerts           unsafe readings that arrived from the phone and haven't been shown
POST   /wearables/alerts/seen

Watch metrics never raise a red flag (app/wearables.py). The Watch agent is not changed: after an
import it runs as after any check-in and reads the new sleep and BP like any other numbers.
Parser and nudges by Sreeja (person2-backend).
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app import auth, db, notify, store
from app.ai import red_flags
from app.config import get_settings
from app.schemas import CheckinMetrics
from app.wearables import parse_health_auto_export, sample_week

router = APIRouter(prefix="/wearables", tags=["wearables"])
log = logging.getLogger("tidewell.wearables")

INGEST_PATH = "/wearables/apple-health"
MAX_POINTS = 50_000  # per request; the guide tells the app to group by day or hour
INSTANT_WINDOW = timedelta(hours=24)  # older readings can't need urgent care now
_RANK = {None: 0, "urgent": 1, "emergency": 2}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _need_db() -> None:
    if not db.enabled():
        raise HTTPException(503, "Apple Health needs the database (TIGER_DATABASE_URL)")


def _own_patient(patient_id: UUID, user: Optional[auth.User]) -> None:
    auth.authorize_patient(patient_id, user)
    if auth.is_demo(patient_id):
        raise HTTPException(403, "The demo is read-only. Create your own account to try Apple Health.")
    _need_db()


def ingest_url(request: Request) -> str:
    """Where the iPhone should send data: PUBLIC_API_URL when set (Render), else this request's host."""
    base = get_settings().public_api_url.rstrip("/")
    if not base:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        base = f"{proto}://{host}"
    return base + INGEST_PATH


def _safety_check(patient_id: UUID, readings: list, source: str) -> red_flags.RedFlagResult:
    """Fixed BP rules on recent readings that haven't been checked before. An unsafe reading is saved
    to vitals at once (so charts, the Watch agent and the clinician view see it) and recorded as an
    alert; an emergency also texts the support person."""
    worst, worst_reading = red_flags.SAFE, None
    cutoff = datetime.now(timezone.utc) - INSTANT_WINDOW
    for r in readings:
        if r.time < cutoff:
            continue
        res = red_flags.check_rules("", CheckinMetrics(bp_sys=r.sys, bp_dia=r.dia))
        if not res.flag:
            continue
        store.add_bp_reading(patient_id, r.time, r.sys, r.dia, source)
        if not store.create_health_alert(patient_id, r.time, res.level, res.reason, r.sys, r.dia):
            continue  # this reading already alerted
        if _RANK[res.level] > _RANK[worst.level]:
            worst, worst_reading = res, r
    if worst_reading is not None:
        from app.routes.agents import analyse_later

        if worst.level == "emergency":
            notify.send_support_alert(patient_id)  # skipped (and logged) without consent or Twilio
        analyse_later(patient_id)
    return worst


# --- Phone -> server ----------------------------------------------------------------------------
class IngestOut(BaseModel):
    saved: bool
    recognized: dict[str, int]   # Tidewell metric -> points kept
    ignored: list[str]           # Health Auto Export metric names Tidewell does not use
    rejected: int                # points dropped as unreadable or implausible
    new_bp_readings: int = 0
    alert_level: Optional[Literal["emergency", "urgent"]] = None


def _token_from(authorization: Optional[str], x_token: Optional[str], query_token: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return (x_token or query_token or "").strip() or None


@router.post(INGEST_PATH.removeprefix("/wearables"), response_model=IngestOut)
def ingest_apple_health(
    payload: Any = Body(...),
    authorization: Optional[str] = Header(default=None),
    x_tidewell_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None, description="Only if the app cannot send headers"),
) -> IngestOut:
    _need_db()
    raw = _token_from(authorization, x_tidewell_token, token)
    patient_id = store.patient_for_wearable_token(_hash(raw)) if raw else None
    if patient_id is None:
        raise HTTPException(401, "missing or unknown Tidewell connection code", headers={"WWW-Authenticate": "Bearer"})
    parsed = parse_health_auto_export(payload)
    # Readings dated in the future are a phone clock or export error: drop them (an hour of slack).
    latest_ok = datetime.now(timezone.utc) + timedelta(hours=1)
    keep_s = [x for x in parsed.samples if x.time <= latest_ok]
    keep_b = [x for x in parsed.bp if x.time <= latest_ok]
    parsed.rejected += len(parsed.samples) - len(keep_s) + len(parsed.bp) - len(keep_b)
    parsed.samples, parsed.bp = keep_s, keep_b
    total = len(parsed.samples) + len(parsed.bp)
    if total > MAX_POINTS:
        raise HTTPException(413, f"too many data points ({total}); set the export's grouping to Days or Hours")
    new_bp = store.stage_wearables(patient_id, parsed.samples, parsed.bp)
    worst = _safety_check(patient_id, new_bp, "apple_health")
    log.info("apple health sync for %s: %s, %d new BP, %d rejected, alert=%s",
             patient_id, parsed.recognized, len(new_bp), parsed.rejected, worst.level)
    return IngestOut(saved=True, recognized=parsed.recognized, ignored=parsed.ignored, rejected=parsed.rejected,
                     new_bp_readings=len(new_bp), alert_level=worst.level)


# --- Website: connecting the iPhone -------------------------------------------------------------
@router.post("/token")
def create_token(request: Request, user: auth.User = Depends(auth.require_user)) -> dict:
    """The code is shown once. A new one disconnects the old phone setup."""
    _need_db()
    if user.patient_id is None:
        raise HTTPException(409, "finish onboarding before connecting an iPhone")
    code = "tw_" + secrets.token_urlsafe(32)
    store.set_wearable_token(user.patient_id, _hash(code))
    return {"code": code, "ingest_url": ingest_url(request), "header_name": "Authorization",
            "header_value": f"Bearer {code}"}


@router.delete("/token", status_code=204)
def delete_token(user: auth.User = Depends(auth.require_user)) -> Response:
    _need_db()
    if user.patient_id:
        store.clear_wearable_token(user.patient_id)
    return Response(status_code=204)


@router.get("/status")
def status(request: Request, patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    auth.authorize_patient(patient_id, user)
    if auth.is_demo(patient_id) or not db.enabled():
        return {"available": False, "connected": False, "ingest_url": ingest_url(request)}
    return {"available": True, **store.wearable_status(patient_id), "ingest_url": ingest_url(request)}


@router.get("/guide.pdf")
def guide(request: Request) -> Response:
    from app.health_guide_pdf import build

    return Response(build(ingest_url(request)), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="tidewell-apple-health-setup.pdf"'})


# --- Website: the "Get my Apple Health data" button ------------------------------------------
class ImportIn(BaseModel):
    patient_id: UUID


@router.post("/import")
def import_health(body: ImportIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    pid = body.patient_id
    _own_patient(pid, user)
    st = store.wearable_status(pid)
    recent = st["latest_reading"] and st["latest_reading"] >= datetime.now(timezone.utc) - timedelta(days=7)
    source = "apple_health" if recent else store.SAMPLE_SOURCE
    if source == store.SAMPLE_SOURCE:
        samples, bp = sample_week(datetime.now(timezone.utc), seed=str(pid))
        store.stage_wearables(pid, samples, bp, source=store.SAMPLE_SOURCE)
    filled = store.import_wearables(pid, days=7, source=source)

    # Readings imported now still get the fixed rules (instant check already ran for phone data;
    # an alert is never repeated). Sample data is normal by design, so this only matters for real data.
    worst = red_flags.SAFE
    if source == "apple_health" and filled["latest_bp"]:
        from app.wearables import BpReading

        lb = filled["latest_bp"]
        worst = _safety_check(pid, [BpReading(lb["time"], lb["sys"], lb["dia"])], source)
    from app.routes.agents import analyse_later

    analyse_later(pid)  # the Watch agent, exactly as after a check-in
    return {"source": "sample" if source == store.SAMPLE_SOURCE else "iphone", "connected": st["connected"],
            "last_sync": st["last_sync"], **filled,
            "red_flag": worst.flag, "red_flag_level": worst.level}


@router.delete("/sample", status_code=204)
def remove_sample(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> Response:
    _own_patient(patient_id, user)
    store.remove_wearable_source(patient_id, store.SAMPLE_SOURCE)
    return Response(status_code=204)


# --- Website: alerts from the instant check --------------------------------------------------
@router.get("/alerts")
def alerts(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    auth.authorize_patient(patient_id, user)
    if auth.is_demo(patient_id) or not db.enabled():
        return {"alerts": []}
    return {"alerts": store.unseen_health_alerts(patient_id)}


@router.post("/alerts/seen", status_code=204)
def alerts_seen(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> Response:
    _own_patient(patient_id, user)
    store.mark_health_alerts_seen(patient_id)
    return Response(status_code=204)
