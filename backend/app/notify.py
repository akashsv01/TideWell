"""Outbound notifications — SMS via Vonage + voice call via Twilio for BP red flags."""
import logging
import urllib.parse
import urllib.request
import json
from uuid import UUID

from app import db, store
from app.config import get_settings

log = logging.getLogger("tidewell.notify")

SUPPORT_SMS = (
    "TideWell alert: someone you support may need urgent medical care after giving birth. "
    "Please call or check on them right away. If it is an emergency, call 911."
)

TWIML_URL = "http://demo.twilio.com/docs/voice.xml"


def _record(patient_id: UUID, status: str, sid=None):
    log.info("support alert for %s: %s", patient_id, status)
    if db.enabled():
        try:
            store.log_alert(patient_id, status, sid)
        except Exception:
            log.exception("could not write alert_log")
    return {"status": status, "sid": sid}


def _send_sms(phone: str) -> dict:
    s = get_settings()
    vonage_key = getattr(s, "vonage_api_key", "")
    vonage_secret = getattr(s, "vonage_api_secret", "")
    vonage_from = getattr(s, "vonage_from_number", "TideWell")
    if not vonage_key or not vonage_secret:
        log.warning("Vonage credentials not configured, skipping SMS")
        return {"sms_status": "skipped_no_credentials"}
    try:
        data = json.dumps({
            "from": str(vonage_from),
            "text": SUPPORT_SMS,
            "to": phone.lstrip("+"),
            "api_key": vonage_key,
            "api_secret": vonage_secret,
        }).encode()
        req = urllib.request.Request(
            "https://rest.nexmo.com/sms/json",
            data=data,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        msgs = result.get("messages", [{}])
        status = msgs[0].get("status", "unknown")
        if status == "0":
            log.info("Vonage SMS sent to %s", phone)
            return {"sms_status": "sent"}
        else:
            log.error("Vonage SMS error: %s", msgs[0])
            return {"sms_status": "failed", "error": msgs[0].get("error-text")}
    except Exception:
        log.exception("Vonage SMS send failed")
        return {"sms_status": "failed"}


def _make_voice_call(phone: str) -> dict:
    s = get_settings()
    if not s.twilio_account_sid or not s.twilio_auth_token or not s.twilio_from_number:
        log.warning("Twilio credentials not configured, skipping voice call")
        return {"call_status": "skipped_no_credentials"}
    try:
        import base64
        credentials = base64.b64encode(
            f"{s.twilio_account_sid}:{s.twilio_auth_token}".encode()
        ).decode()
        data = urllib.parse.urlencode({
            "To": phone,
            "From": s.twilio_from_number,
            "Url": TWIML_URL,
        }).encode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Calls.json"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {credentials}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        call_sid = result.get("sid")
        call_status = result.get("status", "unknown")
        log.info("Twilio call to %s: sid=%s status=%s", phone, call_sid, call_status)
        return {"call_status": call_status, "call_sid": call_sid}
    except Exception:
        log.exception("Twilio voice call failed")
        return {"call_status": "failed"}


def send_support_alert(patient_id: UUID) -> dict:
    if not db.enabled():
        return {"status": "skipped_no_database"}
    try:
        patient = store.get_patient(patient_id)
    except Exception:
        log.exception("could not load patient for alert")
        return {"status": "failed"}
    if not patient:
        return {"status": "skipped_no_patient"}
    if not patient["support_consent"]:
        return _record(patient_id, "skipped_no_consent")
    if not patient["support_phone"]:
        return _record(patient_id, "skipped_no_phone")

    phone = patient["support_phone"]
    sms_result = _send_sms(phone)
    call_result = _make_voice_call(phone)

    combined_status = "sent" if (
        sms_result.get("sms_status") == "sent" or
        call_result.get("call_status") not in ("failed", "skipped_no_credentials")
    ) else "failed"

    _record(patient_id, combined_status, call_result.get("call_sid"))
    return {"status": combined_status, "sms": sms_result, "call": call_result}
