-- Phase 2: username/password accounts, server-side sessions, and the full onboarding baseline profile.
-- Idempotent, safe to re-run. Replaces the Clerk link from 002.

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT NOT NULL,
    password_hash TEXT NOT NULL,           -- scrypt$N$r$p$salt$hash (see app/auth.py); never the password
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Usernames are case-insensitive: "Maya" and "maya" are the same account.
CREATE UNIQUE INDEX IF NOT EXISTS users_username_key ON users (lower(username));

-- One row per signed-in device. Only a SHA-256 of the token is stored; logout deletes the row.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id);

-- Each account owns at most one patient record. The demo patient (Maya) has no user.
ALTER TABLE patients ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users (id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS patients_user_id_key ON patients (user_id) WHERE user_id IS NOT NULL;

-- Baseline profile (collected once at onboarding, editable in Settings).
-- Existing columns cover: birth_date (delivery date), gestation_weeks, delivery_type (method),
-- language (preference), support_phone. conditions/breastfeeding stay as derived fields for the
-- category rules and the reply context.
ALTER TABLE patients ADD COLUMN IF NOT EXISTS consent_granted BOOL NOT NULL DEFAULT false;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS feeding_type TEXT;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS history_mental_health BOOL NOT NULL DEFAULT false;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS pregnancy_complications TEXT[] NOT NULL DEFAULT '{}';

ALTER TABLE patients ADD COLUMN IF NOT EXISTS support_person_name TEXT;

-- The Clerk link (002) is replaced by user_id.
DROP INDEX IF EXISTS patients_clerk_user_id_key;

ALTER TABLE patients DROP COLUMN IF EXISTS clerk_user_id;

CREATE INDEX IF NOT EXISTS epds_patient_day ON epds_scores (patient_id, time DESC);
