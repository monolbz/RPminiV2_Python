-- =============================================================================
-- Migration 004: Feedback Surveys
-- =============================================================================
-- Creates the feedback_surveys table for the WhatsApp NPS survey system.
-- Surveys are triggered on day 3 of use (created_at <= now()-3d AND routes>=1).
-- A partial unique index prevents duplicate active surveys per user.
--
-- Usage:
--   psql $DATABASE_URL -f database/migrations/004_add_feedback_surveys.sql
-- =============================================================================

CREATE TABLE feedback_surveys (
    survey_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number     VARCHAR(20) NOT NULL REFERENCES users(phone_number) ON DELETE CASCADE,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','sent','in_progress','completed','skipped')),
    current_step     VARCHAR(20) NOT NULL DEFAULT 'q1'
                         CHECK (current_step IN ('q1','q2','q3','done')),
    nps_score        SMALLINT CHECK (nps_score BETWEEN 1 AND 10),
    free_text        TEXT,
    willing_to_pay   VARCHAR(10) CHECK (willing_to_pay IN ('si','no','quizas')),
    price_suggestion VARCHAR(100),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at          TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    skipped_at       TIMESTAMPTZ
);

-- Prevent duplicate active surveys per user.
-- Allows re-survey after a previous survey is completed or skipped.
CREATE UNIQUE INDEX idx_feedback_surveys_active_phone
    ON feedback_surveys(phone_number)
    WHERE status NOT IN ('completed', 'skipped');

CREATE INDEX idx_feedback_surveys_phone ON feedback_surveys(phone_number);
CREATE INDEX idx_feedback_surveys_status ON feedback_surveys(status);
CREATE INDEX idx_feedback_surveys_created ON feedback_surveys(created_at);

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('004', 'Feedback surveys: NPS, free text, willingness to pay');
