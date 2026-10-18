"""Alerts to the patient's support person: an SMS and a voice call.

Two fixed messages, written in advance. No AI wording, ever (plan: "Red ... rules only"):
  urgent: a red-flag check-in, an unsafe blood pressure reading, or a self-harm answer.
  mood:   the daily mood check scored below MOOD_ALERT_BELOW (out of 30, lower is harder).
Sends only if the patient gave explicit permission AND a phone number. SMS goes through Vonage
when it is configured, otherwise Twilio; the call always goes through Twilio and reads the same
words aloud. Never raises: a failed alert must not break the response the patient sees.
Phone numbers are never logged.
"""
import base64
import json
import logging
import urllib.parse
import urllib.request
from typing import Literal, Optional
from uuid import UUID
from xml.sax.saxutils import escape

from app import db, store
from app.config import get_settings

log = logging.getLogger("tidewell.notify")

AlertKind = Literal["urgent", "mood"]

MESSAGES: dict[str, str] = {
    "urgent": (
        "Tidewell alert: someone you support may need urgent medical care after giving birth. "
        "Please call or check on them right away. If it is an emergency, call 911."
    ),
    "mood": (
        "Tidewell: someone you support had a hard mood check-in today. "
        "Please call or check on them. If you think they are in danger, call 911."
    ),
}
# Kept for older imports.
SUPPORT_MESSAGE = MESSAGES["urgent"]


def _record(patient_id: UUID, status: str, sid: Optional[str] = None) -> dict:
    log.info("support alert for %s: %s", patient_id, status)
    if db.enabled():
        try:
            store.log_alert(patient_id, status, sid)
        except Exception:  # noqa: BLE001 - audit logging must never break the request
            log.exception("could not write alert_log")
    return {"status": status, "sid": sid}


def _post(url: str, data: bytes, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _twilio_auth() -> Optional[dict]:
    s = get_settings()
    if not (s.twilio_account_sid and s.twilio_auth_token and s.twilio_from_number):
        return None
    token = base64.b64encode(f"{s.twilio_account_sid}:{s.twilio_auth_token}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"}


def _send_sms(phone: str, text: str) -> dict:
    """{"sms": "sent" | "failed" | "skipped_not_configured", "sid": ...}"""
    s = get_settings()
    if s.vonage_api_key and s.vonage_api_secret:
        try:
            body = json.dumps({
                "from": s.vonage_from_number or "Tidewell", "to": phone.lstrip("+"), "text": text,
                "api_key": s.vonage_api_key, "api_secret": s.vonage_api_secret,
            }).encode()
            msg = (_post("https://rest.nexmo.com/sms/json", body, {"Content-Type": "application/json"}, 10)
                   .get("messages") or [{}])[0]
            if msg.get("status") == "0":
                return {"sms": "sent", "sid": msg.get("message-id")}
            log.error("Vonage SMS refused: %s", msg.get("error-text"))
            return {"sms": "failed", "sid": None}
        except Exception:  # noqa: BLE001
            log.exception("Vonage SMS failed")
            return {"sms": "failed", "sid": None}

    headers = _twilio_auth()
    if not headers:
        return {"sms": "skipped_not_configured", "sid": None}
    try:
        sid = s.twilio_account_sid
        body = urllib.parse.urlencode({"To": phone, "From": s.twilio_from_number, "Body": text}).encode()
        res = _post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", body, headers, 10)
        return {"sms": "sent", "sid": res.get("sid")}
    except Exception:  # noqa: BLE001
        log.exception("Twilio SMS failed")
        return {"sms": "failed", "sid": None}


def _call(phone: str, text: str) -> dict:
    """A Twilio voice call that reads the fixed message twice. {"call": ..., "sid": ...}"""
    s = get_settings()
    headers = _twilio_auth()
    if not headers:
        return {"call": "skipped_not_configured", "sid": None}
    say = f'<Say voice="alice">{escape(text)}</Say>'
    twiml = f'<Response>{say}<Pause length="1"/>{say}</Response>'
    try:
        body = urllib.parse.urlencode({"To": phone, "From": s.twilio_from_number, "Twiml": twiml}).encode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Calls.json"
        res = _post(url, body, headers, 15)
        return {"call": "sent", "sid": res.get("sid")}
    except Exception:  # noqa: BLE001
        log.exception("Twilio voice call failed")
        return {"call": "failed", "sid": None}


def send_support_alert(patient_id: UUID, kind: AlertKind = "urgent") -> dict:
    """Text and call the support person. Returns {"status", "sid", "sms", "call"}; status is one of:
    sent (the SMS or the call went out) | skipped_no_database | skipped_no_patient | skipped_no_consent |
    skipped_no_phone | skipped_not_configured | failed
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

    text = MESSAGES[kind]
    sms = _send_sms(patient["support_phone"], text)
    call = _call(patient["support_phone"], text)
    if "sent" in (sms["sms"], call["call"]):
        status = "sent"
    elif sms["sms"] == call["call"] == "skipped_not_configured":
        status = "skipped_not_configured"
    else:
        status = "failed"
    out = _record(patient_id, f"{status}" if kind == "urgent" else f"{status}_mood", sms["sid"] or call["sid"])
    return {**out, "status": status, "sms": sms["sms"], "call": call["call"]}
