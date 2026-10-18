"""Visits: providers, open times, booking (in person or video), your visits, cancel, join.

Without a provider the original behaviour is kept (generic clinic slots, in person) for the voice agent and
the Booking agent, which use _generate below. With a provider, times come from app/booking.py (per-provider
hours; a FHIR/clinic feed can replace booking.candidates later). Red tier never books: it gets the urgent card.
"""
from datetime import datetime, time, timedelta
from typing import Literal, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app import auth, booking, db, store
from app.schemas_data import AppointmentIn, AppointmentOut, JoinOut, ProviderOut, Slot, VisitMode, VisitOut

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


def _raise(e: booking.BookingError):
    raise HTTPException(e.status, e.message) from None


def _authorize_visit(appointment_id: UUID, user: Optional[auth.User]) -> None:
    try:
        owner = booking.visit_owner(appointment_id)
    except booking.BookingError as e:
        _raise(e)
    if db.enabled():
        auth.authorize_patient(owner, user)


@router.get("/providers", response_model=list[ProviderOut])
def providers() -> list[dict]:
    return booking.list_providers()


@router.get("/providers", response_model=list[ProviderOut])
def providers() -> list[dict]:
    return booking.list_providers()


@router.get("/appointments/slots", response_model=list[Slot])
def slots(
    urgency: Literal["watch", "amber", "routine"] = Query("amber"),
    provider_id: Optional[UUID] = None,
    mode: VisitMode = "in_person",
) -> list[Slot]:
    if provider_id is None:  # original behaviour
        candidates = _generate("amber" if urgency == "routine" else urgency)
        if db.enabled():
            taken = store.booked_slots()
            candidates = [c for c in candidates if c not in taken]
        return [Slot(slot=c) for c in candidates]
    try:
        return [Slot(slot=s) for s in booking.open_slots(provider_id, mode, urgency)]
    except booking.BookingError as e:
        _raise(e)


@router.post("/appointments", response_model=AppointmentOut)
def book(body: AppointmentIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> AppointmentOut:
    if body.provider_id is None:  # original behaviour (voice agent / older clients)
        if body.slot.tzinfo is None:
            raise HTTPException(422, "slot must include a timezone offset")
        if not db.enabled():
            return AppointmentOut(appointment_id=uuid4())  # mock mode: nothing is stored
        if not store.patient_exists(body.patient_id):
            raise HTTPException(404, "patient not found")
        if body.slot in store.booked_slots():
            raise HTTPException(409, "that slot was just taken")
        urgency = "amber" if body.urgency == "routine" else body.urgency
        return AppointmentOut(appointment_id=store.insert_appointment(body.patient_id, body.slot, body.reason, urgency))
    if db.enabled():
        auth.authorize_patient(body.patient_id, user)
    try:
        visit = booking.book(body.patient_id, body.provider_id, body.slot, body.mode, body.reason, body.urgency)
    except booking.BookingError as e:
        _raise(e)
    return AppointmentOut(appointment_id=visit["appointment_id"], visit=visit)


@router.get("/appointments", response_model=list[VisitOut])
def my_visits(patient_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> list[dict]:
    if db.enabled():
        auth.authorize_patient(patient_id, user)
    return booking.list_visits(patient_id)


@router.post("/appointments/{appointment_id}/cancel", response_model=VisitOut)
def cancel(appointment_id: UUID, user: Optional[auth.User] = Depends(auth.optional_user)) -> dict:
    _authorize_visit(appointment_id, user)
    try:
        return booking.cancel(appointment_id)
    except booking.BookingError as e:
        _raise(e)


@router.post("/appointments/{appointment_id}/join", response_model=JoinOut)
def join(
    appointment_id: UUID,
    as_: Optional[Literal["provider"]] = Query(None, alias="as"),
    user: Optional[auth.User] = Depends(auth.optional_user),
) -> dict:
    _authorize_visit(appointment_id, user)
    try:
        return booking.join(appointment_id, as_ == "provider")
    except booking.BookingError as e:
        _raise(e)


@router.get("/visits/doctor/{room}", include_in_schema=False)
def doctor_join(room: str):
    """Link in the doctor's email. The room name is the secret; opening it sends the doctor into the call."""
    import html as _html

    try:
        return RedirectResponse(booking.provider_join(room), status_code=302)
    except booking.BookingError as e:
        page = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Tidewell video visit</title><body style="font-family:system-ui,sans-serif;background:#f4f9f9;'
                'color:#0b2545;display:grid;place-items:center;min-height:100vh;margin:0"><main style="max-width:420px;'
                'background:#fff;border-radius:24px;padding:32px;margin:16px"><p style="color:#0e6a70;font-weight:700;'
                f'font-size:22px;margin:0 0 12px">Tidewell</p><p style="font-size:18px;margin:0">{_html.escape(e.message)}</p></main>')
        return HTMLResponse(page, status_code=e.status)
