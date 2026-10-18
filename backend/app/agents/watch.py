"""Watch agent: continuously analyses each patient's data and flags anything abnormal.

Runs after every saved check-in, daily-log edit and mood check, and every 30 minutes for everyone
(main.py), so a patient who stops checking in is noticed too. Detection is deterministic and uses the
agreed thresholds (clinical_assets/thresholds.md, guidelines.json); Gemini only writes the clinician
note, and only when something needs action (amber/red), which keeps it explainable and cheap.
Amber or red hands off to the Booking agent. It never diagnoses.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app import db, store
from app.agents import booking

log = logging.getLogger("tidewell.watch")

RANK = {"green": 0, "watch": 1, "amber": 2, "red": 3}
SCORE = {"green": 0.1, "watch": 0.4, "amber": 0.75, "red": 1.0}
NEXT_STEP = {
    "green": "Routine daily check-in",
    "watch": "Targeted follow-up tomorrow",
    "amber": "Recommend a visit within 1-3 days and offer times",
    "red": "Urgent care now (911 / emergency room)",
}


def _vals(points: list[dict], key: str) -> list:
    return [p[key] for p in points if p.get(key) is not None]


def _rising(xs: list, n: int = 3) -> bool:
    tail = xs[-n:]
    return len(tail) == n and all(b > a for a, b in zip(tail, tail[1:]))


def assess(profile: dict, points: list[dict], last_epds: Optional[dict], last_checkin: Optional[datetime]) -> list[dict]:
    """Per-category tiers with plain reasons. Pure function (no I/O), so it is easy to test."""
    out = []
    week = points[-7:]

    # High blood pressure (bp-01..03, wsign-01)
    sys_, dia = _vals(points, "bp_sys"), _vals(points, "bp_dia")
    headaches = sum(1 for p in week if p.get("headache"))
    tier, why = "green", []
    if sys_:
        ls, ld = sys_[-1], dia[-1]
        if ls >= 160 or ld >= 110:
            tier, why = "red", [f"Latest blood pressure was {ls}/{ld}, in the severe range (160/110 or higher)"]
        elif ls >= 140 or ld >= 90:
            tier, why = "amber", [f"Latest blood pressure was {ls}/{ld}, at or above the 140/90 limit"]
        if _rising(sys_, 3) and tier != "red":
            why.append(f"Top number rose {len(sys_[-3:])} readings in a row ({', '.join(map(str, sys_[-3:]))})")
            tier = "amber" if headaches >= 3 or tier == "amber" else max(tier, "watch", key=RANK.get)
        if headaches >= 3 and tier in ("green", "watch"):
            tier = "watch"
        if headaches:
            why.append(f"Headaches on {headaches} of the last {len(week)} days")
        if any("hypertension" in c for c in profile.get("history_pregnancy_complications", [])) and tier != "green":
            why.append("History of high blood pressure in pregnancy")
    out.append({"category": "high_blood_pressure", "tier": tier, "reasons": why or ["Blood pressure within range"]})

    # Depression / anxiety (mh-06, mh-07, thresholds.md section 5)
    tier, why = "green", []
    if last_epds:
        age = (datetime.now(timezone.utc) - last_epds["time"]).days
        if last_epds["item10"] and age <= 7:
            tier, why = "amber", ["Mood check mentioned thoughts of self-harm this week"]
        if last_epds["score"] >= 13:
            tier = max(tier, "amber", key=RANK.get)
            why.append(f"Latest mood check scored {last_epds['score']} out of 30, where a follow-up is advised (13 or more)")
        elif last_epds["score"] >= 10:
            tier = max(tier, "watch", key=RANK.get)
            why.append(f"Latest mood check scored {last_epds['score']} out of 30, worth watching (10 to 12)")
    moods = _vals(week, "mood")
    if len(moods) >= 3 and sum(moods) / len(moods) <= 4:
        tier = max(tier, "watch", key=RANK.get)
        why.append(f"Average mood was {sum(moods) / len(moods):.1f} out of 10 this week")
    if profile.get("history_mental_health"):
        tier = max(tier, "watch", key=RANK.get)
        why.append("History of depression or anxiety")
    out.append({"category": "depression_anxiety", "tier": tier, "reasons": why or ["Mood steady"]})

    # Post-cesarean recovery (csec-02)
    if profile.get("delivery_method") == "c-section":
        inc = _vals(points, "incision_pain")
        tier, why = "green", []
        if inc and inc[-1] >= 7:
            tier, why = "amber", [f"Incision pain was {inc[-1]} out of 10"]
        elif _rising(inc, 3):
            tier, why = "watch", [f"Incision pain rising ({', '.join(map(str, inc[-3:]))})"]
        out.append({"category": "post_cesarean", "tier": tier, "reasons": why or ["Incision pain stable or improving"]})

    # Sleep
    sleep = _vals(points[-5:], "sleep_hrs")
    if len(sleep) >= 3 and sum(sleep) / len(sleep) < 4:
        out.append({"category": "sleep", "tier": "watch",
                    "reasons": [f"Averaging {sum(sleep) / len(sleep):.1f} hours of sleep"]})

    # Disengagement
    if last_checkin and profile.get("day_postpartum", 0) >= 3:
        gap = (datetime.now(timezone.utc) - last_checkin).days
        if gap >= 3:
            out.append({"category": "disengagement", "tier": "watch", "reasons": [f"No check-in for {gap} days"]})

    for o in out:
        o["next_step"] = NEXT_STEP[o["tier"]]
        o["score"] = SCORE[o["tier"]]
    return out


def overall(tiers: list[dict]) -> str:
    return max((t["tier"] for t in tiers), key=RANK.get, default="green")


def _note(tiers: list[dict], profile: dict) -> str:
    """Two-sentence factual handoff for the clinician (Gemini, with a plain fallback)."""
    flagged = [f"{t['category']}: {'; '.join(t['reasons'])}" for t in tiers if t["tier"] in ("amber", "red", "watch")]
    fallback = (f"Day {profile.get('day_postpartum')} postpartum ({profile.get('delivery_method')}). "
                + " | ".join(flagged))
    try:
        from google.genai import types

        from app.ai._gemini import generate

        r = generate(
            contents=f"Patient: day {profile.get('day_postpartum')} after a {profile.get('delivery_method')} birth.\n"
                     "Findings:\n" + "\n".join(flagged),
            config=types.GenerateContentConfig(
                system_instruction="Write a 2-sentence factual handoff note for an OB clinician from these "
                                   "self-reported findings. No diagnosis, no treatment advice, no speculation.",
                temperature=0.2,
            ),
        )
        return (r.text or "").strip() or fallback
    except Exception as e:  # noqa: BLE001
        log.info("note fallback (%s)", type(e).__name__)
        return fallback


def run(patient_id: UUID, persist: bool = True) -> dict:
    """Analyse one patient now. Persists the assessment and hands amber/red to the Booking agent."""
    profile = store.get_profile(patient_id)
    if not profile:
        return {"overall": "green", "tiers": [], "care_request": None}
    points = store.trends(patient_id, 14)
    tiers = assess(profile, points, store.last_epds(patient_id), store.last_checkin_time(patient_id))
    level = overall(tiers)
    request = None
    if persist and db.enabled():
        note = None
        if level in ("amber", "red") and not store.open_care_request(patient_id):
            note = _note(tiers, profile)
            request = booking.create_request(patient_id, level, tiers, note, profile)
        store.save_assessment(patient_id, tiers, note)
    return {"overall": level, "tiers": tiers, "care_request": request or store.open_care_request(patient_id)}


def run_safely(patient_id: UUID) -> None:
    try:
        run(patient_id)
    except Exception:  # noqa: BLE001 - analysis must never break a check-in
        log.exception("watch agent failed for %s", patient_id)


def sweep() -> int:
    """Re-analyse every active real patient (called every 30 minutes)."""
    n = 0
    for pid in store.active_patient_ids(days=30):
        run_safely(pid)
        n += 1
    return n
