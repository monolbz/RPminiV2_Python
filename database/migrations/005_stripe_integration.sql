-- Migration 005: Stripe Integration
-- Adds payment/subscription fields to users table
-- Extends audit_logs valid_action constraint with payment events

BEGIN;

-- 1. New columns on users table
ALTER TABLE users ADD COLUMN stripe_customer_id     VARCHAR(30);
ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(30);
ALTER TABLE users ADD COLUMN stripe_price_id        VARCHAR(30);
ALTER TABLE users ADD COLUMN pending_tier           VARCHAR(20);
ALTER TABLE users ADD COLUMN checkout_created_at    TIMESTAMPTZ;

-- 2. Index for fast webhook lookups by Stripe customer ID
CREATE INDEX idx_users_stripe_customer
    ON users(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- 3. Extend valid_action CHECK on audit_logs (drop + recreate)
ALTER TABLE audit_logs DROP CONSTRAINT valid_action;
ALTER TABLE audit_logs ADD CONSTRAINT valid_action CHECK (
    action IN (
        'user_created', 'consent_given', 'consent_revoked',
        'data_accessed', 'data_exported', 'data_deleted',
        'session_started', 'route_requested', 'route_blocked',
        'tier_assigned',
        'payment_initiated', 'payment_completed', 'tier_upgraded',
        'tier_expired', 'subscription_cancelled', 'ppu_usage_reported'
    )
);

-- 4. Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('005', 'Stripe integration: customer/subscription fields + payment audit actions');

COMMIT;
