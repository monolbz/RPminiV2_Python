#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stripe Manager — payment integration for Mi Ruta Pro.

Single boundary between the application and the Stripe API.
No other module calls stripe.* directly.

Supported billing models:
  - ppu      : metered subscription (€1.99/route, invoiced monthly)
  - premium  : recurring subscription (€29.99/month, 2 routes/day)
  - plus     : recurring subscription (€49.99/month, 4 routes/day)

All prices are inclusive of Spanish IVA 21%.
"""

import stripe
from datetime import datetime, timezone
from typing import Optional, Tuple

from database.db_manager import get_db_manager
from database.models import User, AuditLog
from ..config.config import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

TIER_DISPLAY = {
    'ppu':     ('📦 Pago por uso',  '€1,99 por ruta',         ''),
    'premium': ('⭐ Premium',        '€29,99/mes',             '2 rutas/día'),
    'plus':    ('🚀 Plus',           '€49,99/mes',             '4 rutas/día'),
}


class StripeManager:
    """Manages Stripe customers, checkout sessions and webhook events."""

    def __init__(self):
        config = Config()
        if not config.STRIPE_SECRET_KEY:
            raise RuntimeError(
                "STRIPE_SECRET_KEY is not configured. "
                "Add it to Railway env vars or .env file."
            )
        stripe.api_key = config.STRIPE_SECRET_KEY
        self.config = config
        self.db = get_db_manager()
        self.price_map = {
            'ppu':     config.STRIPE_PRICE_PPU,
            'premium': config.STRIPE_PRICE_PREMIUM,
            'plus':    config.STRIPE_PRICE_PLUS,
        }

    # ------------------------------------------------------------------
    # Customer management
    # ------------------------------------------------------------------

    def get_or_create_customer(self, phone_number: str) -> Optional[str]:
        """
        Return the Stripe customer ID for this phone number.
        Creates one if it doesn't exist yet.
        """
        try:
            with self.db.get_session() as session:
                user = session.query(User).filter_by(
                    phone_number=phone_number, deleted_at=None
                ).first()
                if not user:
                    logger.error(f"get_or_create_customer: no user for {phone_number}")
                    return None

                if user.stripe_customer_id:
                    return user.stripe_customer_id

                customer = stripe.Customer.create(
                    metadata={'phone_number': phone_number}
                )
                user.stripe_customer_id = customer.id

                audit = AuditLog.log_action(
                    user_id=user.user_id,
                    action='payment_initiated',
                    actor='system',
                    details={'stripe_customer_id': customer.id}
                )
                session.add(audit)
                logger.info(f"Created Stripe customer {customer.id} for {phone_number}")
                return customer.id

        except stripe.StripeError as e:
            logger.error(f"Stripe error creating customer for {phone_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in get_or_create_customer for {phone_number}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def create_checkout_session(self, phone_number: str, tier: str) -> Optional[str]:
        """
        Create a Stripe Checkout session for the given tier.
        Returns the session URL or None on failure.
        """
        if tier not in self.price_map:
            logger.error(f"Unknown tier '{tier}' for checkout")
            return None

        price_id = self.price_map[tier]
        if not price_id:
            logger.error(f"STRIPE_PRICE_{tier.upper()} env var not configured")
            return None

        if not self.config.STRIPE_SUCCESS_URL or not self.config.STRIPE_CANCEL_URL:
            logger.error("STRIPE_SUCCESS_URL or STRIPE_CANCEL_URL not configured")
            return None

        customer_id = self.get_or_create_customer(phone_number)
        if not customer_id:
            return None

        try:
            if tier == 'ppu':
                # One-time payment per route credit — no subscription
                session = stripe.checkout.Session.create(
                    customer=customer_id,
                    client_reference_id=phone_number,
                    metadata={'tier': tier, 'phone_number': phone_number},
                    line_items=[{'price': price_id, 'quantity': 1}],
                    mode='payment',
                    locale='es',
                    automatic_tax={'enabled': True},
                    customer_update={'address': 'auto', 'name': 'auto'},
                    tax_id_collection={'enabled': True},
                    success_url=self.config.STRIPE_SUCCESS_URL,
                    cancel_url=self.config.STRIPE_CANCEL_URL,
                )
            else:
                # Recurring subscription (premium / plus)
                session = stripe.checkout.Session.create(
                    customer=customer_id,
                    client_reference_id=phone_number,
                    metadata={'tier': tier, 'phone_number': phone_number},
                    line_items=[{'price': price_id, 'quantity': 1}],
                    mode='subscription',
                    locale='es',
                    automatic_tax={'enabled': True},
                    customer_update={'address': 'auto', 'name': 'auto'},
                    tax_id_collection={'enabled': True},
                    success_url=self.config.STRIPE_SUCCESS_URL,
                    cancel_url=self.config.STRIPE_CANCEL_URL,
                    subscription_data={
                        'metadata': {'tier': tier, 'phone_number': phone_number}
                    },
                )

            # Record pending tier and checkout timestamp
            with self.db.get_session() as db_session:
                user = db_session.query(User).filter_by(
                    phone_number=phone_number, deleted_at=None
                ).first()
                if user:
                    user.pending_tier = tier
                    user.checkout_created_at = datetime.now(timezone.utc)

            logger.info(f"Checkout session created for {phone_number} tier={tier}")
            return session.url

        except stripe.StripeError as e:
            logger.error(f"Stripe error creating checkout for {phone_number} tier={tier}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating checkout for {phone_number}: {e}", exc_info=True)
            return None

    def get_checkout_link_message(self, phone_number: str, tier: str) -> str:
        """
        Return a formatted Spanish WhatsApp message string with the checkout URL
        for a single tier.  Falls back gracefully if Stripe is unavailable.
        """
        url = self.create_checkout_session(phone_number, tier)
        if not url:
            return ""

        display_name, price, limit = TIER_DISPLAY.get(tier, (tier, '', ''))
        return f"*{display_name}* — {price} ({limit})\n{url}"

    def get_upgrade_options(self, phone_number: str, tiers: list) -> str:
        """
        Build a multi-tier upgrade block (one section per tier).
        Returns empty string if all Stripe calls fail.
        """
        parts = []
        for tier in tiers:
            msg = self.get_checkout_link_message(phone_number, tier)
            if msg:
                parts.append(msg)
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Webhook dispatcher
    # ------------------------------------------------------------------

    def handle_webhook_event(self, payload: bytes, sig_header: str) -> Tuple[bool, str]:
        """
        Verify Stripe signature and dispatch to the appropriate handler.
        Returns (True, 'ok') on success or (False, reason) on failure.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.config.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook: invalid signature")
            return False, 'invalid_signature'
        except Exception as e:
            logger.error(f"Stripe webhook construction error: {e}")
            return False, str(e)

        event_type = event['type']
        logger.info(f"Stripe webhook received: {event_type}")

        try:
            if event_type == 'checkout.session.completed':
                self._handle_checkout_completed(event)
            elif event_type == 'invoice.paid':
                self._handle_invoice_paid(event)
            elif event_type == 'invoice.payment_failed':
                self._handle_invoice_payment_failed(event)
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event)
            elif event_type == 'charge.dispute.created':
                self._handle_dispute_created(event)
            else:
                logger.info(f"Stripe webhook: unhandled event type {event_type} — ignored")
        except Exception as e:
            logger.error(f"Error handling Stripe event {event_type}: {e}", exc_info=True)
            return False, str(e)

        return True, 'ok'

    # ------------------------------------------------------------------
    # Webhook handlers (idempotent)
    # ------------------------------------------------------------------

    def _handle_checkout_completed(self, event: dict) -> None:
        session_obj = event['data']['object']
        phone_number = session_obj.get('client_reference_id')

        if not phone_number:
            logger.error("checkout.session.completed: missing client_reference_id")
            return

        with self.db.get_session() as db_session:
            user = db_session.query(User).filter_by(
                phone_number=phone_number, deleted_at=None
            ).first()
            if not user:
                logger.error(f"checkout.session.completed: no user for {phone_number}")
                return

            # Read tier from session metadata (authoritative — set at session creation)
            # Fallback to pending_tier for sessions created before this fix
            tier = (session_obj.get('metadata') or {}).get('tier') or user.pending_tier
            if not tier:
                logger.warning(f"checkout.session.completed: could not determine tier for {phone_number} — ignoring")
                return

            is_topup = False
            if tier == 'ppu':
                # Idempotency: skip if this session was already processed
                session_id = session_obj.get('id')
                already_processed = db_session.query(AuditLog).filter(
                    AuditLog.user_id == user.user_id,
                    AuditLog.action == 'payment_completed',
                    AuditLog.details['stripe_session_id'].astext == session_id
                ).first()
                if already_processed:
                    logger.info(f"checkout.session.completed: duplicate PPU event {session_id} for {phone_number} — skipping")
                    return

                # One-time payment: add 1 route credit.
                if user.tier in ('btester', 'premium', 'plus'):
                    # Top-up for active subscriber — keep their plan intact
                    is_topup = True
                    user.ppu_credits = (user.ppu_credits or 0) + 1
                    logger.info(f"Added PPU top-up credit for {phone_number} (tier={user.tier}, credits={user.ppu_credits})")
                else:
                    # User on free/ppu — cancel any subscription and switch to PPU mode
                    old_sub_id = user.stripe_subscription_id
                    if old_sub_id:
                        try:
                            stripe.Subscription.cancel(old_sub_id)
                            user.stripe_subscription_id = None
                            user.stripe_price_id = None
                            logger.info(f"Cancelled subscription {old_sub_id} for {phone_number} (switching to ppu)")
                        except stripe.StripeError as e:
                            logger.error(f"Could not cancel subscription {old_sub_id} on ppu switch: {e}")
                    user.ppu_credits = (user.ppu_credits or 0) + 1
                    if user.tier != 'ppu':
                        user.tier = 'ppu'
                        user.tier_started_at = datetime.now(timezone.utc)
                        user.tier_expires_at = None
            else:
                # Subscription: activate tier
                subscription_id = session_obj.get('subscription')
                # Idempotency: skip if already on this tier with same subscription
                if user.tier == tier and user.stripe_subscription_id == subscription_id:
                    logger.info(f"checkout.session.completed: already activated tier={tier} for {phone_number}")
                    return
                # Cancel previous subscription if switching plans (e.g. Premium → Plus)
                old_sub_id = user.stripe_subscription_id
                if old_sub_id and old_sub_id != subscription_id:
                    try:
                        stripe.Subscription.cancel(old_sub_id)
                        logger.info(f"Cancelled old subscription {old_sub_id} for {phone_number} (switching to {tier})")
                    except stripe.StripeError as e:
                        logger.error(f"Could not cancel old subscription {old_sub_id}: {e}")
                self._activate_tier(user, tier, subscription_id, db_session)

            ppu_credits_after = user.ppu_credits or 0
            user.pending_tier = None
            user.checkout_created_at = None

            audit = AuditLog.log_action(
                user_id=user.user_id,
                action='payment_completed',
                actor='system',
                details={
                    'stripe_session_id': session_obj.get('id'),
                    'tier': tier,
                    'amount_total': session_obj.get('amount_total'),
                    'ppu_credits': user.ppu_credits if tier == 'ppu' else None,
                }
            )
            db_session.add(audit)

        logger.info(f"checkout.session.completed: tier={tier} processed for {phone_number}")

        # Send WhatsApp confirmation
        self._send_payment_confirmation(phone_number, tier, ppu_credits=ppu_credits_after, is_topup=is_topup)

    def _handle_invoice_paid(self, event: dict) -> None:
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return

        with self.db.get_session() as db_session:
            user = db_session.query(User).filter_by(
                stripe_subscription_id=subscription_id, deleted_at=None
            ).first()
            if not user:
                logger.info(f"invoice.paid: no user for sub {subscription_id} — may be initial checkout")
                return

            # Use Stripe's current_period_end for accuracy
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                period_end = sub.get('current_period_end')
                if period_end:
                    new_expires = datetime.fromtimestamp(period_end, tz=timezone.utc)
                    # Idempotency: skip if already extended to this date
                    if user.tier_expires_at and abs((user.tier_expires_at - new_expires).total_seconds()) < 60:
                        return
                    user.tier_expires_at = new_expires
            except stripe.StripeError as e:
                logger.error(f"Could not retrieve subscription for invoice.paid: {e}")
                return

            audit = AuditLog.log_action(
                user_id=user.user_id,
                action='tier_upgraded',
                actor='system',
                details={'reason': 'renewal', 'new_expires_at': user.tier_expires_at.isoformat()}
            )
            db_session.add(audit)

        logger.info(f"invoice.paid: tier extended for sub {subscription_id}")

    def _handle_invoice_payment_failed(self, event: dict) -> None:
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return

        with self.db.get_session() as db_session:
            user = db_session.query(User).filter_by(
                stripe_subscription_id=subscription_id, deleted_at=None
            ).first()
            if not user:
                return

            audit = AuditLog.log_action(
                user_id=user.user_id,
                action='payment_initiated',
                actor='system',
                details={'reason': 'payment_failed', 'invoice_id': invoice.get('id')}
            )
            db_session.add(audit)
            phone_number = user.phone_number

        logger.warning(f"invoice.payment_failed for sub {subscription_id}")
        self._send_payment_failed_warning(phone_number)

    def _handle_subscription_deleted(self, event: dict) -> None:
        sub_obj = event['data']['object']
        subscription_id = sub_obj.get('id')

        with self.db.get_session() as db_session:
            user = db_session.query(User).filter_by(
                stripe_subscription_id=subscription_id, deleted_at=None
            ).first()
            if not user:
                logger.info(f"subscription.deleted: no user for sub {subscription_id}")
                return

            # Idempotency: already downgraded
            if user.stripe_subscription_id is None:
                return

            old_tier = user.tier
            ppu_credits = user.ppu_credits or 0
            user.tier = 'ppu'
            user.tier_started_at = datetime.now(timezone.utc)
            user.tier_expires_at = None
            user.stripe_subscription_id = None
            user.stripe_price_id = None

            audit = AuditLog.log_action(
                user_id=user.user_id,
                action='subscription_cancelled',
                actor='system',
                details={'previous_tier': old_tier, 'stripe_subscription_id': subscription_id,
                         'ppu_credits': ppu_credits}
            )
            db_session.add(audit)
            phone_number = user.phone_number

        logger.info(f"subscription.deleted: downgraded {phone_number} from {old_tier} to ppu (credits={ppu_credits})")
        self._send_subscription_cancelled(phone_number)

    def _activate_tier(self, user: User, tier: str, subscription_id: str, session) -> None:
        """Set the user's tier and Stripe subscription fields."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        user.tier = tier
        user.tier_started_at = now
        user.tier_expires_at = now + timedelta(days=30) if tier != 'ppu' else None
        user.stripe_subscription_id = subscription_id
        user.stripe_price_id = self.price_map.get(tier)
        user.routes_used_today = 0

        audit = AuditLog.log_action(
            user_id=user.user_id,
            action='tier_upgraded',
            actor='system',
            details={'tier': tier, 'stripe_subscription_id': subscription_id}
        )
        session.add(audit)

    # ------------------------------------------------------------------
    # WhatsApp notifications (sent after DB session closes)
    # ------------------------------------------------------------------

    def _send_payment_confirmation(self, phone_number: str, tier: str, ppu_credits: int = 1, is_topup: bool = False) -> None:
        try:
            from .message_sender import MessageSender
            display_name, price, limit = TIER_DISPLAY.get(tier, (tier, '', ''))
            if tier == 'ppu':
                credits_word = "crédito" if ppu_credits == 1 else "créditos"
                if is_topup:
                    msg = (
                        f"✅ *¡Pago confirmado! Tienes {ppu_credits} {credits_word} disponible{'s' if ppu_credits != 1 else ''}.*\n\n"
                        f"Tus créditos se usarán automáticamente cuando alcances el límite diario de tu plan 🗺️\n\n"
                        f"Escribe *pagos* para ver tu saldo."
                    )
                else:
                    msg = (
                        f"✅ *¡Pago confirmado! Tienes {ppu_credits} {credits_word} de ruta.*\n\n"
                        f"Ahora envíame las direcciones que quieres optimizar 🗺️\n\n"
                        f"Cada crédito vale para 1 ruta optimizada.\n"
                        f"Escribe *pagos* para ver tu saldo."
                    )
            else:
                validity = '30 días desde hoy'
                msg = (
                    f"✅ *¡Pago confirmado!*\n\n"
                    f"Bienvenido al plan *{display_name}*. Ya puedes enviarme tus rutas 🚀\n\n"
                    f"📦 *Tu plan:* {display_name}\n"
                    f"🗺️ *Rutas:* {limit}\n"
                    f"📅 *Válido:* {validity}\n\n"
                    f"Escribe *pagos* en cualquier momento para ver o cambiar tu plan."
                )
            MessageSender().provider.send(phone_number, msg)
        except Exception as e:
            logger.error(f"Could not send payment confirmation to {phone_number}: {e}")

    def _send_payment_failed_warning(self, phone_number: str) -> None:
        try:
            from .message_sender import MessageSender
            msg = (
                "⚠️ *No hemos podido cobrar tu suscripción.*\n\n"
                "Verifica tu método de pago y asegúrate de que esté activo.\n"
                "Si no se resuelve en los próximos días, tu plan se cancelará automáticamente.\n\n"
                "Escribe *pagos* para gestionar tu suscripción."
            )
            MessageSender().provider.send(phone_number, msg)
        except Exception as e:
            logger.error(f"Could not send payment failed warning to {phone_number}: {e}")

    def _handle_dispute_created(self, event: dict) -> None:
        dispute = event['data']['object']
        dispute_id = dispute.get('id')
        charge_id = dispute.get('charge')
        amount = dispute.get('amount', 0)
        reason = dispute.get('reason', 'unknown')

        # Look up the user via the disputed charge
        phone_number = None
        try:
            charge = stripe.Charge.retrieve(charge_id)
            customer_id = charge.get('customer')
            if customer_id:
                with self.db.get_session() as db_session:
                    user = db_session.query(User).filter_by(
                        stripe_customer_id=customer_id, deleted_at=None
                    ).first()
                    if not user:
                        logger.warning(f"dispute.created: no user for customer {customer_id} (dispute {dispute_id})")
                        return

                    phone_number = user.phone_number
                    old_tier = user.tier

                    user.tier = 'free'
                    user.tier_started_at = datetime.now(timezone.utc)
                    user.tier_expires_at = None
                    user.stripe_subscription_id = None
                    user.stripe_price_id = None

                    audit = AuditLog.log_action(
                        user_id=user.user_id,
                        action='access_suspended',
                        actor='system',
                        details={
                            'reason': 'dispute',
                            'dispute_id': dispute_id,
                            'charge_id': charge_id,
                            'amount': amount,
                            'dispute_reason': reason,
                            'previous_tier': old_tier,
                        }
                    )
                    db_session.add(audit)

                logger.warning(
                    f"dispute.created: suspended access for {phone_number} "
                    f"(dispute={dispute_id}, charge={charge_id}, reason={reason}, amount={amount})"
                )
        except Exception as e:
            logger.error(f"Error handling dispute {dispute_id}: {e}", exc_info=True)
            return

        if phone_number:
            self._send_dispute_suspension_notice(phone_number)

    def _send_subscription_cancelled(self, phone_number: str) -> None:
        try:
            from .message_sender import MessageSender
            msg = (
                "ℹ️ *Tu suscripción ha sido cancelada.*\n\n"
                "Has pasado al modo *Pago por uso*. "
                "Puedes seguir optimizando rutas a €1,99 por ruta, sin suscripción.\n\n"
                "Escribe *pagos* para recargar créditos o reactivar un plan."
            )
            MessageSender().provider.send(phone_number, msg)
        except Exception as e:
            logger.error(f"Could not send cancellation notice to {phone_number}: {e}")

    def _send_dispute_suspension_notice(self, phone_number: str) -> None:
        try:
            from .message_sender import MessageSender
            msg = (
                "⚠️ *Tu acceso ha sido suspendido temporalmente.*\n\n"
                "Contacta con nosotros en support@mirutapro.es para más información."
            )
            MessageSender().provider.send(phone_number, msg)
        except Exception as e:
            logger.error(f"Could not send dispute suspension notice to {phone_number}: {e}")
