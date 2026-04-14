-- Migration 006: PPU credits — pay-per-route upfront model
-- PPU users pre-pay €1.99 per route. Credits are decremented on each route use.
-- Replaces metered Stripe subscription with one-time payment per route.

ALTER TABLE users ADD COLUMN ppu_credits INTEGER NOT NULL DEFAULT 0;

INSERT INTO schema_migrations (version, description)
VALUES ('006', 'PPU credits: pay-per-route upfront model');
