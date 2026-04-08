#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Usage Manager — Tier-based route limit enforcement.

Manages user tier assignments and route usage counters.
Tiers: btester, free, ppu, premium, plus.

Pre-Stripe phase: blocked users see "payments coming soon" message.
Stripe payment links will be added in Phase 3.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import get_db_manager
from database.models import User, AuditLog
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------

TIER_CONFIG = {
    'btester': {
        'daily_limit': 3,
        'lifetime_limit': None,
        'days': 7,
    },
    'free': {
        'daily_limit': None,
        'lifetime_limit': 3,
        'days': 30,
    },
    'ppu': {
        'daily_limit': 10,   # Safety cap — not shown to user unless hit
        'lifetime_limit': None,
        'days': None,        # No expiry
    },
    'premium': {
        'daily_limit': 2,
        'lifetime_limit': None,
        'days': 30,
    },
    'plus': {
        'daily_limit': 4,
        'lifetime_limit': None,
        'days': 30,
    },
}

# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------

def assign_default_tier(user: User, session) -> str:
    """
    Assign the default tier to a newly created user.

    Called from consent_manager_db.save_consent() within the existing DB
    session so tier is committed atomically with user creation.

    Logic:
    - If active B-Tester count < BTESTER_MAX_USERS → assign 'btester' (7 days)
    - Otherwise → assign 'free' (30 days)

    Args:
        user: The newly created User ORM object (already flushed, has user_id)
        session: The active SQLAlchemy session

    Returns:
        str: The assigned tier name
    """
    from ..config.config import Config
    config = Config()
    btester_cap = config.BTESTER_MAX_USERS

    active_btesters = session.query(User).filter(
        User.tier == 'btester',
        User.deleted_at.is_(None)
    ).count()

    now = datetime.now(timezone.utc)

    if active_btesters < btester_cap:
        tier = 'btester'
        expires_at = now + timedelta(days=7)
    else:
        tier = 'free'
        expires_at = now + timedelta(days=30)

    user.tier = tier
    user.tier_started_at = now
    user.tier_expires_at = expires_at

    audit = AuditLog.log_action(
        user_id=user.user_id,
        action='tier_assigned',
        actor='system',
        details={'tier': tier, 'expires_at': expires_at.isoformat()}
    )
    session.add(audit)

    logger.info(f"Assigned tier '{tier}' to new user {user.phone_number} "
                f"(expires: {expires_at.date()})")
    return tier


# ---------------------------------------------------------------------------
# Route gate check
# ---------------------------------------------------------------------------

def check_route_allowed(phone_number: str) -> Tuple[bool, str]:
    """
    Check whether this user is allowed to run a route optimization.

    Also resets the daily counter if the UTC date has changed since the
    last route was recorded.

    Args:
        phone_number: User's phone number (E.164 format)

    Returns:
        (True, '') if allowed
        (False, message) if blocked
    """
    if _is_superuser(phone_number):
        logger.info(f"Superuser bypass: {phone_number}")
        return True, ''

    try:
        db = get_db_manager()
        with db.get_session() as session:
            user = session.query(User).filter_by(
                phone_number=phone_number,
                deleted_at=None
            ).first()

            if not user:
                logger.warning(f"check_route_allowed: no user found for {phone_number}")
                return False, _error_message()

            cfg = TIER_CONFIG.get(user.tier, TIER_CONFIG['free'])
            today_utc = datetime.now(timezone.utc).date()

            # 1. Reset daily counter if a new UTC day has started
            if user.routes_reset_date != today_utc:
                user.routes_used_today = 0
                user.routes_reset_date = today_utc

            # 2. Check tier expiry (all tiers except ppu)
            if user.tier_expires_at is not None:
                expires_at = user.tier_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_at:
                    _log_blocked(session, user, 'expired')
                    return False, _blocked_message(user.tier, reason='expired', phone_number=phone_number)

            # 3. Check lifetime limit (free tier only)
            if cfg['lifetime_limit'] is not None:
                if user.routes_used_lifetime >= cfg['lifetime_limit']:
                    _log_blocked(session, user, 'lifetime_exhausted')
                    return False, _blocked_message(user.tier, reason='lifetime_exhausted', phone_number=phone_number)

            # 4. Check daily limit (btester, ppu, premium, plus)
            if cfg['daily_limit'] is not None:
                if user.routes_used_today >= cfg['daily_limit']:
                    _log_blocked(session, user, 'daily_limit')
                    return False, _blocked_message(user.tier, reason='daily_limit', phone_number=phone_number)

            return True, ''

    except Exception as e:
        logger.error(f"Error in check_route_allowed for {phone_number}: {e}", exc_info=True)
        return False, _error_message()


def record_route_used(phone_number: str) -> None:
    """
    Increment route usage counters after a successful optimization.

    Must be called ONLY after the route has been successfully processed
    and sent to the user. Failed or error routes must not be counted.

    Args:
        phone_number: User's phone number (E.164 format)
    """
    if _is_superuser(phone_number):
        logger.info(f"Superuser bypass: skipping counter increment for {phone_number}")
        return

    user_tier = None
    try:
        db = get_db_manager()
        with db.get_session() as session:
            user = session.query(User).filter_by(
                phone_number=phone_number,
                deleted_at=None
            ).first()

            if not user:
                logger.warning(f"record_route_used: no user found for {phone_number}")
                return

            today_utc = datetime.now(timezone.utc).date()

            # Sync daily reset date in case check_route_allowed was called in
            # a different session (shouldn't happen in practice but be safe)
            if user.routes_reset_date != today_utc:
                user.routes_used_today = 0
                user.routes_reset_date = today_utc

            user.routes_used_lifetime += 1
            user.routes_used_today += 1
            user_tier = user.tier  # capture before session closes

            audit = AuditLog.log_action(
                user_id=user.user_id,
                action='route_requested',
                actor='user',
                details={
                    'tier': user.tier,
                    'lifetime_total': user.routes_used_lifetime,
                    'today_total': user.routes_used_today,
                }
            )
            session.add(audit)

            logger.info(f"Route recorded for {phone_number} "
                        f"(lifetime={user.routes_used_lifetime}, "
                        f"today={user.routes_used_today}, tier={user.tier})")

    except Exception as e:
        logger.error(f"Error in record_route_used for {phone_number}: {e}", exc_info=True)

    # Report metered usage to Stripe for ppu users (non-fatal)
    if user_tier == 'ppu':
        try:
            from .stripe_manager import StripeManager
            StripeManager().report_ppu_usage(phone_number)
        except Exception as e:
            logger.error(f"PPU usage reporting failed for {phone_number}: {e}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_blocked(session, user: User, reason: str) -> None:
    """Log a route_blocked audit entry."""
    try:
        audit = AuditLog.log_action(
            user_id=user.user_id,
            action='route_blocked',
            actor='system',
            details={'tier': user.tier, 'reason': reason}
        )
        session.add(audit)
    except Exception:
        pass  # Don't let audit failure block the gate response


def _blocked_message(tier: str, reason: str, phone_number: Optional[str] = None) -> str:
    """
    Return the appropriate blocked message for the given tier and reason.
    Includes Stripe Checkout links when phone_number is provided.
    Falls back gracefully if Stripe is not configured.
    """
    if reason == 'daily_limit':
        # User hit their daily cap — offer upgrade to plus
        opening = (
            f"⛔ *Has alcanzado el límite diario de tu plan* ({tier}).\n\n"
            "Mañana el contador se reinicia automáticamente 🌅\n\n"
            "Para más rutas hoy, actualiza a *Plus* (4 rutas/día):"
        )
        if phone_number:
            upgrade = _get_upgrade_block(phone_number, ['plus'])
            if upgrade:
                return f"{opening}\n\n{upgrade}\n\n_Los precios incluyen IVA. Pago seguro con Stripe 🔒_"
        return f"{opening}\n\n💳 Los pagos estarán disponibles muy pronto."

    elif reason == 'lifetime_exhausted':
        opening = (
            "📦 *Has usado todas las rutas de tu período de prueba.*\n\n"
            "Elige un plan para continuar optimizando:"
        )
    else:  # expired
        opening = (
            "⌛ *Tu período de acceso ha finalizado.*\n\n"
            "Elige un plan para continuar:"
        )

    # lifetime_exhausted and expired: show all 3 tiers
    if phone_number:
        upgrade = _get_upgrade_block(phone_number, ['ppu', 'premium', 'plus'])
        if upgrade:
            return f"{opening}\n\n{upgrade}\n\n_Los precios incluyen IVA. Pago seguro con Stripe 🔒_"

    return (
        f"{opening}\n\n"
        "💳 Los pagos estarán disponibles muy pronto.\n"
        "¡Gracias por tu paciencia!"
    )


def _get_upgrade_block(phone_number: str, tiers: list) -> str:
    """Build Stripe checkout links block. Returns '' on any failure."""
    try:
        from .stripe_manager import StripeManager
        return StripeManager().get_upgrade_options(phone_number, tiers)
    except Exception as e:
        logger.error(f"Could not build upgrade block for {phone_number}: {e}")
        return ''


def _error_message() -> str:
    """Generic error message when usage check fails unexpectedly."""
    return "❌ No se pudo verificar tu acceso. Por favor, intenta de nuevo."


def _is_superuser(phone_number: str) -> bool:
    """Return True if phone_number is listed in SUPERUSER_PHONES env var."""
    from ..config.config import Config
    return phone_number in Config().SUPERUSER_PHONES
