"""Twilio SMS to the patient's support person on a Red tier.

The message is fixed text written in advance. No AI wording, ever (plan: "Red ... rules only").
Sends only if the patient gave explicit permission AND a phone number. Never raises: a failed
text must not break the urgent response the patient sees. Phone numbers are never logged.
"""
import logging
from typing import Optional
from uuid import UUID

from app import db, store
from app.config import get_settings

log = logging.getLogger("tidewell.notify")

SUPPORT_MESSAGE = (
    "Tidewell alert: someone you support may need urgent medical care after giving birth. "
    "Please call or check on them right away. If it is an emergency, call 911."
)


def _record(patient_id: UUID, status: str, sid: Optional[str] = None) -> dict:
    log.info("support alert for %s: %s", patient_id, status)
    if db.enabled():
        try:
            store.log_alert(patient_id, status, sid)
        except Exception:  # noqa: BLE001 - audit logging must never break the request
            log.exception("could not write alert_log")
    return {"status": status, "sid": sid}


def send_support_alert(patient_id: UUID) -> dict:
    """Returns {"status": ..., "sid": ...}. status is one of:
    sent | skipped_no_database | skipped_no_patient | skipped_no_consent | skipped_no_phone |
    skipped_not_configured | failed
    """
    if not db.enabled():
        return {"status": "skipped_no_database", "sid": None}
    try:
        patient = store.get_patient(patient_id)
    except Exception:  # noqa: BLE001
        log.exception("could not load patient for alert")
        return {"status": "failed", "sid": None}
    if not patient:
        return {"status": "skipped_no_patient", "sid": None}
    if not patient["support_consent"]:
        return _record(patient_id, "skipped_no_consent")
    if not patient["support_phone"]:
        return _record(patient_id, "skipped_no_phone")

    s = get_settings()
    if not (s.twilio_account_sid and s.twilio_auth_token and s.twilio_from_number):
        return _record(patient_id, "skipped_not_configured")
    try:
        from twilio.rest import Client

        msg = Client(s.twilio_account_sid, s.twilio_auth_token).messages.create(
            to=patient["support_phone"], from_=s.twilio_from_number, body=SUPPORT_MESSAGE
        )
        return _record(patient_id, "sent", msg.sid)
    except Exception:  # noqa: BLE001
        log.exception("twilio send failed")
        return _record(patient_id, "failed")
