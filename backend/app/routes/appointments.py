"""GET /appointments/slots, POST /appointments.

Slots are generated (the plan's mock scheduler; a FHIR/clinic feed can replace _generate later).
Red tier never books: it gets the urgent card instead, so urgency is watch | amber only.
"""
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from app import db, store
from app.schemas_data import AppointmentIn, AppointmentOut, Slot

router = APIRouter()
CLINIC_TZ = ZoneInfo("America/New_York")
# (first_day_offset, last_day_offset): Amber = visit within 1-3 days, Watch = later this week.
_WINDOW = {"amber": (1, 3), "watch": (3, 6)}
_HOURS = (10, 14)


def _generate(urgency: str) -> list[datetime]:
    first, last = _WINDOW[urgency]
    today = datetime.now(CLINIC_TZ).date()
    out = []
    for offset in range(first, last + 1):
        for hour in _HOURS:
            out.append(datetime.combine(today + timedelta(days=offset), time(hour), tzinfo=CLINIC_TZ))
    return out[:5]


@router.get("/appointments/slots", response_model=list[Slot])
def slots(urgency: Literal["watch", "amber"] = Query("amber")) -> list[Slot]:
    candidates = _generate(urgency)
    if db.enabled():
        taken = store.booked_slots()
        candidates = [c for c in candidates if c not in taken]
    return [Slot(slot=c) for c in candidates]


@router.post("/appointments", response_model=AppointmentOut)
def book(body: AppointmentIn) -> AppointmentOut:
    if body.slot.tzinfo is None:
        raise HTTPException(422, "slot must include a timezone offset")
    if not db.enabled():
        from uuid import uuid4
        return AppointmentOut(appointment_id=uuid4())  # mock mode: nothing is stored
    if not store.patient_exists(body.patient_id):
        raise HTTPException(404, "patient not found")
    if body.slot in store.booked_slots():
        raise HTTPException(409, "that slot was just taken")
    return AppointmentOut(appointment_id=store.insert_appointment(body.patient_id, body.slot, body.reason, body.urgency))
