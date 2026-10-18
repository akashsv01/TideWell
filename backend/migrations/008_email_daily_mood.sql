-- Accounts: an email address, asked for at registration (welcome email). Older accounts keep NULL.
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;

-- One-off data changes are recorded here so a re-run of scripts/migrate.py never repeats them.
CREATE TABLE IF NOT EXISTS data_migrations (
    name       TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Daily check-in mood moves from 0-10 to 0-30 (higher is better), the same scale as the mood check
-- score (30 minus the EPDS total). Existing rows are multiplied by 3, exactly once.
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM data_migrations WHERE name = 'mood_0_30') THEN UPDATE checkins SET mood = LEAST(mood * 3, 30) WHERE mood IS NOT NULL; INSERT INTO data_migrations (name) VALUES ('mood_0_30'); END IF; END $$;

-- Rebuild the daily averages from the rescaled rows.
CALL refresh_continuous_aggregate('daily_checkins', NULL, NULL);
