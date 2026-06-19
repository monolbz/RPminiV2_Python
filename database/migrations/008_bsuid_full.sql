-- Migration 008: Full BSUID-only user support
-- Allows users without a phone number (WhatsApp username users).
-- Apply AFTER migration 007 (which added the bsuid column).

-- 1. Make phone_number nullable (BSUID-only users have no phone)
ALTER TABLE users ALTER COLUMN phone_number DROP NOT NULL;

-- 2. Relax phone_format constraint: only validate non-NULL values
ALTER TABLE users DROP CONSTRAINT phone_format;
ALTER TABLE users ADD CONSTRAINT phone_format
    CHECK (phone_number IS NULL OR phone_number ~ '^\+?[0-9]+$');

-- 3. Ensure at least one identifier exists (phone OR bsuid, not both NULL)
ALTER TABLE users ADD CONSTRAINT requires_identifier
    CHECK (phone_number IS NOT NULL OR bsuid IS NOT NULL);

-- 4. feedback_surveys: add user_id FK (proper relational link regardless of identifier)
ALTER TABLE feedback_surveys
    ADD COLUMN user_id UUID REFERENCES users(user_id) ON DELETE CASCADE;

-- 5. Backfill user_id from existing phone_number rows
UPDATE feedback_surveys fs
SET user_id = u.user_id
FROM users u
WHERE u.phone_number = fs.phone_number;

-- 6. Make user_id NOT NULL and phone_number nullable in feedback_surveys
ALTER TABLE feedback_surveys ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE feedback_surveys ALTER COLUMN phone_number DROP NOT NULL;

-- 7. Index for the new FK
CREATE INDEX idx_feedback_surveys_user_id ON feedback_surveys(user_id);

INSERT INTO schema_migrations (version, description)
VALUES ('008', 'Full BSUID-only user support: nullable phone, feedback_surveys user_id FK');
