-- Visits: care providers (seeded demo data) and richer appointments (in person or video).
-- Idempotent, safe to re-run. The provider rows themselves are upserted by scripts/migrate.py
-- from app/providers_data.py, so there is one source of truth for them.

CREATE TABLE IF NOT EXISTS providers (
    id           UUID PRIMARY KEY,
    name         TEXT NOT NULL,
    specialty    TEXT NOT NULL,                 -- shown to the patient, e.g. "Obstetrician-gynecologist"
    kind         TEXT NOT NULL,                 -- obstetrics | midwifery | lactation | mental_health | blood_pressure
    bio          TEXT,
    modes        TEXT[] NOT NULL,               -- subset of {in_person, virtual}
    clinic       TEXT,
    address      TEXT,
    hours        INT[] NOT NULL,                -- clinic-local start hours offered each weekday
    is_synthetic BOOL NOT NULL DEFAULT true,    -- the seeded providers are fictional
    active       BOOL NOT NULL DEFAULT true
);

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS provider_id UUID REFERENCES providers (id);

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'in_person';

-- Video visits: which service hosts the room ("daily" or the "jitsi" fallback), the room name and its base URL.
-- The URL a person actually joins with (it carries a short-lived token) is built at join time, never stored.
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS meeting_provider TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS meeting_room TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS meeting_url TEXT;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- One booked patient per provider and time. The shared demo patient (Maya) is excluded so
-- everyone trying the demo can book the same slot.
CREATE UNIQUE INDEX IF NOT EXISTS appointments_provider_slot
    ON appointments (provider_id, slot)
    WHERE status = 'booked' AND patient_id <> '00000000-0000-4000-8000-000000000001';
