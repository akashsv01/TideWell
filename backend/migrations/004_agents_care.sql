-- Phase 3/4: agents, care requests, location for nearby care, Care Circle share link. Idempotent.

-- Where the patient is, for "nearest care" (set from the browser with permission, or a ZIP code).
ALTER TABLE patients ADD COLUMN IF NOT EXISTS postal_code TEXT;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS home_lat DOUBLE PRECISION;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS home_lon DOUBLE PRECISION;

-- Care Circle: a private read-only link for the support person (token hash only).
ALTER TABLE patients ADD COLUMN IF NOT EXISTS circle_token_hash TEXT;

-- The Watch agent's plain-language note for the clinician, kept with each assessment run.
ALTER TABLE risk_assessments ADD COLUMN IF NOT EXISTS agent_note TEXT;

-- One row per "this patient should be seen" decision from the Watch agent, handled by the Booking
-- agent: proposed -> booked | dismissed.
CREATE TABLE IF NOT EXISTS care_requests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id  UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    tier        TEXT NOT NULL,
    reasons     TEXT[] NOT NULL DEFAULT '{}',
    clinician_note TEXT,
    patient_message TEXT,
    facilities  JSONB NOT NULL DEFAULT '[]',
    slots       JSONB NOT NULL DEFAULT '[]',
    status      TEXT NOT NULL DEFAULT 'proposed',
    appointment_id UUID
);

CREATE INDEX IF NOT EXISTS care_requests_patient ON care_requests (patient_id, created_at DESC);

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS facility_name TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS facility_address TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS facility_phone TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS clinician_note TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
