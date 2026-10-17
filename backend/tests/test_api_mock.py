"""Runs with no database: every route must work on mock data. Run from backend/:  python -m pytest -q"""
import os

os.environ["TIGER_DATABASE_URL"] = ""  # force mock mode even if backend/.env has a real URL

from fastapi.testclient import TestClient  # noqa: E402

from app import categories, demo_data  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()
client = TestClient(app)
MAYA = str(demo_data.MAYA_ID)


def test_health_reports_mock_mode():
    r = client.get("/health").json()
    assert r["status"] == "ok" and "mock" in r["database"]


def test_onboard_assigns_categories_and_returns_uuid():
    body = {"birth_date": "2026-09-29", "delivery_type": "c-section",
            "conditions": ["gestational hypertension"], "breastfeeding": True}
    r = client.post("/onboard", json=body)
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert {"high_blood_pressure", "post_cesarean", "breastfeeding_complications", "depression_anxiety"} <= set(cats)
    assert r.json()["patient_id"]


def test_onboard_rejects_bad_phone():
    body = {"birth_date": "2026-09-29", "delivery_type": "vaginal", "support_phone": "202-555-0123"}
    assert client.post("/onboard", json=body).status_code == 422


def test_maya_story_matches_the_plan():
    cs = demo_data.checkins()
    last7 = cs[-7:]
    assert sum(c["headache"] for c in last7) == 3
    assert round(sum(c["sleep_hrs"] for c in last7) / 7, 1) == 3.8
    assert [(v["bp_sys"], v["bp_dia"]) for v in demo_data.vitals()[-4:]] == [(132, 84), (136, 88), (141, 90), (144, 92)]
    assert [e["score"] for e in demo_data.epds()] == [7, 11]
    assert categories.assign("c-section", ["gestational hypertension", "history of depression"], True)


def test_trends_shape():
    r = client.get(f"/trends/{MAYA}?range=21d").json()
    assert len(r) == demo_data.DAYS
    assert set(r[0]) == {"day", "mood", "pain", "sleep_hrs", "bp_sys", "bp_dia"}
    assert r[-1]["bp_sys"] == 144


def test_trends_range_validation():
    assert client.get(f"/trends/{MAYA}?range=banana").status_code == 422
    assert client.get("/trends/not-a-uuid").status_code == 422


def test_slots_amber_within_three_days_and_watch_later():
    amber = client.get("/appointments/slots?urgency=amber").json()
    watch = client.get("/appointments/slots?urgency=watch").json()
    assert 1 <= len(amber) <= 5 and 1 <= len(watch) <= 5
    assert min(s["slot"] for s in watch) > min(s["slot"] for s in amber)
    assert client.get("/appointments/slots?urgency=red").status_code == 422


def test_book_appointment_mock():
    body = {"patient_id": MAYA, "slot": "2026-10-20T10:00:00-04:00", "reason": "BP check"}
    assert client.post("/appointments", json=body).json()["appointment_id"]
    body["slot"] = "2026-10-20T10:00:00"  # no timezone
    assert client.post("/appointments", json=body).status_code == 422


def test_clinician_list_has_maya_amber():
    r = client.get("/clinician/patients").json()
    assert r[0]["name"] == "Maya" and r[0]["overall_tier"] == "amber"
    assert r[0]["categories"]["depression_anxiety"] == "watch"
    assert any("BP rose" in x for x in r[0]["reasons"])


def test_typed_vitals_red_flag_uses_fixed_urgent_text():
    from app.ai.red_flags import URGENT_RESPONSE
    r = client.post("/vitals", json={"patient_id": MAYA, "bp_sys": 170, "bp_dia": 115}).json()
    assert r["red_flag"] is True and r["urgent_message"] == URGENT_RESPONSE
    ok = client.post("/vitals", json={"patient_id": MAYA, "bp_sys": 118, "bp_dia": 76}).json()
    assert ok["red_flag"] is False and ok["urgent_message"] is None


def test_vitals_validation():
    assert client.post("/vitals", json={"patient_id": MAYA}).status_code == 422
    assert client.post("/vitals", json={"patient_id": MAYA, "bp_sys": 120}).status_code == 422


def test_cors_allows_local_frontend():
    r = client.options("/onboard", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
