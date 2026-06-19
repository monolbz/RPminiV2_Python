-- Migration 007: WhatsApp username / BSUID support
-- Stores the Business-Scoped User ID assigned by Meta when a user adopts a
-- WhatsApp username. Nullable because existing users have no BSUID.
-- Used as a secondary identifier if contact book resolution fails.

ALTER TABLE users
    ADD COLUMN bsuid VARCHAR(64) UNIQUE;

CREATE INDEX idx_users_bsuid ON users(bsuid)
    WHERE bsuid IS NOT NULL;

INSERT INTO schema_migrations (version, description)
VALUES ('007', 'BSUID column for WhatsApp username users');
