"""Booking in person or by video. Runs with no database (in-memory visits). From backend/:  python -m pytest -q"""
import os

os.environ["TIGER_DATABASE_URL"] = ""
os.environ["DAILY_API_KEY"] = ""

from datetime import datetime, timedelta, timezone  # noqa: E402
from uuid import uuid4  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app import booking, demo_data, video  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()
client = TestClient(app)
MAYA = str(demo_data.MAYA_ID)
OKAFOR = "00000000-0000-4000-8000-0000000000a1"
LACTATION = "00000000-0000-4000-8000-0000000000a4"  # video only


def _first_slot(provider=OKAFOR, mode="in_person", urgency="routine"):
    r = client.get("/appointments/slots", params={"provider_id": provider, "mode": mode, "urgency": urgency})
    assert r.status_code == 200
    return r.json()[0]["slot"]


def _book(patient=None, provider=OKAFOR, mode="in_person", **kw):
    slot = kw.pop("slot", None) or _first_slot(provider, mode)
    body = {"patient_id": patient or str(uuid4()), "provider_id": provider, "mode": mode, "slot": slot,
            "reason": "Blood pressure check", "urgency": "routine", **kw}
    return client.post("/appointments", json=body)


def test_providers_are_seeded_and_labelled_synthetic():
    ps = client.get("/providers").json()
    assert len(ps) >= 4 and all(p["is_synthetic"] for p in ps)
    assert {"in_person", "virtual"} <= {m for p in ps for m in p["modes"]}


def test_slots_are_weekdays_in_the_future_and_respect_mode():
    slots = client.get("/appointments/slots", params={"provider_id": OKAFOR, "mode": "in_person", "urgency": "routine"}).json()
    assert slots
    for s in slots:
        t = datetime.fromisoformat(s["slot"])
        assert t.weekday() < 5 and t > datetime.now(timezone.utc)
    # lactation is video only
    assert client.get("/appointments/slots", params={"provider_id": LACTATION, "mode": "in_person"}).status_code == 422
    assert client.get("/appointments/slots", params={"provider_id": str(uuid4())}).status_code == 404


def test_book_in_person_then_the_slot_is_gone_for_others():
    slot = _first_slot()
    first = _book(slot=slot)
    assert first.status_code == 200
    v = first.json()["visit"]
    assert v["mode"] == "in_person" and v["join"] is None and v["provider"]["address"]
    assert _book(slot=slot).status_code == 409
    assert slot not in [s["slot"] for s in client.get("/appointments/slots", params={"provider_id": OKAFOR, "urgency": "routine"}).json()]


def test_book_rejects_made_up_times_and_missing_timezone():
    assert _book(slot="2026-01-03T10:00:00-05:00").status_code == 409
    assert _book(slot="2026-10-20T10:00:00").status_code == 422


def test_virtual_visit_gets_a_room_and_cannot_be_joined_early_by_a_real_patient():
    pid = str(uuid4())
    r = _book(patient=pid, provider=LACTATION, mode="virtual")
    assert r.status_code == 200
    v = r.json()["visit"]
    assert v["join"]["can_join"] is False
    early = client.post(f"/appointments/{v['appointment_id']}/join")
    assert early.status_code == 409


def test_demo_visit_can_always_be_joined_and_opened_as_provider(monkeypatch):
    v = _book(patient=MAYA, provider=LACTATION, mode="virtual").json()["visit"]
    assert v["join"]["can_join"] is True
    j = client.post(f"/appointments/{v['appointment_id']}/join").json()
    assert j["service"] == "webrtc" and j["url"].startswith("http://localhost:5000/?room=tw-") and j["embeddable"] is False
    assert "role=patient" in j["url"] and "return=http%3A%2F%2Flocalhost%3A3000%2Fvisits" in j["url"]
    assert client.post(f"/appointments/{v['appointment_id']}/join", params={"as": "provider"}).status_code == 200
    # only the demo visit can be opened as the provider
    other = _book(patient=str(uuid4()), provider=LACTATION, mode="virtual").json()["visit"]
    assert client.post(f"/appointments/{other['appointment_id']}/join", params={"as": "provider"}).status_code == 403


def test_in_person_visit_has_nothing_to_join():
    v = _book(patient=MAYA).json()["visit"]
    assert client.post(f"/appointments/{v['appointment_id']}/join").status_code == 422


def test_list_and_cancel_frees_the_slot():
    pid = str(uuid4())
    slot = _first_slot()
    v = _book(patient=pid, slot=slot).json()["visit"]
    mine = client.get("/appointments", params={"patient_id": pid}).json()
    assert [x["appointment_id"] for x in mine] == [v["appointment_id"]]
    c = client.post(f"/appointments/{v['appointment_id']}/cancel")
    assert c.status_code == 200 and c.json()["status"] == "cancelled"
    assert client.post(f"/appointments/{v['appointment_id']}/cancel").status_code == 409
    assert _book(slot=slot).status_code == 200  # someone else can now take it


def test_demo_bookings_never_block_a_slot():
    slot = _first_slot(urgency="routine")
    assert _book(patient=MAYA, slot=slot).status_code == 200
    assert _book(patient=MAYA, slot=slot).status_code == 200


def test_old_clients_without_a_provider_still_book():
    body = {"patient_id": MAYA, "slot": "2026-10-20T10:00:00-04:00", "reason": "BP check"}
    r = client.post("/appointments", json=body)
    assert r.status_code == 200 and r.json()["appointment_id"]


def test_daily_room_and_token_requests(monkeypatch):
    calls = []

    class Resp:
        def __init__(self, data): self.data = data
        def raise_for_status(self): pass
        def json(self): return self.data

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append((url, json))
        if url.endswith("/rooms"):
            return Resp({"name": json["name"], "url": f"https://tidewell.daily.co/{json['name']}"})
        return Resp({"token": "tok123"})

    monkeypatch.setenv("DAILY_API_KEY", "key")
    get_settings.cache_clear()
    monkeypatch.setattr(video.httpx, "post", fake_post)
    try:
        slot = datetime(2026, 11, 2, 10, tzinfo=booking.CLINIC_TZ)
        room = video.create_room(slot)
        assert room["provider"] == "daily"
        body = calls[0][1]
        assert body["privacy"] == "private" and body["properties"]["exp"] == int((slot + video.LATE).timestamp())
        url = video.join_url(room, slot, "Patient")
        assert url.endswith("?t=tok123")
        assert calls[1][1]["properties"]["room_name"] == room["room"]
    finally:
        monkeypatch.delenv("DAILY_API_KEY")
        get_settings.cache_clear()


def test_room_creation_falls_back_to_webrtc_when_daily_is_down(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setenv("DAILY_API_KEY", "key")
    get_settings.cache_clear()
    monkeypatch.setattr(video.httpx, "post", boom)
    try:
        assert video.create_room(datetime.now(timezone.utc) + timedelta(days=1))["provider"] == "webrtc"
    finally:
        monkeypatch.delenv("DAILY_API_KEY")
        get_settings.cache_clear()


def test_legacy_booking_without_provider_still_works():
    """The Booking agent and older clients send no provider_id: original slots and in-person booking."""
    r = client.get("/appointments/slots", params={"urgency": "amber"})
    assert r.status_code == 200 and r.json()
    slot = r.json()[0]["slot"]
    r = client.post("/appointments", json={"patient_id": MAYA, "slot": slot, "reason": "BP check", "urgency": "amber"})
    assert r.status_code == 200 and r.json()["appointment_id"] and r.json()["visit"] is None


def test_booking_agent_scheduler_is_unchanged():
    from app.routes.appointments import _generate
    assert 1 <= len(_generate("amber")) <= 5


def test_old_jitsi_visits_still_join(monkeypatch):
    meeting = {"provider": "jitsi", "room": "tw-old", "url": "https://meet.jit.si/tw-old"}
    assert video.join_url(meeting, datetime.now(timezone.utc), "Patient") == "https://meet.jit.si/tw-old"


def test_webrtc_link_uses_current_setting(monkeypatch):
    monkeypatch.setenv("WEBRTC_BASE_URL", "https://example.ngrok-free.dev/")
    get_settings.cache_clear()
    try:
        meeting = video.create_room(datetime.now(timezone.utc) + timedelta(days=1))
        url = video.join_url(meeting, datetime.now(timezone.utc), "Patient")
        assert url.startswith(f"https://example.ngrok-free.dev/?room={meeting['room']}&role=patient")
    finally:
        monkeypatch.delenv("WEBRTC_BASE_URL")
        get_settings.cache_clear()


# --- doctor email ---------------------------------------------------------------------------
def _sent_emails(monkeypatch, key="re_test", to="doctor@example.com"):
    from app import provider_mail

    monkeypatch.setenv("RESEND_API_KEY", key)
    monkeypatch.setenv("DOCTOR_EMAIL", to)
    get_settings.cache_clear()
    sent = []

    class R:
        def raise_for_status(self):
            pass

    monkeypatch.setattr(provider_mail, "_run", lambda fn: fn())
    monkeypatch.setattr(provider_mail.httpx, "post", lambda url, **kw: sent.append((url, kw)) or R())
    return sent


def test_doctor_gets_an_email_with_a_join_link_for_a_video_visit(monkeypatch):
    sent = _sent_emails(monkeypatch)
    try:
        v = _book(patient=MAYA, provider=LACTATION, mode="virtual", reason="Latch pain").json()["visit"]
        assert len(sent) == 1
        url, kw = sent[0]
        assert url == "https://api.resend.com/emails"
        assert kw["headers"]["Authorization"] == "Bearer re_test" and kw["json"]["to"] == ["doctor@example.com"]
        assert "/visits/doctor/tw-" in kw["json"]["html"] and "Latch pain" in kw["json"]["text"]
        assert "Maya" not in kw["json"]["text"]
        # cancelling tells the doctor too, without a link
        client.post(f"/appointments/{v['appointment_id']}/cancel")
        assert len(sent) == 2 and "cancelled" in sent[1][1]["json"]["subject"].lower()
        assert "/visits/doctor/" not in sent[1][1]["json"]["html"]
    finally:
        monkeypatch.delenv("RESEND_API_KEY")
        monkeypatch.delenv("DOCTOR_EMAIL")
        get_settings.cache_clear()


def test_no_email_for_in_person_visits_or_without_config(monkeypatch):
    sent = _sent_emails(monkeypatch)
    try:
        _book(patient=MAYA, mode="in_person")
        assert sent == []
    finally:
        monkeypatch.delenv("RESEND_API_KEY")
        monkeypatch.delenv("DOCTOR_EMAIL")
        get_settings.cache_clear()
    sent2 = []
    from app import provider_mail

    monkeypatch.setattr(provider_mail, "_run", lambda fn: fn())
    monkeypatch.setattr(provider_mail.httpx, "post", lambda *a, **k: sent2.append(1))
    _book(patient=MAYA, provider=LACTATION, mode="virtual")
    assert sent2 == []  # no key / address set: nothing is sent and booking still works


def test_a_failed_email_does_not_break_booking(monkeypatch):
    from app import provider_mail

    _sent_emails(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("resend down")

    monkeypatch.setattr(provider_mail.httpx, "post", boom)
    try:
        assert _book(patient=MAYA, provider=LACTATION, mode="virtual").status_code == 200
    finally:
        monkeypatch.delenv("RESEND_API_KEY")
        monkeypatch.delenv("DOCTOR_EMAIL")
        get_settings.cache_clear()


def test_doctor_link_redirects_into_the_room_and_is_time_boxed():
    v = _book(patient=MAYA, provider=LACTATION, mode="virtual").json()["visit"]
    room = next(x["meeting_room"] for x in booking._MOCK_VISITS.values() if x["id"] == __import__("uuid").UUID(v["appointment_id"]))
    r = client.get(f"/visits/doctor/{room}", follow_redirects=False)
    assert r.status_code == 302 and "role=provider" in r.headers["location"] and "return=" not in r.headers["location"]
    # a real patient's visit is not open days ahead
    other = _book(patient=str(uuid4()), provider=LACTATION, mode="virtual").json()["visit"]
    room2 = next(x["meeting_room"] for x in booking._MOCK_VISITS.values() if str(x["id"]) == other["appointment_id"])
    early = client.get(f"/visits/doctor/{room2}", follow_redirects=False)
    assert early.status_code == 409 and "15 minutes" in early.text
    assert client.get("/visits/doctor/tw-nope", follow_redirects=False).status_code == 404
    client.post(f"/appointments/{v['appointment_id']}/cancel")
    assert client.get(f"/visits/doctor/{room}", follow_redirects=False).status_code == 410


def test_join_anytime_setting_opens_the_room_for_testing(monkeypatch):
    other = _book(patient=str(uuid4()), provider=LACTATION, mode="virtual").json()["visit"]
    aid = other["appointment_id"]
    assert other["join"]["can_join"] is False
    assert client.post(f"/appointments/{aid}/join").status_code == 409
    monkeypatch.setenv("VIDEO_JOIN_ANYTIME", "true")
    get_settings.cache_clear()
    try:
        assert client.post(f"/appointments/{aid}/join").status_code == 200
        room = next(x["meeting_room"] for x in booking._MOCK_VISITS.values() if str(x["id"]) == aid)
        assert client.get(f"/visits/doctor/{room}", follow_redirects=False).status_code == 302
    finally:
        monkeypatch.delenv("VIDEO_JOIN_ANYTIME")
        get_settings.cache_clear()
    assert client.post(f"/appointments/{aid}/join").status_code == 409
