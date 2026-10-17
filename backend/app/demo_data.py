"""Maya, the demo patient (plan section 8 worked example, day 18). Pure data, no I/O.

Used by scripts/seed_maya.py to fill Tiger Data and by the routes as mock data when no database
is configured. Deterministic apart from the date, so every run produces the same story.
"""
import random
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

MAYA_ID = UUID("00000000-0000-4000-8000-000000000001")
DAYS = 18  # Maya is on postpartum day 18 "today"

# Day number -> value, for the final week (days 12-18) that the plan's example describes.
_LAST_BP = {12: (132, 84), 14: (136, 88), 16: (141, 90), 18: (144, 92)}  # 4 rising readings
_HEADACHE_DAYS = {13, 16, 18}  # 3 of the last 7 days
_SLEEP_LAST_WEEK = {12: 4.0, 13: 3.5, 14: 4.2, 15: 3.6, 16: 3.9, 17: 3.8, 18: 3.6}  # mean 3.8
_MOOD_LAST_WEEK = {12: 5, 13: 5, 14: 4, 15: 5, 16: 4, 17: 4, 18: 4}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _at(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=timezone.utc)


def patient(today: date | None = None) -> dict:
    today = today or _today()
    return {
        "id": MAYA_ID,
        "name": "Maya",
        "age": 31,
        "language": "en",
        "birth_date": today - timedelta(days=DAYS),
        "delivery_type": "c-section",
        "gestation_weeks": 38,
        "conditions": ["gestational hypertension", "history of depression"],
        "breastfeeding": True,
    }


def checkins(today: date | None = None) -> list[dict]:
    today = today or _today()
    rng = random.Random(7)
    rows = []
    for n in range(1, DAYS + 1):
        d = today - timedelta(days=DAYS - n)
        late = n >= 12
        rows.append({
            "time": _at(d, 14),
            "mood": _MOOD_LAST_WEEK[n] if late else rng.choice([6, 7, 7, 8]),
            "pain": rng.choice([2, 3, 3]) if late else max(2, 6 - n // 2),
            "incision_pain": 3,  # stable
            "sleep_hrs": _SLEEP_LAST_WEEK[n] if late else round(rng.uniform(4.8, 5.8), 1),
            "headache": n in _HEADACHE_DAYS,
            "vision_change": False,
            "bleeding": "light" if n <= 7 else "none",
            "fever": False,
            "mentions": ["headache"] if n in _HEADACHE_DAYS else [],
            "red_flag": False,
        })
    return rows


def vitals(today: date | None = None) -> list[dict]:
    today = today or _today()
    rng = random.Random(11)
    rows = []
    for n in range(1, DAYS + 1):
        d = today - timedelta(days=DAYS - n)
        if n in _LAST_BP:
            sys_, dia = _LAST_BP[n]
        elif n % 2 == 0 and n < 12:
            sys_, dia = rng.randint(116, 124), rng.randint(74, 80)  # baseline
        else:
            continue
        rows.append({
            "time": _at(d, 8), "bp_sys": sys_, "bp_dia": dia,
            "heart_rate": rng.randint(72, 84), "temp_c": 36.8, "glucose": None, "source": "typed",
        })
    return rows


def epds(today: date | None = None) -> list[dict]:
    today = today or _today()
    return [
        {"time": _at(today - timedelta(days=DAYS - 7), 10), "score": 7, "item10": 0},   # week 1
        {"time": _at(today - timedelta(days=DAYS - 14), 10), "score": 11, "item10": 0},  # week 2
    ]


# Placeholder risk output copied from the plan's worked example. Replace with the real risk engine
# (Phase 3); until then it lets /clinician/patients show Maya as Amber.
def risk_assessments() -> list[dict]:
    return [
        {"category": "high_blood_pressure", "tier": "amber", "score": 0.78,
         "reasons": ["BP rose 4 readings in a row", "Headaches 3 of 7 days", "Prior gestational hypertension"],
         "next_step": "Recommend a visit within 1-3 days, offer slots, add to clinician review list"},
        {"category": "depression_anxiety", "tier": "watch", "score": 0.55,
         "reasons": ["EPDS 7 -> 11", "Average sleep 3.8 hrs", "History of depression"],
         "next_step": "Targeted follow-up: repeat screen in 3 days, share support resources"},
        {"category": "post_cesarean", "tier": "green", "score": 0.12,
         "reasons": ["Incision pain stable"], "next_step": "Routine daily check-in"},
    ]


def trend_points(range_days: int = 21, today: date | None = None) -> list[dict]:
    """Mock /trends output: one point per day, built from the same rows the seed script inserts."""
    today = today or _today()
    cutoff = today - timedelta(days=range_days)
    bp = {v["time"].date(): v for v in vitals(today)}
    out = []
    for c in checkins(today):
        d = c["time"].date()
        if d < cutoff:
            continue
        v = bp.get(d)
        out.append({
            "day": d, "mood": c["mood"], "pain": c["pain"], "sleep_hrs": c["sleep_hrs"],
            "bp_sys": v["bp_sys"] if v else None, "bp_dia": v["bp_dia"] if v else None,
        })
    return out
