-- Apple Health (Health Auto Export) data. Idempotent: the shared database already has the first
-- two tables (created by hand while building person2-backend), a fresh one gets them here.

-- Every watch/phone sample, one row per (patient, metric, time). BP readings are staged here as
-- bp_sys / bp_dia and copied into vitals when the patient imports them (or at once if unsafe).
CREATE TABLE IF NOT EXISTS wearable_metrics (
    time        TIMESTAMPTZ NOT NULL,
    patient_id  UUID NOT NULL,
    metric      TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    source      TEXT NOT NULL DEFAULT 'apple_health'
);
SELECT create_hypertable('wearable_metrics', 'time', if_not_exists => TRUE, migrate_data => TRUE);
CREATE UNIQUE INDEX IF NOT EXISTS wearable_metrics_key ON wearable_metrics (patient_id, metric, time);

-- One phone connection code per patient; only its SHA-256 is stored.
CREATE TABLE IF NOT EXISTS wearable_tokens (
    token_hash    TEXT PRIMARY KEY,
    patient_id    UUID NOT NULL UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at  TIMESTAMPTZ
);

-- Unsafe readings that arrived from the phone, shown once as the urgent card on the website.
CREATE TABLE IF NOT EXISTS health_alerts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id    UUID NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    reading_time  TIMESTAMPTZ NOT NULL,
    level         TEXT NOT NULL,
    reason        TEXT,
    bp_sys        INT,
    bp_dia        INT,
    seen_at       TIMESTAMPTZ,
    UNIQUE (patient_id, reading_time)
);
CREATE INDEX IF NOT EXISTS health_alerts_unseen ON health_alerts (patient_id) WHERE seen_at IS NULL;

-- Where a check-in came from. Apple Health rows fill sleep only and are not counted as the patient
-- checking in (the Watch agent's "hasn't checked in" signal).
ALTER TABLE checkins ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'voice';
