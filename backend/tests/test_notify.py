"""Support-person alerts (SMS + voice call) and the welcome email, offline: no network, no database."""
from types import SimpleNamespace
from uuid import uuid4

from app import mail, notify

TWILIO = SimpleNamespace(twilio_account_sid="AC1", twilio_auth_token="t", twilio_from_number="+15550000000",
                         vonage_api_key="", vonage_api_secret="", vonage_from_number="")
NOTHING = SimpleNamespace(twilio_account_sid="", twilio_auth_token="", twilio_from_number="",
                          vonage_api_key="", vonage_api_secret="", vonage_from_number="")


def _setup(monkeypatch, settings, patient):
    calls, logged = [], []

    def fake_post(url, data, headers, timeout):
        calls.append((url, data.decode()))
        return {"sid": "SM1"} if "Messages" in url else {"sid": "CA1"}

    monkeypatch.setattr(notify, "_post", fake_post)
    monkeypatch.setattr(notify, "get_settings", lambda: settings)
    monkeypatch.setattr(notify.db, "enabled", lambda: True)
    monkeypatch.setattr(notify.store, "get_patient", lambda pid: patient)
    monkeypatch.setattr(notify.store, "log_alert", lambda pid, status, sid: logged.append(status))
    return calls, logged


def test_mood_alert_texts_and_calls_with_the_gentle_message(monkeypatch):
    calls, logged = _setup(monkeypatch, TWILIO, {"support_consent": True, "support_phone": "+15551112222"})
    r = notify.send_support_alert(uuid4(), kind="mood")
    assert (r["status"], r["sms"], r["call"]) == ("sent", "sent", "sent")
    sms = next(d for u, d in calls if u.endswith("/Messages.json"))
    call = next(d for u, d in calls if u.endswith("/Calls.json"))
    assert "hard+mood+check-in" in sms
    assert "Twiml=" in call and "hard+mood+check-in" in call  # the call reads the same fixed words
    assert logged == ["sent_mood"]


def test_urgent_alert_uses_the_urgent_message(monkeypatch):
    calls, _ = _setup(monkeypatch, TWILIO, {"support_consent": True, "support_phone": "+15551112222"})
    notify.send_support_alert(uuid4())
    assert all("urgent+medical+care" in d for _, d in calls)


def test_no_consent_no_contact(monkeypatch):
    calls, logged = _setup(monkeypatch, TWILIO, {"support_consent": False, "support_phone": "+15551112222"})
    assert notify.send_support_alert(uuid4(), kind="mood")["status"] == "skipped_no_consent"
    assert calls == [] and logged == ["skipped_no_consent"]


def test_not_configured_is_skipped_not_failed(monkeypatch):
    calls, _ = _setup(monkeypatch, NOTHING, {"support_consent": True, "support_phone": "+15551112222"})
    assert notify.send_support_alert(uuid4())["status"] == "skipped_not_configured"
    assert calls == []


def test_welcome_email_text():
    w = mail.build_welcome("maya")
    assert w["subject"] == "Welcome to Tidewell"
    assert "maya" in w["text"] and "911" in w["text"] and "988" in w["text"]
