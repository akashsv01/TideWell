"""Booking agent: turns a Watch-agent flag into a concrete, bookable next step.

Amber -> finds the nearest suitable maternity care (OB-GYN, midwife, hospital) from the patient's
location, proposes appointment times, and writes a short message for the patient. Red never books:
it points to the nearest emergency room. Booking always needs the patient's tap (POST
/care-requests/{id}/book); the agent never books on its own. The clinician note travels with the booking.
Times come from the mock clinic scheduler (app/routes/appointments.py); a FHIR or clinic feed can
replace it later.
"""
import logging
from uuid import UUID

from app import care, store

log = logging.getLogger("tidewell.booking")


def _places(profile: dict) -> list[dict]:
    lat, lon = profile.get("home_lat"), profile.get("home_lon")
    if lat is None or lon is None:
        return []
    return care.nearby(lat, lon, profile.get("postal_code"))


def create_request(patient_id: UUID, level: str, tiers: list[dict], note: str, profile: dict) -> dict:
    from app.routes.appointments import _generate  # mock scheduler

    reasons = [r for t in tiers if t["tier"] in ("amber", "red") for r in t["reasons"]]
    places = _places(profile)
    if level == "red":
        er = care.nearest_er(places)
        facilities = [er] if er else []
        slots: list[str] = []
        msg = ("Some of your numbers need care right now. Please call 911 or go to the nearest emergency room"
               + (f": {er['name']}, about {er['distance_km']} km away." if er else "."))
    else:
        facilities = care.best_for_visit(places)
        slots = [s.isoformat() for s in _generate("amber")[:4]]
        where = f" near you, like {facilities[0]['name']}" if facilities else ""
        msg = ("Your recent check-ins suggest getting seen in the next 1 to 3 days: "
               + "; ".join(reasons[:2]) + f". I found a few places{where}. Pick a time and I'll book it for you.")
        if not facilities:
            msg += " Add your ZIP code on the Care page to see places near you, or call your own provider."
    return store.create_care_request(patient_id, level, reasons, note, msg, facilities, slots)
