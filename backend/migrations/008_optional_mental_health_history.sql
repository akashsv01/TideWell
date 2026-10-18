-- Preserve "not sure / prefer not to say" instead of treating it as a negative history.
-- Previous versions stored both "no" and "not sure" as false, so those values cannot be recovered.
UPDATE patients SET history_mental_health = NULL WHERE history_mental_health = false;
ALTER TABLE patients ALTER COLUMN history_mental_health DROP NOT NULL;
