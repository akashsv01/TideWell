"""Agent and care endpoints.

POST /ask                          Care Navigator chat (safety check first; cited answers)
GET  /patients/{id}/risk           Watch agent analysis now (+ open care request, appointments)
PUT  /patients/{id}/location       save location (browser coords or ZIP) for nearby care
GET  /care/nearby                  nearest maternity care (patient's saved location, coords or ZIP)
POST /care-requests/{id}/book      patient books a proposed time (Booking agent never books alone)
POST /care-requests/{id}/dismiss
GET  /patients/{id}/summary.pdf    one-page visit summary for the doctor
POST /vitals/photo                 read a BP cuff photo (Gemini vision); the patient confirms it
POST/DELETE /patients/{id}/circle  Care Circle read-only link for the support person
GET  /circle/{token}               what the support person sees
GET  /clinician/overview           patients by tier with agent notes, requests, appointments + query timing
"""
import base64
import hashlib
import io
import logging
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app import auth, care, db, store
from app.agents import watch
from app.ai import red_flags
from app.ai.agent import CareNavigator
from app.ai.checkin import patient_context

router = APIRouter()
log = logging.getLogger("tidewell.agents")
_pool = ThreadPoolExecutor(max_workers=4)


def analyse_later(patient_id: UUID) -> None:
    """Fire-and-forget Watch-agent run after new data (never for the shared demo)."""
    if db.enabled() and not auth.is_demo(patient_id):
        _pool.submit(watch.run_safely, patient_id)


def _need_db() -> None:
    if not db.enabled():
        raise HTTPException(503, "this needs the database (TIGER_DATABASE_URL)")


# --- Ask (Care Navigator) -------------------------------------------------------------------
class AskIn(BaseModel):
    patient_id: UUID
    question: str = Field(min_length=2, max_length=1000)


class AskOut(BaseModel):
    answer: str
    citations: list[dict] = Field(default_factory=list)
    tools_called: list[str] = Field(default_factory=list)
    red_flag: bool = False
    red_flag_level: Optional[Literal["emergency", "urgent"]] = None


@router.post("/ask", response_model=AskOut)
def ask(body: AskIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> AskOut:
    auth.authorize_patient(body.patient_id, user)
    flag = red_flags.check(body.question)  # safety before any AI, same as check-ins
    if flag.flag:
        return AskOut(answer=flag.response, red_flag=True, red_flag_level=flag.level)
    reply = CareNavigator().run(str(body.patient_id), body.question, context=patient_context(body.patient_id))
    return AskOut(answer=reply.text, citations=reply.citations, tools_called=reply.tools_called)


# --- Risk + care requests -----------------------------------------------------------------------
@router.get("/patients/{patient_id}/risk")
def risk(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    auth.authorize_patient(patient_id, user)
    _need_db()
    r = watch.run(patient_id, persist=not auth.is_demo(patient_id))
    r["appointments"] = [] if auth.is_demo(patient_id) else store.upcoming_appointments(patient_id)
    if auth.is_demo(patient_id) and r["overall"] in ("amber", "red"):
        # Show the demo what the Booking agent proposes, without writing to the shared demo.
        from app.agents.booking import _places
        from app.routes.appointments import _generate

        prof = store.get_profile(patient_id) or {}
        r["care_request"] = {"id": None, "tier": r["overall"], "demo": True,
                             "reasons": [x for t in r["tiers"] if t["tier"] == "amber" for x in t["reasons"]],
                             "patient_message": "Your blood pressure has gone up four readings in a row and you've had "
                                                "headaches this week. Guidelines suggest getting it checked in the next "
                                                "1 to 3 days. Pick a time below.",
                             "facilities": care.best_for_visit(_places(prof)),
                             "slots": [s.isoformat() for s in _generate("amber")[:4]]}
    return r


class BookIn(BaseModel):
    slot: datetime
    facility_index: int = Field(default=0, ge=0, le=5)


@router.post("/care-requests/{request_id}/book")
def book(request_id: UUID, body: BookIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    _need_db()
    req = store.get_care_request(request_id)
    if not req:
        raise HTTPException(404, "request not found")
    auth.authorize_patient(UUID(req["patient_id"]), user)
    if req["status"] != "proposed":
        raise HTTPException(409, f"this request is already {req['status']}")
    if req["slots"] and body.slot.isoformat() not in req["slots"] and \
            body.slot.astimezone(timezone.utc).isoformat() not in [datetime.fromisoformat(s).astimezone(timezone.utc).isoformat() for s in req["slots"]]:
        raise HTTPException(422, "choose one of the proposed times")
    fac = req["facilities"][body.facility_index] if body.facility_index < len(req["facilities"]) else None
    appt = store.book_care_request(req, fac, body.slot.isoformat())
    return {"appointment_id": appt, "facility": fac, "slot": body.slot.isoformat()}


@router.post("/care-requests/{request_id}/dismiss", status_code=204)
def dismiss(request_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> Response:
    _need_db()
    req = store.get_care_request(request_id)
    if not req:
        raise HTTPException(404, "request not found")
    auth.authorize_patient(UUID(req["patient_id"]), user)
    store.dismiss_care_request(request_id)
    return Response(status_code=204)


# --- Location + nearby care --------------------------------------------------------------------------
class LocationIn(BaseModel):
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    postal_code: Optional[str] = Field(default=None, max_length=12)


@router.put("/patients/{patient_id}/location")
def save_location(patient_id: UUID, body: LocationIn, user: auth.User = Depends(auth.require_user)) -> dict:
    if auth.is_demo(patient_id):
        raise HTTPException(403, "the demo is read-only")
    auth.authorize_patient(patient_id, user)
    _need_db()
    lat, lon, label = body.lat, body.lon, None
    if (lat is None or lon is None) and body.postal_code:
        g = care.geocode(body.postal_code)
        if not g:
            raise HTTPException(422, "we couldn't find that ZIP code")
        lat, lon, label = g
    if lat is None or lon is None:
        raise HTTPException(422, "send coordinates or a ZIP code")
    store.set_location(patient_id, round(lat, 3), round(lon, 3), body.postal_code)  # ~100 m precision is enough
    return {"lat": round(lat, 3), "lon": round(lon, 3), "label": label}


@router.get("/care/nearby")
def nearby(patient_id: Optional[UUID] = None, lat: Optional[float] = None, lon: Optional[float] = None,
           zip: Optional[str] = Query(default=None, max_length=12),
           user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    label = None
    if patient_id and lat is None:
        auth.authorize_patient(patient_id, user)
        prof = store.get_profile(patient_id) or {}
        lat, lon = prof.get("home_lat"), prof.get("home_lon")
        if auth.is_demo(patient_id) and lat is None:
            lat, lon, label = 38.989, -76.943, "College Park, MD (demo)"
    if (lat is None or lon is None) and zip:
        g = care.geocode(zip)
        if not g:
            raise HTTPException(422, "we couldn't find that ZIP code")
        lat, lon, label = g
    if lat is None or lon is None:
        return {"places": [], "needs_location": True}
    places = care.nearby(lat, lon)
    return {"places": places, "label": label, "nearest_er": care.nearest_er(places), "needs_location": False}


# --- Visit summary PDF -----------------------------------------------------------------------
@router.get("/patients/{patient_id}/summary.pdf")
def summary_pdf(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> Response:
    auth.authorize_patient(patient_id, user)
    _need_db()
    from app.summary_pdf import build

    prof = store.get_profile(patient_id)
    if not prof:
        raise HTTPException(404, "patient not found")
    r = watch.run(patient_id, persist=False)
    pdf = build(prof, store.trends(patient_id, 21), r["tiers"], store.upcoming_appointments(patient_id))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="tidewell-visit-summary.pdf"'})


# --- BP cuff photo ---------------------------------------------------------------------------------
class CuffReading(BaseModel):
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
    pulse: Optional[int] = None
    readable: bool = False


@router.post("/vitals/photo")
async def cuff_photo(patient_id: UUID = Form(...), image: UploadFile = File(...),
                     user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    auth.authorize_patient(patient_id, user)
    data = await image.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "photo is too large (max 8 MB)")
    from google.genai import types

    from app.ai._gemini import generate

    try:
        r = generate(
            contents=[types.Part.from_bytes(data=data, mime_type=image.content_type or "image/jpeg"),
                      "Read the blood pressure monitor display in this photo."],
            config=types.GenerateContentConfig(
                system_instruction="Return the systolic (SYS, top), diastolic (DIA, bottom) and pulse numbers "
                                   "shown on the cuff display. If the display isn't readable, set readable=false "
                                   "and leave the numbers null. Never guess.",
                response_mime_type="application/json", response_schema=CuffReading, temperature=0,
            ),
        )
        reading = r.parsed if isinstance(r.parsed, CuffReading) else CuffReading.model_validate_json(r.text or "{}")
    except Exception as e:  # noqa: BLE001
        log.warning("cuff photo failed: %s", e)
        raise HTTPException(502, "we couldn't read the photo; please type the numbers instead") from e
    return {**reading.model_dump(), "needs_confirm": True}


# --- Care Circle -------------------------------------------------------------------------------------
@router.post("/patients/{patient_id}/circle")
def circle_create(patient_id: UUID, user: auth.User = Depends(auth.require_user)) -> dict:
    if auth.is_demo(patient_id):
        raise HTTPException(403, "the demo is read-only")
    auth.authorize_patient(patient_id, user)
    token = secrets.token_urlsafe(18)
    store.set_circle_token(patient_id, hashlib.sha256(token.encode()).hexdigest())
    return {"token": token, "path": f"/circle/{token}"}


@router.delete("/patients/{patient_id}/circle", status_code=204)
def circle_revoke(patient_id: UUID, user: auth.User = Depends(auth.require_user)) -> Response:
    auth.authorize_patient(patient_id, user)
    store.set_circle_token(patient_id, None)
    return Response(status_code=204)


@router.get("/circle/{token}")
def circle_view(token: str) -> dict:
    """Read-only, deliberately limited: how they're doing and how to help. No transcripts, no mood answers."""
    _need_db()
    pid = store.patient_for_circle(hashlib.sha256(token.encode()).hexdigest())
    if not pid:
        raise HTTPException(404, "this link is no longer active")
    prof = store.get_profile(pid)
    pts = store.trends(pid, 7)
    r = watch.run(pid, persist=False)
    sleep = [p["sleep_hrs"] for p in pts if p.get("sleep_hrs") is not None]
    last = store.last_checkin_time(pid)
    tips = {"green": "Things look steady. A meal, a nap, or an hour with the baby goes a long way.",
            "watch": "This week looks harder. Offer to take a night feed so they can sleep, and check in kindly.",
            "amber": "Tidewell suggested a doctor visit soon. Help them book it and get there.",
            "red": "Tidewell flagged something urgent. Make sure they are getting care now."}
    return {
        "name": prof.get("name") or "Your person", "day_postpartum": prof["day_postpartum"],
        "status": r["overall"], "how_to_help": tips[r["overall"]],
        "avg_sleep_7d": round(sum(sleep) / len(sleep), 1) if sleep else None,
        "last_checkin": last.isoformat() if last else None,
        "appointments": [{"slot": a["slot"], "where": a["facility_name"]} for a in store.upcoming_appointments(pid)],
    }


# --- Clinician -------------------------------------------------------------------------------------
@router.get("/clinician/overview")
def clinician_overview(limit: int = Query(100, ge=1, le=1000)) -> dict:
    """Patients sorted by tier with reasons and the Watch agent's note. Hackathon demo: no clinician login yet."""
    _need_db()
    t0 = time.perf_counter()
    with db.connection() as conn:
        rows = conn.execute(
            """
            WITH latest AS (
              SELECT DISTINCT ON (patient_id, category) patient_id, category, tier, reasons, agent_note, time
              FROM risk_assessments WHERE time >= now() - interval '30 days'
              ORDER BY patient_id, category, time DESC)
            SELECT p.id::text AS patient_id, p.name, p.is_synthetic, (current_date - p.birth_date) AS day_postpartum,
                   p.delivery_type,
                   max(CASE l.tier WHEN 'red' THEN 3 WHEN 'amber' THEN 2 WHEN 'watch' THEN 1 ELSE 0 END) AS rank,
                   array_agg(l.category || ': ' || array_to_string(l.reasons, '; ')) FILTER (WHERE l.tier <> 'green') AS reasons,
                   (array_agg(l.agent_note ORDER BY l.time DESC) FILTER (WHERE l.agent_note IS NOT NULL))[1] AS note
            FROM latest l JOIN patients p ON p.id = l.patient_id
            GROUP BY p.id ORDER BY rank DESC, p.name LIMIT %s
            """,
            (limit,),
        ).fetchall()
        appts = conn.execute(
            """SELECT a.patient_id::text, a.slot, a.facility_name, a.clinician_note FROM appointments a
               WHERE a.slot >= now() - interval '1 day' ORDER BY a.slot LIMIT 50"""
        ).fetchall()
    query_ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    with db.connection() as conn:
        agg = conn.execute(
            """SELECT count(DISTINCT patient_id) AS patients, sum(n) AS checkins
               FROM daily_checkins WHERE day >= now() - interval '30 days'"""
        ).fetchone()
    agg_ms = (time.perf_counter() - t1) * 1000
    tier = {3: "red", 2: "amber", 1: "watch", 0: "green"}
    return {
        "patients": [{**r, "overall_tier": tier[r["rank"] or 0], "reasons": r["reasons"] or []} for r in rows],
        "appointments": appts,
        "timing": {"overview_ms": round(query_ms, 1), "aggregate_ms": round(agg_ms, 1),
                   "patients_30d": agg["patients"], "checkins_30d": int(agg["checkins"] or 0)},
    }
