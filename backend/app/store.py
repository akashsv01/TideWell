"""All SQL for the data layer in one place. Callers must check db.enabled() first.

Public helpers for Person 1's /checkin pipeline:
    store.save_checkin(patient_id, metrics, red_flag)   # writes checkins (+ vitals if BP was said)
    store.get_patient(patient_id)
    store.patient_context(patient_id)                   # chart + last-7-day summary for the reply
    store.get_backboard_ids / set_backboard_ids         # Backboard memory ids per patient
    store.upsert_profile / get_profile / overview       # the onboarding baseline profile
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

from app import db, demo_data
from app.schemas import CheckinMetrics, Profile
from app.schemas_data import VitalsIn

MENTAL_HEALTH_CONDITION = "history of depression or anxiety"


def patient_exists(patient_id: UUID) -> bool:
    with db.connection() as conn:
        return conn.execute("SELECT 1 FROM patients WHERE id = %s", (patient_id,)).fetchone() is not None


def get_patient(patient_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute("SELECT * FROM patients WHERE id = %s", (patient_id,)).fetchone()


def derived_conditions(p: Profile) -> list[str]:
    """`conditions` feeds the category rules and the reply context."""
    out = list(p.history_pregnancy_complications)
    if p.history_mental_health:
        out.append(MENTAL_HEALTH_CONDITION)
    return out


def upsert_profile(user_id: UUID, p: Profile, categories: list[str]) -> UUID:
    """Create this account's patient record, or update it. Returns the patient id."""
    with db.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO patients (user_id, name, language, birth_date, delivery_type, gestation_weeks,
                                  conditions, breastfeeding, support_phone, support_consent, categories,
                                  consent_granted, consent_at, feeding_type, history_mental_health,
                                  pregnancy_complications, support_person_name)
            VALUES (%(user_id)s, %(name)s, %(language)s, %(birth_date)s, %(delivery_type)s, %(gestation_weeks)s,
                    %(conditions)s, %(breastfeeding)s, %(support_phone)s, %(support_consent)s, %(categories)s,
                    true, now(), %(feeding_type)s, %(history_mental_health)s,
                    %(complications)s, %(support_name)s)
            ON CONFLICT (user_id) WHERE user_id IS NOT NULL DO UPDATE SET
                name = EXCLUDED.name, language = EXCLUDED.language, birth_date = EXCLUDED.birth_date,
                delivery_type = EXCLUDED.delivery_type, gestation_weeks = EXCLUDED.gestation_weeks,
                conditions = EXCLUDED.conditions, breastfeeding = EXCLUDED.breastfeeding,
                support_phone = EXCLUDED.support_phone, support_consent = EXCLUDED.support_consent,
                categories = EXCLUDED.categories, feeding_type = EXCLUDED.feeding_type,
                history_mental_health = EXCLUDED.history_mental_health,
                pregnancy_complications = EXCLUDED.pregnancy_complications,
                support_person_name = EXCLUDED.support_person_name
            RETURNING id
            """,
            {
                "user_id": user_id, "name": p.name, "language": p.language_preference,
                "birth_date": p.delivery_date, "delivery_type": p.delivery_method,
                "gestation_weeks": p.gestation_weeks, "conditions": derived_conditions(p),
                "breastfeeding": p.feeding_type in ("breastfeeding", "mixed"),
                "support_phone": p.support_person_phone,
                # Never record SMS consent without a number to consent about.
                "support_consent": bool(p.support_sms_consent and p.support_person_phone),
                "categories": categories, "feeding_type": p.feeding_type,
                "history_mental_health": p.history_mental_health,
                "complications": p.history_pregnancy_complications,
                "support_name": p.support_person_name,
            },
        ).fetchone()
    return row["id"]


def get_profile(patient_id: UUID) -> Optional[dict]:
    """The profile in API field names, plus day_postpartum and categories. None if unknown."""
    with db.connection() as conn:
        r = conn.execute(
            """
            SELECT id, name, birth_date, delivery_type, gestation_weeks, feeding_type, breastfeeding,
                   history_mental_health, pregnancy_complications, language, support_person_name,
                   support_phone, support_consent, consent_granted, categories,
                   postal_code, home_lat, home_lon,
                   (current_date - birth_date) AS day_postpartum
            FROM patients WHERE id = %s
            """,
            (patient_id,),
        ).fetchone()
    if not r:
        return None
    return {
        "patient_id": str(r["id"]), "name": r["name"], "consent_granted": r["consent_granted"],
        "delivery_date": r["birth_date"], "gestation_weeks": r["gestation_weeks"],
        "delivery_method": r["delivery_type"],
        "feeding_type": r["feeding_type"] or ("breastfeeding" if r["breastfeeding"] else "formula"),
        "history_mental_health": r["history_mental_health"],
        "history_pregnancy_complications": r["pregnancy_complications"] or [],
        "language_preference": r["language"] if r["language"] in ("en", "es") else "en",
        "support_person_name": r["support_person_name"], "support_person_phone": r["support_phone"],
        "support_sms_consent": r["support_consent"], "day_postpartum": r["day_postpartum"],
        "categories": r["categories"] or [],
        "postal_code": r["postal_code"], "home_lat": r["home_lat"], "home_lon": r["home_lon"],
    }


def owner_of(patient_id: UUID) -> Optional[UUID]:
    with db.connection() as conn:
        row = conn.execute("SELECT user_id FROM patients WHERE id = %s", (patient_id,)).fetchone()
    return row["user_id"] if row else None


def save_epds(patient_id: UUID, total: int, item10: int, answers: Optional[list[int]] = None) -> None:
    """One mood check per (UTC) day: a retake the same day replaces the earlier answers."""
    with db.connection() as conn:
        conn.execute(
            "DELETE FROM epds_scores WHERE patient_id = %s AND time >= date_trunc('day', now())",
            (patient_id,),
        )
        conn.execute(
            "INSERT INTO epds_scores (time, patient_id, score, item10, answers) VALUES (now(), %s, %s, %s, %s)",
            (patient_id, total, item10, answers),
        )


def last_epds(patient_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute(
            "SELECT time, score, item10 FROM epds_scores WHERE patient_id = %s ORDER BY time DESC LIMIT 1",
            (patient_id,),
        ).fetchone()


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
    """Daily points: check-ins and BP from the two continuous aggregates (real-time, so today is
    included), plus the weekly EPDS score on the day it was taken. day_postpartum is counted from
    the delivery date."""
    with db.connection() as conn:
        return conn.execute(
            """
            WITH c AS (SELECT day, mood, pain, incision_pain, sleep_hrs, headache_count FROM daily_checkins
                       WHERE patient_id = %(p)s AND day >= now() - %(span)s),
                 v AS (SELECT day, bp_sys, bp_dia FROM daily_metrics
                       WHERE patient_id = %(p)s AND day >= now() - %(span)s),
                 e AS (SELECT time_bucket('1 day', time) AS day, max(score) AS score, max(item10) AS item10
                       FROM epds_scores WHERE patient_id = %(p)s AND time >= now() - %(span)s
                       GROUP BY 1),
                 days AS (SELECT day FROM c UNION SELECT day FROM v UNION SELECT day FROM e)
            SELECT d.day::date AS day,
                   (d.day::date - (SELECT birth_date FROM patients WHERE id = %(p)s)) AS day_postpartum,
                   round(c.mood)::int AS mood,
                   round(c.pain)::int AS pain,
                   round(c.incision_pain)::int AS incision_pain,
                   round(c.sleep_hrs::numeric, 1)::float8 AS sleep_hrs,
                   COALESCE(c.headache_count, 0) > 0 AS headache,
                   round(v.bp_sys)::int AS bp_sys,
                   round(v.bp_dia)::int AS bp_dia,
                   e.score AS epds_score,
                   COALESCE(e.item10, 0) > 0 AS item_10_alert
            FROM days d
            LEFT JOIN c ON c.day = d.day
            LEFT JOIN v ON v.day = d.day
            LEFT JOIN e ON e.day = d.day
            ORDER BY 1
            """,
            {"p": patient_id, "span": timedelta(days=days)},
        ).fetchall()


def epds_due(day_postpartum: int, last: Optional[dict], today: Optional[date] = None) -> bool:
    """Weekly from day 7: due when there is no score in the last 7 days."""
    if day_postpartum < 7:
        return False
    if not last:
        return True
    today = today or date.today()
    return (today - last["time"].date()).days >= 7


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


# --- Providers and visits ----------------------------------------------------------------
_PROVIDER_COLS = "id, name, specialty, kind, bio, modes, clinic, address, hours, is_synthetic"


def upsert_providers(conn, providers: list[dict]) -> None:
    """Used by scripts/migrate.py with a plain psycopg connection. Idempotent."""
    for p in providers:
        conn.execute(
            """
            INSERT INTO providers (id, name, specialty, kind, bio, modes, clinic, address, hours, is_synthetic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, specialty = EXCLUDED.specialty,
                kind = EXCLUDED.kind, bio = EXCLUDED.bio, modes = EXCLUDED.modes, clinic = EXCLUDED.clinic,
                address = EXCLUDED.address, hours = EXCLUDED.hours, active = true
            """,
            (p["id"], p["name"], p["specialty"], p["kind"], p["bio"], p["modes"], p["clinic"], p["address"], p["hours"]),
        )


def list_providers() -> list[dict]:
    with db.connection() as conn:
        return conn.execute(f"SELECT {_PROVIDER_COLS} FROM providers WHERE active ORDER BY name").fetchall()


def get_provider(provider_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute(
            f"SELECT {_PROVIDER_COLS} FROM providers WHERE id = %s AND active", (provider_id,)
        ).fetchone()


def provider_booked_slots(provider_id: UUID) -> set:
    """Slots a provider can no longer offer. The shared demo patient never blocks a slot."""
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT slot FROM appointments
            WHERE provider_id = %s AND status = 'booked' AND slot >= now() AND patient_id <> %s
            """,
            (provider_id, demo_data.MAYA_ID),
        ).fetchall()
    return {r["slot"] for r in rows}


class SlotTaken(Exception):
    pass


_VISIT_SELECT = """
    SELECT a.id, a.patient_id, a.provider_id, a.slot, a.mode, a.reason, a.urgency, a.status,
           a.meeting_provider, a.meeting_room, a.meeting_url,
           p.name AS provider_name, p.specialty AS provider_specialty, p.kind AS provider_kind,
           p.clinic AS provider_clinic, p.address AS provider_address, p.modes AS provider_modes
    FROM appointments a JOIN providers p ON p.id = a.provider_id
"""


def insert_visit(patient_id: UUID, provider_id: UUID, slot, mode: str, reason: str, urgency: str,
                 meeting: Optional[dict]) -> UUID:
    """Raises SlotTaken when the provider is already booked at that time (unique index, so it is race-safe)."""
    from psycopg.errors import UniqueViolation

    m = meeting or {}
    try:
        with db.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO appointments (patient_id, provider_id, slot, mode, reason, urgency, status,
                                          meeting_provider, meeting_room, meeting_url,
                                          facility_name, facility_address)
                SELECT %s, p.id, %s, %s, %s, %s, 'booked', %s, %s, %s, p.clinic, p.address
                FROM providers p WHERE p.id = %s RETURNING id
                """,
                (patient_id, slot, mode, reason, urgency,
                 m.get("provider"), m.get("room"), m.get("url"), provider_id),
            ).fetchone()
            if patient_id == demo_data.MAYA_ID:  # the shared demo account: keep only the newest few
                conn.execute(
                    """
                    DELETE FROM appointments WHERE patient_id = %s AND provider_id IS NOT NULL AND id NOT IN (
                        SELECT id FROM appointments WHERE patient_id = %s AND provider_id IS NOT NULL
                        ORDER BY created_at DESC LIMIT 6)
                    """,
                    (patient_id, patient_id),
                )
    except UniqueViolation:
        raise SlotTaken() from None
    return row["id"]


def list_visits(patient_id: UUID) -> list[dict]:
    with db.connection() as conn:
        return conn.execute(
            _VISIT_SELECT + " WHERE a.patient_id = %s ORDER BY a.slot", (patient_id,)
        ).fetchall()


def get_visit(appointment_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute(_VISIT_SELECT + " WHERE a.id = %s", (appointment_id,)).fetchone()


def get_visit_by_room(room: str) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute(_VISIT_SELECT + " WHERE a.meeting_room = %s", (room,)).fetchone()


def cancel_visit(appointment_id: UUID) -> bool:
    with db.connection() as conn:
        cur = conn.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = %s AND status = 'booked'", (appointment_id,)
        )
    return cur.rowcount > 0


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
                   feeding_type, history_mental_health, pregnancy_complications,
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


_PATIENT_TABLES = ("checkins", "vitals", "epds_scores", "appointments", "risk_assessments", "alert_log",
                   "care_requests")


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


def refresh_all() -> None:
    """Re-materialise the daily aggregates over all time (after delete-my-data)."""
    with db.autocommit_connection() as conn:
        for view in ("daily_checkins", "daily_metrics"):
            conn.execute("CALL refresh_continuous_aggregate(%s::regclass, NULL, NULL)", (view,))


def save_day(patient_id: UUID, day: date, e) -> None:
    """Set one day's numbers (DayEntry). Existing check-ins that day are updated in place, so
    their transcript mentions and red-flag history are kept; a day with none gets one row at noon.
    Blood pressure works the same way on vitals. Then that day's aggregate bucket is refreshed.
    Days are UTC days, matching /trends."""
    start = datetime.combine(day, time(0), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    fields = {"p": patient_id, "s": start, "e": end, "mood": e.mood, "pain": e.pain,
              "inc": e.incision_pain, "sleep": e.sleep_hrs, "head": e.headache}
    with db.connection() as conn:
        cur = conn.execute(
            """UPDATE checkins SET mood = %(mood)s, pain = %(pain)s, incision_pain = %(inc)s,
                      sleep_hrs = %(sleep)s, headache = %(head)s
               WHERE patient_id = %(p)s AND time >= %(s)s AND time < %(e)s""",
            fields,
        )
        if cur.rowcount == 0:
            conn.execute(
                """INSERT INTO checkins (time, patient_id, mood, pain, incision_pain, sleep_hrs, headache,
                                         vision_change, fever, mentions, red_flag)
                   VALUES (%(s)s + interval '12 hours', %(p)s, %(mood)s, %(pain)s, %(inc)s, %(sleep)s,
                           %(head)s, false, false, '{}', false)""",
                fields,
            )
        bp = {"p": patient_id, "s": start, "e": end, "sys": e.bp_sys, "dia": e.bp_dia}
        cur = conn.execute(
            """UPDATE vitals SET bp_sys = %(sys)s, bp_dia = %(dia)s
               WHERE patient_id = %(p)s AND time >= %(s)s AND time < %(e)s AND
                     (bp_sys IS NOT NULL OR source IN ('typed', 'voice'))""",
            bp,
        )
        if cur.rowcount == 0 and e.bp_sys is not None and e.bp_dia is not None:
            conn.execute(
                """INSERT INTO vitals (time, patient_id, bp_sys, bp_dia, source)
                   VALUES (%(s)s + interval '8 hours', %(p)s, %(sys)s, %(dia)s, 'typed')""",
                bp,
            )
    with db.autocommit_connection() as conn:
        for view in ("daily_checkins", "daily_metrics"):
            conn.execute("CALL refresh_continuous_aggregate(%s::regclass, %s, %s)", (view, start, end))


# --- Agents ----------------------------------------------------------------------------
import json as _json  # noqa: E402


def last_checkin_time(patient_id: UUID):
    with db.connection() as conn:
        row = conn.execute("SELECT max(time) AS t FROM checkins WHERE patient_id = %s", (patient_id,)).fetchone()
    return row["t"] if row else None


def active_patient_ids(days: int = 30) -> list[UUID]:
    with db.connection() as conn:
        rows = conn.execute(
            """SELECT DISTINCT c.patient_id FROM checkins c JOIN patients p ON p.id = c.patient_id
               WHERE c.time >= now() - %s AND NOT p.is_synthetic AND p.user_id IS NOT NULL""",
            (timedelta(days=days),),
        ).fetchall()
    return [r["patient_id"] for r in rows]


def save_assessment(patient_id: UUID, tiers: list[dict], note: Optional[str]) -> None:
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO risk_assessments (patient_id, category, tier, score, reasons, next_step, agent_note)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                [(patient_id, t["category"], t["tier"], t["score"], t["reasons"], t["next_step"], note) for t in tiers],
            )


def _request_out(r: Optional[dict]) -> Optional[dict]:
    if not r:
        return None
    return {k: (str(v) if k in ("id", "patient_id", "appointment_id") and v else v) for k, v in r.items()}


def open_care_request(patient_id: UUID) -> Optional[dict]:
    """The latest request that still needs the patient (proposed), from the last 3 days."""
    with db.connection() as conn:
        r = conn.execute(
            """SELECT * FROM care_requests WHERE patient_id = %s AND status = 'proposed'
               AND created_at >= now() - interval '3 days' ORDER BY created_at DESC LIMIT 1""",
            (patient_id,),
        ).fetchone()
    return _request_out(r)


def create_care_request(patient_id, tier, reasons, note, message, facilities, slots) -> dict:
    with db.connection() as conn:
        r = conn.execute(
            """INSERT INTO care_requests (patient_id, tier, reasons, clinician_note, patient_message, facilities, slots)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb) RETURNING *""",
            (patient_id, tier, reasons, note, message, _json.dumps(facilities), _json.dumps(slots)),
        ).fetchone()
    return _request_out(r)


def get_care_request(request_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return _request_out(conn.execute("SELECT * FROM care_requests WHERE id = %s", (request_id,)).fetchone())


def book_care_request(req: dict, facility: Optional[dict], slot: str) -> str:
    with db.connection() as conn:
        with conn.transaction():
            appt = conn.execute(
                """INSERT INTO appointments (patient_id, slot, reason, urgency, status, facility_name,
                                             facility_address, facility_phone, clinician_note)
                   VALUES (%s, %s, %s, %s, 'booked', %s, %s, %s, %s) RETURNING id""",
                (req["patient_id"], slot, "; ".join(req["reasons"])[:500], "amber",
                 (facility or {}).get("name"), (facility or {}).get("address"), (facility or {}).get("phone"),
                 req.get("clinician_note")),
            ).fetchone()
            conn.execute("UPDATE care_requests SET status = 'booked', appointment_id = %s WHERE id = %s",
                         (appt["id"], req["id"]))
    return str(appt["id"])


def dismiss_care_request(request_id: UUID) -> None:
    with db.connection() as conn:
        conn.execute("UPDATE care_requests SET status = 'dismissed' WHERE id = %s", (request_id,))


def upcoming_appointments(patient_id: UUID) -> list[dict]:
    with db.connection() as conn:
        return conn.execute(
            """SELECT id::text, slot, reason, facility_name, facility_address, facility_phone, status
               FROM appointments WHERE patient_id = %s AND slot >= now() - interval '1 day' ORDER BY slot""",
            (patient_id,),
        ).fetchall()


def set_location(patient_id: UUID, lat: Optional[float], lon: Optional[float], postal_code: Optional[str]) -> None:
    """Save (or with all None, forget) where the patient is, for nearby care."""
    with db.connection() as conn:
        conn.execute("UPDATE patients SET home_lat = %s, home_lon = %s, postal_code = %s WHERE id = %s",
                     (lat, lon, postal_code, patient_id))


def set_circle_token(patient_id: UUID, token_hash: Optional[str]) -> None:
    with db.connection() as conn:
        conn.execute("UPDATE patients SET circle_token_hash = %s WHERE id = %s", (token_hash, patient_id))


def patient_for_circle(token_hash: str) -> Optional[UUID]:
    with db.connection() as conn:
        r = conn.execute("SELECT id FROM patients WHERE circle_token_hash = %s", (token_hash,)).fetchone()
    return r["id"] if r else None


def latest_assessment(patient_id: UUID) -> list[dict]:
    with db.connection() as conn:
        return conn.execute(
            """SELECT DISTINCT ON (category) category, tier, reasons, next_step, agent_note, time
               FROM risk_assessments WHERE patient_id = %s ORDER BY category, time DESC""",
            (patient_id,),
        ).fetchall()


def todays_epds(patient_id: UUID) -> Optional[dict]:
    with db.connection() as conn:
        return conn.execute(
            """SELECT score, item10, answers, time FROM epds_scores
               WHERE patient_id = %s AND time >= date_trunc('day', now()) ORDER BY time DESC LIMIT 1""",
            (patient_id,),
        ).fetchone()
