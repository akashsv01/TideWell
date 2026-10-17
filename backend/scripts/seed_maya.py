"""Seed the demo patient Maya (plan section 8 worked example, postpartum day 18).
Run from backend/:  python scripts/seed_maya.py [--support-phone +1XXXXXXXXXX]

Re-running replaces Maya's rows only (fixed id 00000000-0000-4000-8000-000000000001); other patients are
untouched. With --support-phone, Maya's support person is set and consent is recorded, so the Red-flag
text goes to that number. Use a phone you control and have verified in Twilio.
Risk rows are the plan's example output, a placeholder until the real risk engine writes them."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402

from app import categories, demo_data  # noqa: E402
from app.config import get_settings  # noqa: E402

TABLES = ("checkins", "vitals", "epds_scores", "risk_assessments", "appointments", "alert_log")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--support-phone", default=None, help="E.164, e.g. +12025550123")
    args = ap.parse_args()
    url = get_settings().tiger_database_url
    if not url:
        sys.exit("TIGER_DATABASE_URL is empty. Put the Tiger connection string in backend/.env first.")

    p = demo_data.patient()
    mid = demo_data.MAYA_ID
    cats = categories.assign(p["delivery_type"], p["conditions"], p["breastfeeding"])

    with psycopg.connect(url) as conn:
        for t in TABLES:
            conn.execute(f"DELETE FROM {t} WHERE patient_id = %s", (mid,))
        conn.execute("DELETE FROM patients WHERE id = %s", (mid,))
        conn.execute(
            """INSERT INTO patients (id, name, age, language, birth_date, delivery_type, gestation_weeks,
                   conditions, breastfeeding, support_phone, support_consent, categories,
                   consent_granted, consent_at, feeding_type, history_mental_health,
                   pregnancy_complications, support_person_name)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, true, now(), %s,%s,%s,%s)""",
            (mid, p["name"], p["age"], p["language"], p["birth_date"], p["delivery_type"],
             p["gestation_weeks"], p["conditions"], p["breastfeeding"],
             args.support_phone, bool(args.support_phone), cats,
             p["feeding_type"], p["history_mental_health"], p["pregnancy_complications"],
             p["support_person_name"]),
        )
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO checkins (time, patient_id, mood, pain, incision_pain, sleep_hrs, headache,
                       vision_change, bleeding, fever, mentions, red_flag)
                   VALUES (%(time)s, %(pid)s, %(mood)s, %(pain)s, %(incision_pain)s, %(sleep_hrs)s, %(headache)s,
                       %(vision_change)s, %(bleeding)s, %(fever)s, %(mentions)s, %(red_flag)s)""",
                [{**c, "pid": mid} for c in demo_data.checkins()],
            )
            cur.executemany(
                """INSERT INTO vitals (time, patient_id, bp_sys, bp_dia, heart_rate, temp_c, glucose, source)
                   VALUES (%(time)s, %(pid)s, %(bp_sys)s, %(bp_dia)s, %(heart_rate)s, %(temp_c)s, %(glucose)s, %(source)s)""",
                [{**v, "pid": mid} for v in demo_data.vitals()],
            )
            cur.executemany(
                "INSERT INTO epds_scores (time, patient_id, score, item10) VALUES (%(time)s, %(pid)s, %(score)s, %(item10)s)",
                [{**e, "pid": mid} for e in demo_data.epds()],
            )
            cur.executemany(
                """INSERT INTO risk_assessments (patient_id, category, tier, score, reasons, next_step)
                   VALUES (%(pid)s, %(category)s, %(tier)s, %(score)s, %(reasons)s, %(next_step)s)""",
                [{**r, "pid": mid} for r in demo_data.risk_assessments()],
            )
        conn.commit()

    # Refresh needs autocommit (cannot run inside a transaction block).
    with psycopg.connect(url, autocommit=True) as conn:
        for view in ("daily_metrics", "daily_checkins"):
            conn.execute(f"CALL refresh_continuous_aggregate('{view}', NULL, NULL)")
    print(f"Seeded Maya ({mid}): {len(demo_data.checkins())} check-ins, {len(demo_data.vitals())} BP readings, "
          f"{len(demo_data.epds())} EPDS scores. Try GET /trends/{mid}?range=21d")


if __name__ == "__main__":
    main()
