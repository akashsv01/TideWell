-- Preserve "not sure / prefer not to say" instead of treating it as a negative history.
-- Previous versions stored both "no" and "not sure" as false, so those values cannot be recovered.
-- The column must allow NULL before any row is set to NULL.
ALTER TABLE patients ALTER COLUMN history_mental_health DROP NOT NULL;

-- One-off: older false answers become unknown. Recorded so a re-run of scripts/migrate.py never
-- erases a "no" given after this migration.
CREATE TABLE IF NOT EXISTS data_migrations (
    name       TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM data_migrations WHERE name = 'mental_health_history_unknown') THEN UPDATE patients SET history_mental_health = NULL WHERE history_mental_health = false; INSERT INTO data_migrations (name) VALUES ('mental_health_history_unknown'); END IF; END $$;
