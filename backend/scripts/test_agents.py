"""End-to-end check of the agents and care features, in-process (no running server needed).
Run from backend/:  .venv/Scripts/python scripts/test_agents.py
Creates a throwaway account and deletes it at the end. Uses the real database."""
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import mail  # noqa: E402
from app.main import app  # noqa: E402

mail._run = lambda fn: None  # never send real welcome emails from the test run

MAYA = "00000000-0000-4000-8000-000000000001"
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail if not cond else ''}")


with TestClient(app) as c:
    r = c.get(f"/patients/{MAYA}/risk").json()
    check("Maya: Watch agent -> amber with reasons", r["overall"] == "amber" and r["tiers"], r.get("overall"))
    check("Maya: demo care proposal (no writes)", r.get("care_request", {}).get("demo") and r["care_request"]["slots"], r.get("care_request"))
    r = c.get(f"/care/nearby?patient_id={MAYA}").json()
    check("nearby care for the demo", len(r["places"]) > 0 and r["nearest_er"], len(r.get("places", [])))
    pdf = c.get(f"/patients/{MAYA}/summary.pdf")
    check("visit summary PDF", pdf.status_code == 200 and pdf.content[:4] == b"%PDF", pdf.status_code)

    tok = c.post("/auth/register", json={"username": "qa_" + secrets.token_hex(3), "password": "a long password 1", "email": "qa@example.invalid"}).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    today = datetime.now(timezone.utc).date()
    pid = c.post("/onboard", headers=H, json={
        "consent_granted": True, "delivery_date": str(today - timedelta(days=12)), "delivery_method": "c-section",
        "feeding_type": "breastfeeding", "history_pregnancy_complications": ["gestational hypertension"],
        "language_preference": "en"}).json()["patient_id"]
    r = c.post("/auth/register", json={"username": "qa_" + secrets.token_hex(3), "password": "a long password 1"})
    check("register without an email is refused", r.status_code == 422, r.status_code)
    r = c.post("/auth/register", json={"username": "qa_" + secrets.token_hex(3), "password": "a long password 1", "email": "not-an-email"})
    check("register with a malformed email is refused", r.status_code == 422, r.status_code)
    # Daily mood check: EPDS total 11 -> mood score 19 (below 20). No support consent, so no text or call.
    r = c.post("/epds", headers=H, json={"patient_id": pid, "answers": [2, 2, 1, 2, 2, 2, 2, 3, 3, 3]}).json()
    check("mood check: EPDS 11 shows as mood score 19", r.get("score") == 11 and r.get("mood_score") == 19, r)
    check("mood score below 20 without consent: support person not contacted", r.get("support_alerted") is False, r)
    ov = c.get(f"/patients/{pid}/overview", headers=H).json()
    check("mood check is daily: not due again today", ov.get("epds_due") is False, ov.get("epds_due"))
    r = c.put(f"/patients/{pid}/location", headers=H, json={"postal_code": "20742"})
    check("save location from ZIP", r.status_code == 200, r.text[:120])
    for i, (s_, d_) in enumerate([(128, 82), (134, 86), (146, 94)]):
        c.put(f"/patients/{pid}/days/{today - timedelta(days=2 - i)}", headers=H,
              json={"mood": 5, "sleep_hrs": 4.5, "headache": i > 0, "bp_sys": s_, "bp_dia": d_})
    r = c.get(f"/patients/{pid}/risk", headers=H).json()
    req = r.get("care_request") or {}
    check("Watch agent flags rising BP -> amber", r["overall"] == "amber", r["overall"])
    check("Booking agent proposes places + times", req.get("slots") and req.get("facilities"), req)
    check("clinician note written", bool(req.get("clinician_note")), req.get("clinician_note"))
    for s_ in req["slots"]:  # real clinics: someone may already hold a time there, so take the first free one
        b = c.post(f"/care-requests/{req['id']}/book", headers=H, json={"slot": s_, "facility_index": 0})
        if b.status_code != 409:
            break
    check("patient books a proposed time", b.status_code == 200, b.text[:200])
    r = c.get(f"/patients/{pid}/risk", headers=H).json()
    check("appointment listed", len(r["appointments"]) == 1, r["appointments"])
    circ = c.post(f"/patients/{pid}/circle", headers=H).json()
    v = c.get(f"/circle/{circ['token']}").json()
    check("Care Circle link shows status + tip", v.get("status") == "amber" and v.get("how_to_help"), v)
    c.delete(f"/patients/{pid}/circle", headers=H)
    check("Care Circle link revoked", c.get(f"/circle/{circ['token']}").status_code == 404)
    ov = c.get("/clinician/overview").json()
    mine = next((p for p in ov["patients"] if p["patient_id"] == pid), None)
    check("clinician overview lists the patient as amber", mine and mine["overall_tier"] == "amber", mine)
    check("Tiger timing reported", ov["timing"]["overview_ms"] >= 0, ov["timing"])
    a = c.post("/ask", headers=H, json={"patient_id": pid, "question": "Is it normal to feel this tired two weeks after birth?"}).json()
    check("Ask Tidewell answers", bool(a.get("answer")), a)
    a = c.post("/ask", headers=H, json={"patient_id": pid, "question": "my vision is blurry and I see spots"}).json()
    check("Ask: safety first (emergency)", a.get("red_flag_level") == "emergency", a)
    a = c.post("/ask", headers=H, json={"patient_id": pid, "question": "Write me a python script that sorts a list"}).json()
    check("Ask: off-topic question declined", a.get("source") == "off_topic" and not a.get("citations"), a)
    a = c.post("/ask", headers=H, json={"patient_id": pid, "question": "How much bleeding is normal two weeks after birth?"}).json()
    check("Ask: on-topic answer has trusted citations", a.get("source") in ("web", "curated") and a.get("citations"), a)
    print("    answer source:", a.get("source"), [x.get("site") for x in a.get("citations", [])])
    for q in ("Give me calming exercises", "How is postpartum depression treated?"):
        a = c.post("/ask", headers=H, json={"patient_id": pid, "question": q}).json()
        check(f"Ask: cited answer for {q!r}", a.get("source") in ("web", "curated") and a.get("citations"), a)
    # --- Apple Health -------------------------------------------------------------------------
    from app import store as st  # noqa: E402
    from scripts.setup_apple_health_test import week_payload  # noqa: E402

    before = st.last_checkin_time(__import__("uuid").UUID(pid))
    imp = c.post("/wearables/import", headers=H, json={"patient_id": pid}).json()
    check("Apple Health: no iPhone -> sample week", imp.get("source") == "sample" and imp["hr_days"] >= 6, imp)
    check("sample keeps the patient's own sleep", imp["kept_own_sleep"] >= 2, imp)
    check("sample data is normal (no alert)", not imp["red_flag"] and imp["latest_bp"]["sys"] < 130, imp)
    pts = c.get(f"/trends/{pid}?range=14d", headers=H).json()
    check("resting heart rate in the tide", any(p.get("resting_hr") for p in pts), pts[-1])
    check("Apple rows don't count as check-ins", st.last_checkin_time(__import__("uuid").UUID(pid)) == before)
    check("sample data removed", c.delete(f"/wearables/sample?patient_id={pid}", headers=H).status_code == 204
          and not any(p.get("resting_hr") for p in c.get(f"/trends/{pid}?range=14d", headers=H).json()))
    check("demo can't import", c.post("/wearables/import", json={"patient_id": MAYA}).status_code == 403)
    check("guide PDF", c.get("/wearables/guide.pdf").content[:4] == b"%PDF")
    code = c.post("/wearables/token", headers=H).json()["code"]
    check("phone needs the code", c.post("/wearables/apple-health", json=week_payload(datetime.now(timezone.utc))).status_code == 401)
    sent_at = datetime.now(timezone.utc)
    r = c.post("/wearables/apple-health", headers={"Authorization": f"Bearer {code}"},
               json=week_payload(sent_at, high_bp=True)).json()
    check("instant check: 162/112 from the phone -> emergency", r.get("alert_level") == "emergency", r)
    al = c.get(f"/wearables/alerts?patient_id={pid}", headers=H).json()["alerts"]
    check("alert waiting for the website", len(al) == 1 and al[0]["bp_sys"] == 162, al)
    r = c.post("/wearables/apple-health", headers={"Authorization": f"Bearer {code}"},
               json=week_payload(sent_at, high_bp=True)).json()
    check("re-sent data doesn't alert twice", r.get("alert_level") is None and r["new_bp_readings"] == 0, r)
    c.post(f"/wearables/alerts/seen?patient_id={pid}", headers=H)
    check("alert marked seen", c.get(f"/wearables/alerts?patient_id={pid}", headers=H).json()["alerts"] == [])
    imp = c.post("/wearables/import", headers=H, json={"patient_id": pid}).json()
    check("with an iPhone -> real data imported", imp.get("source") == "iphone" and imp["bp_added"] >= 3, imp)
    check("import doesn't repeat the alert", not imp["red_flag"], imp)
    status = c.get(f"/wearables/status?patient_id={pid}", headers=H).json()
    check("status shows the phone connected", status["connected"] and status["last_sync"], status)
    check("disconnect", c.delete("/wearables/token", headers=H).status_code == 204
          and c.post("/wearables/apple-health", headers={"Authorization": f"Bearer {code}"}, json={}).status_code == 401)

    # --- Book a visit (providers, in person or video; feature/care-book-appointment) -------------
    from app import provider_mail  # noqa: E402
    from app.config import get_settings as _settings  # noqa: E402

    mails = []
    provider_mail._run = lambda fn: fn()  # run now, not on a thread
    provider_mail.send = lambda event, visit, room: mails.append((event, visit["mode"], room))  # don't email
    provs = c.get("/providers").json()
    check("5 providers, labelled made up", len(provs) == 5 and all(p["is_synthetic"] for p in provs), len(provs))
    okafor = next(p["id"] for p in provs if "Okafor" in p["name"])
    sl = c.get(f"/appointments/slots?provider_id={okafor}&mode=virtual&urgency=routine").json()
    check("open video times", len(sl) > 0, sl[:1])
    r = c.post("/appointments", headers=H, json={"patient_id": pid, "provider_id": okafor, "mode": "virtual",
                                                  "slot": sl[0]["slot"], "reason": "BP check", "urgency": "routine"})
    vis = r.json().get("visit") or {}
    check("book a video visit", r.status_code == 200 and vis.get("mode") == "virtual", r.text[:200])
    check("doctor emailed about the video visit", mails and mails[-1][0] == "booked" and mails[-1][2].startswith("tw-"), mails)
    again = c.post("/appointments", headers=H, json={"patient_id": pid, "provider_id": okafor, "mode": "virtual",
                                                      "slot": sl[0]["slot"], "reason": "x", "urgency": "routine"})
    check("same time can't be booked twice", again.status_code == 409, again.status_code)
    mine = c.get(f"/appointments?patient_id={pid}", headers=H).json()
    kinds = {v["provider"]["kind"] for v in mine}
    check("Your visits lists agent-booked and provider visits", {"clinic", "obstetrics"} <= kinds, kinds)
    agent_visit = next(v for v in mine if v["provider"]["kind"] == "clinic")
    check("agent-booked visit is a real clinic (not 'made up')", not agent_visit["provider"]["is_synthetic"], agent_visit["provider"])
    j = c.post(f"/appointments/{vis['appointment_id']}/join", headers=H)
    if _settings().video_join_anytime:
        check("join opens the WebRTC room", j.status_code == 200 and "room=tw-" in j.json()["url"], j.text[:200])
        doc = c.get(f"/visits/doctor/{mails[-1][2]}", follow_redirects=False)
        check("doctor's emailed link opens the room", doc.status_code == 302 and "role=provider" in doc.headers["location"],
              doc.status_code)
    else:
        check("join waits for the 15-minute window", j.status_code == 409, j.status_code)
    other = c.post("/auth/register", json={"username": "qa_" + secrets.token_hex(3), "password": "a long password 1", "email": "qa@example.invalid"}).json()
    oh = {"Authorization": f"Bearer {other['token']}"}
    # Two people, one time: the booked time is hidden from everyone and comes back after a cancel.
    other_pid = c.post("/onboard", headers=oh, json={
        "consent_granted": True, "delivery_date": str(today - timedelta(days=20)), "delivery_method": "vaginal",
        "feeding_type": "formula", "history_pregnancy_complications": [], "language_preference": "en"}).json()["patient_id"]
    taken = sl[0]["slot"]
    open_now = [x["slot"] for x in c.get(f"/appointments/slots?provider_id={okafor}&mode=virtual&urgency=routine",
                                         headers=oh).json()]
    check("someone else's booked time is hidden from me", taken not in open_now, taken)
    grab = c.post("/appointments", headers=oh, json={"patient_id": other_pid, "provider_id": okafor, "mode": "virtual",
                                                     "slot": taken, "reason": "x", "urgency": "routine"})
    check("and I can't book it", grab.status_code == 409, grab.status_code)
    check("another account can't open my visit",
          c.post(f"/appointments/{vis['appointment_id']}/join", headers=oh).status_code == 403)
    risk_appts = c.get(f"/patients/{pid}/risk", headers=H).json()["appointments"]
    check("Care's upcoming visits marks the video visit", any(a.get("mode") == "virtual" for a in risk_appts), risk_appts)
    ov_appts = c.get("/clinician/overview").json()["appointments"]
    check("clinician sees the video visit", any(a["patient_id"] == pid and "(video)" in (a["facility_name"] or "")
                                                for a in ov_appts), [a for a in ov_appts if a["patient_id"] == pid])
    cx = c.post(f"/appointments/{vis['appointment_id']}/cancel", headers=H).json()
    check("cancel a visit (doctor told)", cx.get("status") == "cancelled" and mails[-1][0] == "cancelled", cx.get("status"))
    reopened = [x["slot"] for x in c.get(f"/appointments/slots?provider_id={okafor}&mode=virtual&urgency=routine",
                                         headers=oh).json()]
    check("after the cancel, the time is open for everyone again", taken in reopened, taken)
    grab = c.post("/appointments", headers=oh, json={"patient_id": other_pid, "provider_id": okafor, "mode": "virtual",
                                                     "slot": taken, "reason": "x", "urgency": "routine"})
    check("and the other person can book it", grab.status_code == 200, grab.text[:200])
    # --- Book at a nearby place (Care near you), shared between people ---------------------------
    from app.routes.appointments import _generate, clinic_slots  # noqa: E402

    check("suggested times are weekdays in the future",
          all(t.weekday() < 5 and t > datetime.now(timezone.utc) for t in _generate("amber") + _generate("watch")))
    place = {"name": "QA Test Clinic " + secrets.token_hex(2), "address": "1 Test St, College Park, MD", "phone": "301-555-0100"}
    ps = c.get("/care/place-slots", params={"name": place["name"]}).json()
    check("open times at a nearby place", len(ps) == len(clinic_slots()), len(ps))
    t0 = ps[0]["slot"]
    r = c.post("/care/book-place", headers=H, json={"patient_id": pid, "place": place, "slot": t0, "reason": "BP check"})
    check("book a visit at a nearby place", r.status_code == 200, r.text[:200])
    place_appt = r.json().get("appointment_id")
    clash = c.post("/care/book-place", headers=H, json={"patient_id": pid, "place": {**place, "name": place["name"] + " B"},
                                                         "slot": t0, "reason": ""})
    check("can't book two visits for myself at the same time", clash.status_code == 409 and "already" in clash.text, clash.text[:120])
    check("that time is gone for everyone", t0 not in [x["slot"] for x in c.get("/care/place-slots", params={"name": place["name"]}).json()])
    r2 = c.post("/care/book-place", headers=oh, json={"patient_id": other_pid, "place": place, "slot": t0, "reason": ""})
    check("a second person can't take it", r2.status_code == 409, r2.status_code)
    mine = c.get(f"/appointments?patient_id={pid}", headers=H).json()
    check("place visit shows in Your visits", any(v["appointment_id"] == place_appt for v in mine))
    c.post(f"/appointments/{place_appt}/cancel", headers=H)
    check("after cancel the time is open again", t0 in [x["slot"] for x in c.get("/care/place-slots", params={"name": place["name"]}).json()])
    r2 = c.post("/care/book-place", headers=oh, json={"patient_id": other_pid, "place": place, "slot": t0, "reason": ""})
    check("and the second person can book it", r2.status_code == 200, r2.text[:200])
    check("demo can't book a clinic", c.post("/care/book-place", json={"patient_id": MAYA, "place": place, "slot": t0}).status_code == 403)
    rk = c.get(f"/patients/{pid}/risk", headers=H).json().get("care_request") or {}
    if rk.get("slots"):
        check("suggested visit has no past times", all(datetime.fromisoformat(x) > datetime.now(timezone.utc) for x in rk["slots"]), rk["slots"])
        check("suggestion says when it was made", bool(rk.get("created_at")) and "outdated" in rk, list(rk))

    c.delete(f"/patients/{other_pid}", headers=oh)  # removes their visit and account
    risk_appts = c.get(f"/patients/{pid}/risk", headers=H).json()["appointments"]
    check("cancelled visits leave Care's upcoming list", all(a.get("mode") != "virtual" for a in risk_appts), risk_appts)

    check("clear saved location",c.delete(f"/patients/{pid}/location", headers=H).status_code == 204)
    check("Care asks for a location again", c.get(f"/care/nearby?patient_id={pid}", headers=H).json().get("needs_location"))
    check("demo location can't be cleared", c.delete(f"/patients/{MAYA}/location", headers=H).status_code == 403)
    check("cleanup", c.delete(f"/patients/{pid}", headers=H).status_code == 204)

# Answer sources: Gemini first, Claude only when Gemini fails or has no trusted citation.
from app.ai import guidelines as g  # noqa: E402


def _fail(_contents):
    calls.append("gemini")
    raise RuntimeError("429 quota")


calls = []
orig = g._gemini_answer, g._claude_answer
web = {"answer": "x", "citations": [{"title": "CDC", "url": "https://cdc.gov"}], "source": "web"}
g._claude_answer = lambda c: calls.append("claude") or web
g._gemini_answer = lambda c: calls.append("gemini") or web
g.ask("q")
check("Gemini answers first; Claude not called", calls == ["gemini"], calls)
calls.clear()
g._gemini_answer = _fail
g.ask("q")
check("Claude is the fallback when Gemini fails", calls == ["gemini", "claude"], calls)
g._gemini_answer, g._claude_answer = orig

print("\nALL PASS" if ok else "\nSOME FAILED")
