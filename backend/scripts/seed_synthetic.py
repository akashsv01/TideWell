"""Clinic-scale demo data for Tiger Data: N synthetic patients (labelled is_synthetic), 21 days of
check-ins and BP each, assessed by the Watch agent's rules (no Gemini calls, so no quota used).
Run from backend/:  python scripts/seed_synthetic.py [--n 300]   (re-running replaces them)"""
import argparse
import random
import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402

from app.agents.watch import assess  # noqa: E402
from app.config import get_settings  # noqa: E402

NAMES = ["Ava", "Mia", "Zoe", "Noor", "Lena", "Ruth", "Iris", "Jade", "Kira", "Lucia", "Maren", "Priya", "Rosa",
         "Sana", "Tess", "Uma", "Vera", "Wren", "Yara", "Ada", "Bea", "Cora", "Dina", "Esme", "Faye", "Gia"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    n = ap.parse_args().n
    rng = random.Random(42)
    url = get_settings().tiger_database_url
    today = datetime.now(timezone.utc).date()
    with psycopg.connect(url) as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM patients WHERE is_synthetic").fetchall()]
        for t in ("checkins", "vitals", "epds_scores", "risk_assessments", "care_requests", "appointments"):
            conn.execute(f"DELETE FROM {t} WHERE patient_id = ANY(%s)", (ids,))
        conn.execute("DELETE FROM patients WHERE is_synthetic")
        pats, checks, vits, risks = [], [], [], []
        for i in range(n):
            pid = uuid.uuid4()
            day = rng.randint(4, 40)
            csec = rng.random() < 0.32
            htn = rng.random() < 0.15
            mh = rng.random() < 0.2
            kind = rng.choices(["steady", "rising_bp", "low_mood", "poor_sleep"], [0.6, 0.15, 0.15, 0.1])[0]
            prof = {"day_postpartum": day, "delivery_method": "c-section" if csec else "vaginal",
                    "history_mental_health": mh, "history_pregnancy_complications": ["gestational hypertension"] if htn else []}
            pats.append((pid, f"{rng.choice(NAMES)} {chr(65 + i % 26)}.", today - timedelta(days=day), prof["delivery_method"],
                         prof["history_pregnancy_complications"], mh, rng.choice(["breastfeeding", "formula", "mixed"])))
            points = []
            for k in range(min(day, 21)):
                d = today - timedelta(days=min(day, 21) - 1 - k)
                prog = k / 20
                mood = max(0, min(10, round(rng.gauss(7 - (3 * prog if kind == "low_mood" else 0), 1))))
                sleep = max(1.5, round(rng.gauss(4.0 if kind == "poor_sleep" else 5.5, 0.6), 1))
                head = rng.random() < (0.45 if kind == "rising_bp" and prog > 0.6 else 0.08)
                bp = (round(118 + (28 * prog if kind == "rising_bp" else 0) + rng.gauss(0, 3)),
                      round(76 + (16 * prog if kind == "rising_bp" else 0) + rng.gauss(0, 2)))
                ts = datetime.combine(d, time(14), tzinfo=timezone.utc)
                checks.append((ts, pid, mood, rng.randint(1, 4), rng.randint(1, 4) if csec else None, sleep, head))
                if k % 2 == 0 or kind == "rising_bp":
                    vits.append((ts - timedelta(hours=6), pid, bp[0], bp[1]))
                points.append({"mood": mood, "sleep_hrs": sleep, "headache": head, "bp_sys": bp[0], "bp_dia": bp[1],
                               "incision_pain": None, "pain": None})
            for t in assess(prof, points, None, datetime.combine(today, time(14), tzinfo=timezone.utc)):
                risks.append((pid, t["category"], t["tier"], t["score"], t["reasons"], t["next_step"]))
        with conn.cursor() as cur:
            cur.executemany("""INSERT INTO patients (id, name, birth_date, delivery_type, pregnancy_complications,
                               history_mental_health, feeding_type, is_synthetic, consent_granted)
                               VALUES (%s,%s,%s,%s,%s,%s,%s, true, true)""", pats)
            cur.executemany("""INSERT INTO checkins (time, patient_id, mood, pain, incision_pain, sleep_hrs, headache,
                               vision_change, fever, mentions, red_flag) VALUES (%s,%s,%s,%s,%s,%s,%s,false,false,'{}',false)""", checks)
            cur.executemany("INSERT INTO vitals (time, patient_id, bp_sys, bp_dia, source) VALUES (%s,%s,%s,%s,'typed')", vits)
            cur.executemany("""INSERT INTO risk_assessments (patient_id, category, tier, score, reasons, next_step)
                               VALUES (%s,%s,%s,%s,%s,%s)""", risks)
        conn.commit()
    with psycopg.connect(url, autocommit=True) as conn:
        for view in ("daily_metrics", "daily_checkins"):
            conn.execute(f"CALL refresh_continuous_aggregate('{view}', NULL, NULL)")
    print(f"Seeded {n} synthetic patients: {len(checks)} check-ins, {len(vits)} BP readings, {len(risks)} assessments.")


if __name__ == "__main__":
    main()
