-- =============================================================================
-- Migration 002: User Tier System
-- =============================================================================
-- Adds tier/profile columns to users table and extends audit_logs constraint.
-- Run once against the live database after deploying the code changes.
--
-- Usage:
--   psql $DATABASE_URL -f database/migrations/002_user_tiers.sql
-- =============================================================================

-- Add tier tracking columns to users
ALTER TABLE users ADD COLUMN tier VARCHAR(20) NOT NULL DEFAULT 'btester';
ALTER TABLE users ADD COLUMN tier_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE users ADD COLUMN tier_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN routes_used_lifetime INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN routes_used_today INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN routes_reset_date DATE;  -- UTC date of last daily counter reset

-- Index for tier queries (e.g. counting btester users)
CREATE INDEX idx_users_tier ON users(tier);

-- Extend valid_action CHECK constraint to include tier-related actions.
-- PostgreSQL requires drop + recreate to modify a CHECK constraint.
ALTER TABLE audit_logs DROP CONSTRAINT valid_action;
ALTER TABLE audit_logs ADD CONSTRAINT valid_action CHECK (action IN (
    'user_created',
    'consent_given',
    'consent_revoked',
    'data_accessed',
    'data_exported',
    'data_deleted',
    'session_started',
    'route_requested',
    'tier_assigned',
    'route_blocked'
));

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('002', 'User tier system: btester, free, ppu, premium, plus');
