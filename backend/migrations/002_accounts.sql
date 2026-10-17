-- Phase 2: link a patient row to a login (Clerk user id). Idempotent, safe to re-run.
-- Clerk ids look like "user_2abc...", not UUIDs, so they get their own column; patients.id stays the UUID
-- every other table references.
ALTER TABLE patients ADD COLUMN IF NOT EXISTS clerk_user_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS patients_clerk_user_id_key ON patients (clerk_user_id) WHERE clerk_user_id IS NOT NULL;
