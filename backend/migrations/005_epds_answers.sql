-- Mood check answers (option indexes) so today's check can be reopened and edited. Idempotent.
ALTER TABLE epds_scores ADD COLUMN IF NOT EXISTS answers INT[];
