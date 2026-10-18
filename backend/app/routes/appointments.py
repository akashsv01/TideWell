"""Visits: providers, open times, booking (in person or video), your visits, cancel, join.

Slots are generated per provider (the plan's mock scheduler; a FHIR/clinic feed can replace
booking.candidates later). Red tier never books: it gets the urgent card instead.
Without provider_id the old behaviour is kept (default clinic, in person) for the voice agent.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app import auth, booking, db
from app.schemas_data import AppointmentIn, AppointmentOut, JoinOut, ProviderOut, Slot, VisitMode, VisitOut

router = APIRouter()


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


@router.get("/appointments/slots", response_model=list[Slot])
def slots(
    urgency: Literal["watch", "amber", "routine"] = Query("amber"),
    provider_id: Optional[UUID] = None,
    mode: VisitMode = "in_person",
) -> list[Slot]:
    try:
        pid = provider_id or booking.DEFAULT_PROVIDER_ID
        return [Slot(slot=s) for s in booking.open_slots(pid, mode, urgency)]
    except booking.BookingError as e:
        _raise(e)


@router.post("/appointments", response_model=AppointmentOut)
def book(body: AppointmentIn, user: Optional[auth.User] = Depends(auth.optional_user)) -> AppointmentOut:
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
