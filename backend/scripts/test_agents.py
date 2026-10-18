"""End-to-end check of the agents and care features, in-process (no running server needed).
Run from backend/:  .venv/Scripts/python scripts/test_agents.py
Creates a throwaway account and deletes it at the end. Uses the real database."""
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

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

    tok = c.post("/auth/register", json={"username": "qa_" + secrets.token_hex(3), "password": "a long password 1"}).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    today = datetime.now(timezone.utc).date()
    pid = c.post("/onboard", headers=H, json={
        "consent_granted": True, "delivery_date": str(today - timedelta(days=12)), "delivery_method": "c-section",
        "feeding_type": "breastfeeding", "history_pregnancy_complications": ["gestational hypertension"],
        "language_preference": "en"}).json()["patient_id"]
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
    b = c.post(f"/care-requests/{req['id']}/book", headers=H, json={"slot": req["slots"][0], "facility_index": 0})
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
    check("clear saved location", c.delete(f"/patients/{pid}/location", headers=H).status_code == 204)
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
