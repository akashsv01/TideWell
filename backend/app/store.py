"""All SQL for the data layer in one place. Callers must check db.enabled() first.

Public helpers for Person 1's /checkin pipeline:
    store.save_checkin(patient_id, metrics, red_flag)   # writes checkins (+ vitals if BP was said)
    store.get_patient(patient_id)
    store.patient_context(patient_id)                   # chart + last-7-day summary for the reply
    store.get_backboard_ids / set_backboard_ids         # Backboard memory ids per patient
    store.patient_id_for_clerk(clerk_user_id)           # login -> patient
"""
from datetime import timedelta
from typing import Optional
from uuid import UUID

from app import db
from app.schemas import CheckinMetrics
from app.schemas_data import OnboardIn, VitalsIn


def patient_exists(patient_id: UUID) -> bool:
    with db.connection() as conn:
        return conn.execute("SELECT 1 FROM patients WHERE id = %s", (patient_id,)).fetchone() is not None


def get_patient(patient_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute("SELECT * FROM patients WHERE id = %s", (patient_id,)).fetchone()


def patient_id_for_clerk(clerk_user_id: str) -> Optional[UUID]:
    with db.connection() as conn:
        row = conn.execute("SELECT id FROM patients WHERE clerk_user_id = %s", (clerk_user_id,)).fetchone()
    return row["id"] if row else None


def insert_patient(patient_id: UUID, body: OnboardIn, categories: list[str]) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO patients (id, name, age, language, birth_date, delivery_type, gestation_weeks,
                                  conditions, breastfeeding, support_phone, support_consent, categories,
                                  clerk_user_id)
            VALUES (%(id)s, %(name)s, %(age)s, %(language)s, %(birth_date)s, %(delivery_type)s,
                    %(gestation_weeks)s, %(conditions)s, %(breastfeeding)s, %(support_phone)s,
                    %(support_consent)s, %(categories)s, %(clerk_user_id)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, age = EXCLUDED.age, language = EXCLUDED.language,
                birth_date = EXCLUDED.birth_date, delivery_type = EXCLUDED.delivery_type,
                gestation_weeks = EXCLUDED.gestation_weeks, conditions = EXCLUDED.conditions,
                breastfeeding = EXCLUDED.breastfeeding, support_phone = EXCLUDED.support_phone,
                support_consent = EXCLUDED.support_consent, categories = EXCLUDED.categories,
                clerk_user_id = COALESCE(EXCLUDED.clerk_user_id, patients.clerk_user_id)
            """,
            {
                "id": patient_id, "name": body.name, "age": body.age, "language": body.language,
                "birth_date": body.birth_date, "delivery_type": body.delivery_type,
                "gestation_weeks": body.gestation_weeks, "conditions": body.conditions,
                "breastfeeding": body.breastfeeding,
                "support_phone": body.support_phone,
                # Never record consent without a number to consent about.
                "support_consent": bool(body.support_consent and body.support_phone),
                "categories": categories,
                "clerk_user_id": body.clerk_user_id,
            },
        )


def save_checkin(patient_id: UUID, m: CheckinMetrics, red_flag: bool = False) -> None:
    """One check-in becomes a checkins row, plus a vitals row (source 'voice') if BP was said."""
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO checkins (time, patient_id, mood, pain, incision_pain, sleep_hrs, headache,
                                  vision_change, bleeding, fever, mentions, red_flag)
            VALUES (now(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (patient_id, m.mood, m.pain, m.incision_pain, m.sleep_hrs, m.headache,
             m.vision_change, m.bleeding, m.fever, m.mentions, red_flag),
        )
        if m.bp_sys is not None and m.bp_dia is not None:
            conn.execute(
                "INSERT INTO vitals (time, patient_id, bp_sys, bp_dia, source) VALUES (now(), %s, %s, %s, 'voice')",
                (patient_id, m.bp_sys, m.bp_dia),
            )


def save_vitals(v: VitalsIn) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO vitals (time, patient_id, bp_sys, bp_dia, heart_rate, temp_c, glucose, source)
            VALUES (now(), %s, %s, %s, %s, %s, %s, %s)
            """,
            (v.patient_id, v.bp_sys, v.bp_dia, v.heart_rate, v.temp_c, v.glucose, v.source),
        )


def trends(patient_id: UUID, days: int) -> list[dict]:
    """Daily points from the two continuous aggregates (real-time, so today is included)."""
    with db.connection() as conn:
        return conn.execute(
            """
            SELECT COALESCE(c.day, v.day)::date AS day,
                   round(c.mood)::int AS mood,
                   round(c.pain)::int AS pain,
                   round(c.sleep_hrs::numeric, 1)::float8 AS sleep_hrs,
                   round(v.bp_sys)::int AS bp_sys,
                   round(v.bp_dia)::int AS bp_dia
            FROM (SELECT day, mood, pain, sleep_hrs FROM daily_checkins
                  WHERE patient_id = %(p)s AND day >= now() - %(span)s) c
            FULL OUTER JOIN
                 (SELECT day, bp_sys, bp_dia FROM daily_metrics
                  WHERE patient_id = %(p)s AND day >= now() - %(span)s) v
              ON c.day = v.day
            ORDER BY 1
            """,
            {"p": patient_id, "span": timedelta(days=days)},
        ).fetchall()


def booked_slots() -> set:
    with db.connection() as conn:
        rows = conn.execute("SELECT slot FROM appointments WHERE status = 'booked' AND slot >= now()").fetchall()
    return {r["slot"] for r in rows}


def insert_appointment(patient_id: UUID, slot, reason: str, urgency: str) -> UUID:
    with db.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO appointments (patient_id, slot, reason, urgency, status)
            VALUES (%s, %s, %s, %s, 'booked') RETURNING id
            """,
            (patient_id, slot, reason, urgency),
        ).fetchone()
    return row["id"]


def latest_risk_rows() -> list[dict]:
    """Latest assessment per patient and category, joined to the patient."""
    with db.connection() as conn:
        return conn.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (patient_id, category)
                       patient_id, category, tier, reasons
                FROM risk_assessments
                ORDER BY patient_id, category, time DESC
            )
            SELECT p.id AS patient_id, p.name, p.is_synthetic, l.category, l.tier, l.reasons
            FROM latest l JOIN patients p ON p.id = l.patient_id
            """
        ).fetchall()


def log_alert(patient_id: UUID, status: str, sid: Optional[str] = None) -> None:
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO alert_log (patient_id, status, twilio_sid) VALUES (%s, %s, %s)",
            (patient_id, status, sid),
        )


def get_backboard_ids(patient_id: UUID) -> dict:
    with db.connection() as conn:
        row = conn.execute(
            "SELECT backboard_assistant_id, backboard_thread_id FROM patients WHERE id = %s", (patient_id,)
        ).fetchone()
    if not row or not row["backboard_assistant_id"]:
        return {}
    return {"assistant_id": row["backboard_assistant_id"], "thread_id": row["backboard_thread_id"]}


def set_backboard_ids(patient_id: UUID, assistant_id: str, thread_id: Optional[str]) -> bool:
    """False if the patient row does not exist (the caller falls back to local storage)."""
    with db.connection() as conn:
        cur = conn.execute(
            "UPDATE patients SET backboard_assistant_id = %s, backboard_thread_id = %s WHERE id = %s",
            (assistant_id, thread_id, patient_id),
        )
    return cur.rowcount > 0


def patient_context(patient_id: UUID) -> Optional[dict]:
    """The patient's chart plus a last-7-days summary, for a personalised reply. None if unknown."""
    with db.connection() as conn:
        p = conn.execute(
            """
            SELECT name, birth_date, delivery_type, gestation_weeks, conditions, breastfeeding, language,
                   (current_date - birth_date) AS days_postpartum
            FROM patients WHERE id = %s
            """,
            (patient_id,),
        ).fetchone()
        if not p:
            return None
        week = conn.execute(
            """
            SELECT count(*) AS checkins,
                   round(avg(sleep_hrs)::numeric, 1)::float8 AS avg_sleep,
                   round(avg(mood)::numeric, 1)::float8 AS avg_mood,
                   count(*) FILTER (WHERE headache) AS headache_days
            FROM checkins WHERE patient_id = %s AND time >= now() - interval '7 days'
            """,
            (patient_id,),
        ).fetchone()
        bp = conn.execute(
            """
            SELECT bp_sys, bp_dia FROM vitals
            WHERE patient_id = %s AND bp_sys IS NOT NULL ORDER BY time DESC LIMIT 4
            """,
            (patient_id,),
        ).fetchall()
    return {**p, "week": week, "recent_bp": [f"{r['bp_sys']}/{r['bp_dia']}" for r in reversed(bp)]}


_PATIENT_TABLES = ("checkins", "vitals", "epds_scores", "appointments", "risk_assessments", "alert_log")


def delete_patient(patient_id: UUID) -> bool:
    """Delete everything stored for a patient, in one transaction. False if they did not exist.
    The continuous aggregates (daily_metrics, daily_checkins) drop the rows on their next refresh;
    /trends reads them in real-time mode, so the data disappears immediately."""
    with db.connection() as conn:
        with conn.transaction():
            for table in _PATIENT_TABLES:
                conn.execute(f"DELETE FROM {table} WHERE patient_id = %s", (patient_id,))
            cur = conn.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
    return cur.rowcount > 0


def refresh_today() -> None:
    """Re-materialise today's bucket of the daily aggregates.

    Real-time aggregation only covers time after the last materialised bucket. Once today's bucket
    has been materialised (the seed script refreshes everything, and the policy keeps a 1-hour end
    offset), rows inserted later today would stay invisible on /trends until tomorrow. Called after
    every save; it touches one day, so it is cheap."""
    with db.autocommit_connection() as conn:
        for view in ("daily_checkins", "daily_metrics"):
            conn.execute(
                "CALL refresh_continuous_aggregate(%s::regclass, date_trunc('day', now()),"
                " date_trunc('day', now()) + interval '1 day')",
                (view,),
            )
