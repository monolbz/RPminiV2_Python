-- =============================================================================
-- WhatsApp Route Optimizer - Database Schema
-- =============================================================================
-- Purpose: Define database structure for GDPR-compliant user data management
-- Author: Jorge Blanco
-- Created: 2025-11-06
-- PostgreSQL Version: 15+
--
-- GDPR Compliance:
-- - Article 5: Data minimization, storage limitation
-- - Article 7: Proof of consent (3-year retention)
-- - Article 15-22: User rights (access, deletion, portability)
-- - Article 32: Security measures
-- =============================================================================

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop existing tables if re-running (CAREFUL in production!)
-- ⚠️ WARNING: This deletes all data! Only safe for development.
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS consents CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- =============================================================================
-- TABLE: schema_migrations
-- =============================================================================
-- Purpose: Track which migrations have been applied
-- Used for: Production migration management
-- =============================================================================

CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

COMMENT ON TABLE schema_migrations IS 'Tracks applied database migrations';

-- =============================================================================
-- TABLE: users
-- =============================================================================
-- Purpose: Store user identity and profile information
-- GDPR Retention: Deleted 24h after consent withdrawal (soft delete)
-- =============================================================================

CREATE TABLE users (
    -- Primary Key
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User Identity (from WhatsApp)
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100),

    -- Preferences
    language VARCHAR(5) DEFAULT 'es',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete (NULL = active user)

    -- Constraints
    CONSTRAINT phone_format CHECK (phone_number ~ '^\+?[0-9]+$')
);

-- Indexes for performance
CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_created ON users(created_at);
CREATE INDEX idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NOT NULL;

-- Comments for documentation
COMMENT ON TABLE users IS 'User profiles from WhatsApp Business API';
COMMENT ON COLUMN users.user_id IS 'Internal UUID - never exposed to users';
COMMENT ON COLUMN users.phone_number IS 'WhatsApp phone number (with country code, e.g., 34644252886)';
COMMENT ON COLUMN users.display_name IS 'WhatsApp display name (optional, from profile)';
COMMENT ON COLUMN users.language IS 'Preferred language (es, en, etc.)';
COMMENT ON COLUMN users.deleted_at IS 'Soft delete timestamp (GDPR Art. 17 - Right to erasure)';

-- =============================================================================
-- TABLE: consents
-- =============================================================================
-- Purpose: Store GDPR consent records (proof of consent)
-- GDPR Retention: 3 years (legal requirement - GDPR Article 7)
-- CRITICAL: Must NOT be deleted even when user is deleted
-- =============================================================================

CREATE TABLE consents (
    -- Primary Key
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Key to User (RESTRICT prevents deleting user with consent records)
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,

    -- Consent Decision
    consent_given BOOLEAN NOT NULL,
    consent_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consent_version VARCHAR(10) NOT NULL DEFAULT '1.0',

    -- Withdrawal
    consent_withdrawn BOOLEAN DEFAULT FALSE,
    withdrawal_date TIMESTAMP WITH TIME ZONE,

    -- Audit Trail (optional but recommended)
    ip_address VARCHAR(45),        -- IPv4 (15 chars) or IPv6 (45 chars)
    user_agent VARCHAR(255),
    language VARCHAR(5) DEFAULT 'es',

    -- Constraints
    CONSTRAINT valid_withdrawal CHECK (
        (consent_withdrawn = FALSE AND withdrawal_date IS NULL) OR
        (consent_withdrawn = TRUE AND withdrawal_date IS NOT NULL)
    ),
    CONSTRAINT valid_consent_date CHECK (consent_date <= COALESCE(withdrawal_date, CURRENT_TIMESTAMP))
);

-- Indexes for performance
CREATE INDEX idx_consents_user ON consents(user_id);
CREATE INDEX idx_consents_date ON consents(consent_date);
CREATE INDEX idx_consents_status ON consents(consent_given, consent_withdrawn);

-- Comments
COMMENT ON TABLE consents IS 'GDPR consent records - must be kept 3 years for proof';
COMMENT ON COLUMN consents.consent_version IS 'Version of consent text user agreed to (track changes to terms)';
COMMENT ON COLUMN consents.consent_withdrawn IS 'Whether user has withdrawn consent';
COMMENT ON COLUMN consents.withdrawal_date IS 'When consent was withdrawn (NULL if not withdrawn)';
COMMENT ON COLUMN consents.ip_address IS 'Optional: IP address when consent was given (audit trail)';
COMMENT ON COLUMN consents.user_agent IS 'Optional: User agent when consent was given (audit trail)';

-- =============================================================================
-- TABLE: sessions
-- =============================================================================
-- Purpose: Track 24-hour WhatsApp conversation windows
-- GDPR Retention: 48 hours (automatic cleanup)
-- =============================================================================

CREATE TABLE sessions (
    -- Primary Key
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Key to User (CASCADE deletes sessions when user is deleted)
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Session Timing
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_expiry CHECK (expires_at > last_message_at)
);

-- Indexes for performance
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expiry ON sessions(expires_at);
CREATE INDEX idx_sessions_last_message ON sessions(last_message_at);

-- Comments
COMMENT ON TABLE sessions IS 'WhatsApp 24-hour conversation windows (operational data)';
COMMENT ON COLUMN sessions.last_message_at IS 'Timestamp of user''s last message';
COMMENT ON COLUMN sessions.expires_at IS 'Session expires 24 hours after last_message_at';

-- =============================================================================
-- TABLE: audit_logs
-- =============================================================================
-- Purpose: GDPR accountability and security auditing
-- GDPR Retention: 90 days
-- =============================================================================

CREATE TABLE audit_logs (
    -- Primary Key
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who (can be NULL if user is deleted)
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

    -- What
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(50) NOT NULL DEFAULT 'system',

    -- Details (flexible JSON format)
    details JSONB,

    -- When
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Where (optional)
    ip_address VARCHAR(45),

    -- Constraints
    CONSTRAINT valid_action CHECK (action IN (
        'user_created',
        'consent_given',
        'consent_revoked',
        'data_accessed',
        'data_exported',
        'data_deleted',
        'session_started',
        'route_requested'
    ))
);

-- Indexes for performance
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_details ON audit_logs USING GIN (details);

-- Comments
COMMENT ON TABLE audit_logs IS 'Audit trail for GDPR compliance and security (Art. 5.2 - Accountability)';
COMMENT ON COLUMN audit_logs.action IS 'Type of action performed (see CHECK constraint for valid values)';
COMMENT ON COLUMN audit_logs.actor IS 'Who performed the action: user, system, admin';
COMMENT ON COLUMN audit_logs.details IS 'JSONB field for flexible additional data (e.g., old/new values)';

-- =============================================================================
-- FUNCTION: cleanup_expired_data
-- =============================================================================
-- Purpose: Automatically delete data past retention periods (GDPR compliance)
-- Schedule: Run daily via cron job or pg_cron extension
-- Returns: Table showing how many records were deleted from each table
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS TABLE(
    table_name TEXT,
    records_deleted INTEGER
) AS $$
DECLARE
    sessions_deleted INTEGER;
    consents_deleted INTEGER;
    audit_logs_deleted INTEGER;
    users_deleted INTEGER;
BEGIN
    -- Delete expired sessions (older than 48 hours)
    DELETE FROM sessions WHERE expires_at < NOW() - INTERVAL '48 hours';
    GET DIAGNOSTICS sessions_deleted = ROW_COUNT;

    -- Delete expired consents (older than 3 years)
    DELETE FROM consents WHERE consent_date < NOW() - INTERVAL '3 years';
    GET DIAGNOSTICS consents_deleted = ROW_COUNT;

    -- Delete old audit logs (older than 90 days)
    DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS audit_logs_deleted = ROW_COUNT;

    -- Soft-delete users with revoked consent (older than 24 hours)
    UPDATE users
    SET deleted_at = NOW()
    WHERE user_id IN (
        SELECT user_id FROM consents
        WHERE consent_withdrawn = TRUE
        AND withdrawal_date < NOW() - INTERVAL '24 hours'
    ) AND deleted_at IS NULL;
    GET DIAGNOSTICS users_deleted = ROW_COUNT;

    -- Return results
    RETURN QUERY
    SELECT 'sessions'::TEXT, sessions_deleted
    UNION ALL
    SELECT 'consents'::TEXT, consents_deleted
    UNION ALL
    SELECT 'audit_logs'::TEXT, audit_logs_deleted
    UNION ALL
    SELECT 'users'::TEXT, users_deleted;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON FUNCTION cleanup_expired_data IS 'GDPR-compliant automatic data cleanup (call daily via cron)';

-- =============================================================================
-- INITIAL DATA: Mark schema as applied
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('001', 'Initial schema - users, consents, sessions, audit_logs');

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
--
-- To apply this schema to a fresh database:
--   psql -U wab_user -d wab_db -f database/schema.sql
--
-- To test the cleanup function:
--   SELECT * FROM cleanup_expired_data();
--
-- To schedule automatic cleanup (add to crontab - Linux/Mac):
--   0 2 * * * psql -U wab_user -d wab_db -c "SELECT cleanup_expired_data();"
--
-- To schedule automatic cleanup (Windows Task Scheduler):
--   Program: "C:\Program Files\PostgreSQL\18\bin\psql.exe"
--   Arguments: -U wab_user -d wab_db -c "SELECT cleanup_expired_data();"
--   Schedule: Daily at 2:00 AM
--
-- =============================================================================
