-- Tidewell schema for Tiger Data (Postgres + TimescaleDB + pgvector).
-- Idempotent: safe to re-run. Apply with:  python scripts/migrate.py
-- Statements are split on ";" + newline by migrate.py, so keep one statement per block
-- and do not put a semicolon inside a string or a $$ body.
-- Privacy: no race, income, insurance or address columns, on purpose (plan section 7).

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS patients (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                   TEXT,
    age                    INT,
    language               TEXT NOT NULL DEFAULT 'en',
    birth_date             DATE NOT NULL,
    delivery_type          TEXT NOT NULL,
    gestation_weeks        INT,
    conditions             TEXT[] NOT NULL DEFAULT '{}',
    breastfeeding          BOOL NOT NULL DEFAULT false,
    support_phone          TEXT,
    support_consent        BOOL NOT NULL DEFAULT false,
    categories             TEXT[] NOT NULL DEFAULT '{}',
    is_synthetic           BOOL NOT NULL DEFAULT false,
    backboard_assistant_id TEXT,
    backboard_thread_id    TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS checkins (
    time          TIMESTAMPTZ NOT NULL,
    patient_id    UUID NOT NULL,
    mood          INT,
    pain          INT,
    incision_pain INT,
    sleep_hrs     REAL,
    headache      BOOL,
    vision_change BOOL,
    bleeding      TEXT,
    fever         BOOL,
    mentions      TEXT[],
    red_flag      BOOL
);

SELECT create_hypertable('checkins', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS checkins_patient_time ON checkins (patient_id, time DESC);

CREATE TABLE IF NOT EXISTS vitals (
    time       TIMESTAMPTZ NOT NULL,
    patient_id UUID NOT NULL,
    bp_sys     INT,
    bp_dia     INT,
    heart_rate INT,
    temp_c     REAL,
    glucose    INT,
    source     TEXT
);

SELECT create_hypertable('vitals', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS vitals_patient_time ON vitals (patient_id, time DESC);

-- Continuous aggregate 1: daily blood pressure (plan section 7).
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_metrics
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day,
       patient_id,
       avg(bp_sys)  AS bp_sys,
       avg(bp_dia)  AS bp_dia,
       max(bp_sys)  AS bp_sys_max,
       avg(heart_rate) AS heart_rate,
       count(*)     AS n
FROM vitals
GROUP BY day, patient_id
WITH NO DATA;

-- Continuous aggregate 2: daily check-in metrics (mood, pain, sleep live in checkins, not vitals).
-- sum(CASE ...) instead of count(*) FILTER, which older TimescaleDB versions reject in aggregates.
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_checkins
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day,
       patient_id,
       avg(mood)          AS mood,
       avg(pain)          AS pain,
       avg(incision_pain) AS incision_pain,
       avg(sleep_hrs)     AS sleep_hrs,
       sum(CASE WHEN headache THEN 1 ELSE 0 END) AS headache_count,
       count(*)           AS n
FROM checkins
GROUP BY day, patient_id
WITH NO DATA;

-- Real-time aggregation: today's readings show up without waiting for a refresh.
ALTER MATERIALIZED VIEW daily_metrics SET (timescaledb.materialized_only = false);

ALTER MATERIALIZED VIEW daily_checkins SET (timescaledb.materialized_only = false);

SELECT add_continuous_aggregate_policy('daily_metrics',
    start_offset => INTERVAL '30 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes', if_not_exists => true);

SELECT add_continuous_aggregate_policy('daily_checkins',
    start_offset => INTERVAL '30 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes', if_not_exists => true);

CREATE TABLE IF NOT EXISTS epds_scores (
    time       TIMESTAMPTZ NOT NULL,
    patient_id UUID NOT NULL,
    score      INT,
    item10     INT
);

CREATE INDEX IF NOT EXISTS epds_patient_time ON epds_scores (patient_id, time DESC);

-- RAG: guideline chunks. 768 dims, so embed with output_dimensionality=768 (see plan / notes).
CREATE TABLE IF NOT EXISTS guideline_chunks (
    id        SERIAL PRIMARY KEY,
    source    TEXT,
    url       TEXT,
    section   TEXT,
    content   TEXT,
    embedding VECTOR(768)
);

CREATE INDEX IF NOT EXISTS guideline_chunks_embedding_idx
    ON guideline_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS appointments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    slot       TIMESTAMPTZ NOT NULL,
    reason     TEXT,
    urgency    TEXT,
    status     TEXT NOT NULL DEFAULT 'booked',
    fhir_id    TEXT
);

CREATE INDEX IF NOT EXISTS appointments_patient ON appointments (patient_id, slot);

CREATE TABLE IF NOT EXISTS risk_assessments (
    time       TIMESTAMPTZ NOT NULL DEFAULT now(),
    patient_id UUID NOT NULL,
    category   TEXT NOT NULL,
    tier       TEXT NOT NULL,
    score      REAL,
    reasons    TEXT[],
    next_step  TEXT
);

CREATE INDEX IF NOT EXISTS risk_patient_cat_time ON risk_assessments (patient_id, category, time DESC);

-- Support-person SMS audit trail. Stores the outcome only, never the phone number or message.
CREATE TABLE IF NOT EXISTS alert_log (
    time       TIMESTAMPTZ NOT NULL DEFAULT now(),
    patient_id UUID NOT NULL,
    status     TEXT NOT NULL,
    twilio_sid TEXT
);
