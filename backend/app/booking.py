"""Booking service: providers, open times, booking, listing, cancelling and joining a video visit.

Shared by the HTTP routes and the voice agent tools so there is one set of rules. With no database
(mock mode) visits live in memory, so the whole flow works for frontend work and demos.
"""
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app import db, demo_data, provider_mail, store, video
from app.config import get_settings
from app.providers_data import PROVIDERS, PROVIDERS_BY_ID

CLINIC_TZ = ZoneInfo("America/New_York")
# (first_day_offset, last_day_offset, max_slots). Amber = soon, watch = later this week, routine = any time.
_WINDOW = {"amber": (1, 3, 5), "watch": (3, 6, 5), "routine": (1, 10, 30)}
_MOCK_VISITS: dict[UUID, dict] = {}


def _anytime() -> bool:
    """VIDEO_JOIN_ANYTIME=true (testing only) switches the join time window off."""
    return get_settings().video_join_anytime


class BookingError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


# --- Providers -----------------------------------------------------------------------------
def list_providers() -> list[dict]:
    return store.list_providers() if db.enabled() else list(PROVIDERS)


def get_provider(provider_id: UUID) -> Optional[dict]:
    return store.get_provider(provider_id) if db.enabled() else PROVIDERS_BY_ID.get(provider_id)


# --- Open times ----------------------------------------------------------------------------
def candidates(provider: dict, urgency: str, now: Optional[datetime] = None) -> list[datetime]:
    first, last, cap = _WINDOW[urgency]
    now = now or datetime.now(CLINIC_TZ)
    today = now.astimezone(CLINIC_TZ).date()
    out = []
    for offset in range(first, last + 1):
        day = today + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        for hour in sorted(provider["hours"]):
            out.append(datetime.combine(day, time(hour), tzinfo=CLINIC_TZ))
    return out[:cap]


def _taken(provider_id: UUID) -> set:
    if db.enabled():
        return store.provider_booked_slots(provider_id)
    return {v["slot"] for v in _MOCK_VISITS.values()
            if v["provider_id"] == provider_id and v["status"] == "booked" and v["patient_id"] != demo_data.MAYA_ID}


def open_slots(provider_id: UUID, mode: str, urgency: str) -> list[datetime]:
    provider = get_provider(provider_id)
    if provider is None:
        raise BookingError(404, "provider not found")
    if mode not in provider["modes"]:
        raise BookingError(422, "this provider does not offer that kind of visit")
    taken = _taken(provider_id)
    return [c for c in candidates(provider, urgency) if c not in taken]


# --- Booking -------------------------------------------------------------------------------
def _public_visit(row: dict) -> dict:
    """Row (from the DB join or the mock store) -> VisitOut-shaped dict."""
    provider = {
        "id": row["provider_id"], "name": row["provider_name"], "specialty": row["provider_specialty"],
        "kind": row["provider_kind"], "clinic": row["provider_clinic"], "address": row["provider_address"],
        "modes": row["provider_modes"],
        "bio": None, "is_synthetic": row.get("provider_synthetic", True),
    }
    out = {
        "appointment_id": row["id"], "patient_id": row["patient_id"], "provider": provider, "slot": row["slot"],
        "mode": row["mode"], "reason": row["reason"], "urgency": row["urgency"], "status": row["status"],
        "join": None,
    }
    if row["mode"] == "virtual" and row["status"] == "booked":
        opens, closes = video.window(row["slot"])
        now = datetime.now(timezone.utc)
        demo = row["patient_id"] == demo_data.MAYA_ID  # the demo can always be tried
        out["join"] = {"can_join": demo or _anytime() or opens <= now <= closes, "opens_at": opens, "closes_at": closes}
    return out


def book(patient_id: UUID, provider_id: UUID, slot: datetime, mode: str, reason: str, urgency: str) -> dict:
    if slot.tzinfo is None:
        raise BookingError(422, "slot must include a timezone offset")
    provider = get_provider(provider_id)
    if provider is None:
        raise BookingError(404, "provider not found")
    if mode not in provider["modes"]:
        raise BookingError(422, "this provider does not offer that kind of visit")
    if db.enabled() and not store.patient_exists(patient_id):
        raise BookingError(404, "patient not found")
    if slot not in set(candidates(provider, urgency)):
        raise BookingError(409, "that time is not available")
    if slot in _taken(provider["id"]):
        raise BookingError(409, "that time was just taken")
    if db.enabled() and patient_id != demo_data.MAYA_ID and store.patient_busy(patient_id, slot):
        raise BookingError(409, "you already have a visit at that time; choose another")
    meeting = video.create_room(slot) if mode == "virtual" else None
    if db.enabled():
        try:
            new_id = store.insert_visit(patient_id, provider["id"], slot, mode, reason, urgency, meeting)
        except store.SlotTaken:
            raise BookingError(409, "that time was just taken") from None
        row = store.get_visit(new_id)
    else:
        new_id = uuid4()
        row = {
            "id": new_id, "patient_id": patient_id, "provider_id": provider["id"], "slot": slot, "mode": mode,
            "reason": reason, "urgency": urgency, "status": "booked",
            "meeting_provider": (meeting or {}).get("provider"), "meeting_room": (meeting or {}).get("room"),
            "meeting_url": (meeting or {}).get("url"),
            "provider_name": provider["name"], "provider_specialty": provider["specialty"],
            "provider_kind": provider["kind"], "provider_modes": provider["modes"], "provider_clinic": provider["clinic"],
            "provider_address": provider["address"],
        }
        _MOCK_VISITS[new_id] = {**row}
    out = _public_visit(row)
    provider_mail.notify("booked", out, row["meeting_room"] or "")
    return out


# --- Listing, cancelling, joining ----------------------------------------------------------
def _get_row(appointment_id: UUID) -> Optional[dict]:
    return store.get_visit(appointment_id) if db.enabled() else _MOCK_VISITS.get(appointment_id)


def list_visits(patient_id: UUID) -> list[dict]:
    if db.enabled():
        rows = [r for r in store.list_visits(patient_id)]
    else:
        rows = sorted((v for v in _MOCK_VISITS.values() if v["patient_id"] == patient_id), key=lambda v: v["slot"])
    return [_public_visit(r) for r in rows]


def visit_owner(appointment_id: UUID) -> UUID:
    row = _get_row(appointment_id)
    if row is None:
        raise BookingError(404, "visit not found")
    return row["patient_id"]


def cancel(appointment_id: UUID) -> dict:
    row = _get_row(appointment_id)
    if row is None:
        raise BookingError(404, "visit not found")
    if row["status"] != "booked":
        raise BookingError(409, "this visit is already cancelled")
    if db.enabled():
        store.cancel_visit(appointment_id)
        row = store.get_visit(appointment_id)
    else:
        row["status"] = "cancelled"
    out = _public_visit(row)
    provider_mail.notify("cancelled", out, row["meeting_room"] or "")
    return out


def join(appointment_id: UUID, as_provider: bool = False) -> dict:
    row = _get_row(appointment_id)
    if row is None or row["status"] != "booked":
        raise BookingError(404, "visit not found")
    if row["mode"] != "virtual" or not row["meeting_room"]:
        raise BookingError(422, "this is an in-person visit")
    demo = row["patient_id"] == demo_data.MAYA_ID
    if as_provider and not demo:
        raise BookingError(403, "only the demo visit can be opened as the provider")
    opens, closes = video.window(row["slot"])
    if not demo and not _anytime() and not (opens <= datetime.now(timezone.utc) <= closes):
        raise BookingError(409, "the video room opens 15 minutes before the visit")
    meeting = {"provider": row["meeting_provider"], "room": row["meeting_room"], "url": row["meeting_url"]}
    name = row["provider_name"] if as_provider else "Patient"
    try:
        url = video.join_url(meeting, row["slot"], name, owner=as_provider)
    except Exception:  # noqa: BLE001
        raise BookingError(502, "Video is unavailable right now. Try again in a minute.") from None
    return {"url": url, "service": meeting["provider"], "embeddable": meeting["provider"] == "daily"}


def provider_join(room: str) -> str:
    """The doctor's emailed link: check the visit, then return the URL of the video room (doctor side)."""
    row = store.get_visit_by_room(room) if db.enabled() else next(
        (v for v in _MOCK_VISITS.values() if v["meeting_room"] == room), None)
    if row is None:
        raise BookingError(404, "We could not find this visit.")
    if row["status"] != "booked":
        raise BookingError(410, "This visit was cancelled.")
    opens, closes = video.window(row["slot"])
    now = datetime.now(timezone.utc)
    if row["patient_id"] != demo_data.MAYA_ID and not _anytime():
        if now < opens:
            raise BookingError(409, "The video room is not open yet. It opens 15 minutes before the visit.")
        if now > closes:
            raise BookingError(410, "This visit has ended.")
    meeting = {"provider": row["meeting_provider"], "room": row["meeting_room"], "url": row["meeting_url"]}
    try:
        return video.join_url(meeting, row["slot"], row["provider_name"], owner=True)
    except Exception:  # noqa: BLE001
        raise BookingError(502, "Video is unavailable right now. Try the link again in a minute.") from None
