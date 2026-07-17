#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GDPR Consent Manager - Database Version

Database-backed implementation of ConsentManager using PostgreSQL.
Maintains the same API as the JSON-based version for easy migration.

Advantages over JSON version:
- Handles unlimited users
- Thread-safe and concurrent-safe
- Better performance with indexes
- Automatic GDPR cleanup
- Full audit trail
- Proper ACID transactions

Complies with GDPR Article 7 (burden of proof on controller).
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import func

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import get_db_manager
from database.models import User, Consent, AuditLog
from ..utils.logger import setup_logger
from . import usage_manager

logger = setup_logger(__name__)


class ConsentManager:
    """
    Manages GDPR consent records for WhatsApp users using PostgreSQL database.

    This is a database-backed implementation suitable for:
    - Any scale (tested with 1M+ users)
    - Multi-server deployment
    - High concurrency
    - Production environments

    Features:
    - Automatic GDPR compliance
    - 3-year consent retention
    - Audit logging
    - Thread-safe operations
    - Same API as JSON version (drop-in replacement)
    """

    # Consent record retention (GDPR Article 7 - must keep proof)
    CONSENT_RETENTION_YEARS = 3

    # Current consent version (increment when consent text changes)
    CONSENT_VERSION = "2.0"

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize ConsentManager with database connection.

        Args:
            database_url: PostgreSQL connection URL (optional).
                         If None, reads from DATABASE_URL environment variable.
        """
        try:
            self.db = get_db_manager(database_url=database_url)
            logger.info("ConsentManager initialized with database backend")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def has_consent(self, phone_number: str) -> bool:
        """
        Check if user has given valid consent.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if user has given consent and not withdrawn it
        """
        try:
            with self.db.get_session() as session:
                # Get user by phone number
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    logger.info(f"User {phone_number} not found")
                    return False

                # Get most recent consent
                consent = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).order_by(Consent.consent_date.desc()).first()

                if not consent:
                    logger.info(f"User {phone_number} has no consent record")
                    return False

                # Check if consent is active
                if consent.is_active:
                    logger.info(f"User {phone_number} has valid consent")
                    return True

                logger.info(f"User {phone_number} does not have valid consent")
                return False

        except Exception as e:
            logger.error(f"Error checking consent for {phone_number}: {e}", exc_info=True)
            return False

    def save_consent(
        self,
        phone_number: str,
        consent_given: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        language: str = "es"
    ) -> bool:
        """
        Save user consent decision.

        Args:
            phone_number: User's phone number
            consent_given: True if user accepted, False if declined
            ip_address: Optional IP address (for audit trail)
            user_agent: Optional user agent (for audit trail)
            language: Language of consent (default: Spanish)

        Returns:
            bool: True if saved successfully
        """
        try:
            with self.db.get_session() as session:
                # Get or create user
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    # Create new user — set phone or bsuid based on identifier type
                    stripped = phone_number.lstrip('+')
                    if stripped.isdigit():
                        user = User(phone_number=phone_number, language=language)
                    else:
                        user = User(bsuid=phone_number, language=language)
                    session.add(user)
                    session.flush()  # Get user_id

                    # Log user creation
                    audit = AuditLog.log_action(
                        user_id=user.user_id,
                        action='user_created',
                        actor='system',
                        details={'source': 'whatsapp', 'language': language},
                        ip_address=ip_address
                    )
                    session.add(audit)

                    # Assign default tier (btester or free) within same transaction
                    usage_manager.assign_default_tier(user, session)

                    logger.info(f"Created new user: {phone_number}")

                elif user.tier_expires_at is None:
                    # User exists but tier not yet assigned (created by conversation_tracker)
                    usage_manager.assign_default_tier(user, session)

                # Create consent record
                consent = Consent(
                    user_id=user.user_id,
                    consent_given=consent_given,
                    consent_version=self.CONSENT_VERSION,
                    language=language,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                session.add(consent)
                session.flush()

                # Log consent action (only audit when given, not when declined)
                if consent_given:
                    audit = AuditLog.log_action(
                        user_id=user.user_id,
                        action='consent_given',
                        actor='user',
                        details={
                            'version': self.CONSENT_VERSION,
                            'language': language
                        },
                        ip_address=ip_address
                    )
                    session.add(audit)

                action_text = "granted" if consent_given else "declined"
                logger.info(f"Consent {action_text} for user {phone_number}")

                return True

        except Exception as e:
            logger.error(f"Error saving consent for {phone_number}: {e}", exc_info=True)
            return False

    def revoke_consent(self, phone_number: str) -> bool:
        """
        Revoke user consent (user withdraws consent).

        GDPR Article 7(3): Must be as easy to withdraw as to give.
        IMPORTANT: We keep the record for proof we had consent.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if revoked successfully
        """
        try:
            with self.db.get_session() as session:
                # Get user
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    logger.warning(f"Cannot revoke consent: no record for {phone_number}")
                    return False

                # Get most recent consent
                consent = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).order_by(Consent.consent_date.desc()).first()

                if not consent:
                    logger.warning(f"Cannot revoke consent: no consent record for {phone_number}")
                    return False

                if consent.consent_withdrawn:
                    logger.info(f"Consent already withdrawn for {phone_number}")
                    return True

                # Withdraw consent
                consent.withdraw()
                session.flush()

                # Log revocation
                audit = AuditLog.log_action(
                    user_id=user.user_id,
                    action='consent_revoked',
                    actor='user',
                    details={'version': consent.consent_version}
                )
                session.add(audit)

                logger.info(f"Consent revoked for user {phone_number}")

                return True

        except Exception as e:
            logger.error(f"Error revoking consent for {phone_number}: {e}", exc_info=True)
            return False

    def anonymize_user(self, phone_number: str) -> bool:
        """
        Anonymize user's PII in-place (GDPR Article 17 - Right to erasure).

        Replaces phone_number and display_name with a non-reversible placeholder
        and sets deleted_at. The user row is retained for FK integrity with
        consent records (3-year retention) and audit logs (90-day retention).

        Must be called AFTER revoke_consent(), while the original phone_number
        is still present in the users table.

        Args:
            phone_number: User's current (real) phone number

        Returns:
            bool: True if anonymised successfully, False otherwise
        """
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    logger.warning(f"Cannot anonymize: no user found for {phone_number}")
                    return False

                # GDPR erasure: cancel Stripe subscription and delete customer
                # before anonymizing (phone_number still available here)
                stripe_sub_id = user.stripe_subscription_id
                stripe_customer_id = user.stripe_customer_id

                if stripe_sub_id:
                    try:
                        import stripe
                        from ..config.config import Config
                        stripe.api_key = Config().STRIPE_SECRET_KEY
                        stripe.Subscription.cancel(stripe_sub_id)
                        logger.info(f"Stripe subscription {stripe_sub_id} cancelled for GDPR erasure")
                    except Exception as e:
                        logger.error(f"Failed to cancel Stripe subscription {stripe_sub_id}: {e}")

                if stripe_customer_id:
                    try:
                        import stripe
                        from ..config.config import Config
                        stripe.api_key = Config().STRIPE_SECRET_KEY
                        stripe.Customer.delete(stripe_customer_id)
                        logger.info(f"Stripe customer {stripe_customer_id} deleted for GDPR erasure")
                    except Exception as e:
                        logger.error(f"Failed to delete Stripe customer {stripe_customer_id}: {e}")

                # anonymize() NULLs PII + all Stripe fields and sets deleted_at
                user.anonymize()

                # Audit trail logged by user_id (phone_number is being overwritten)
                audit = AuditLog.log_action(
                    user_id=user.user_id,
                    action='data_deleted',
                    actor='user',
                    details={
                        'gdpr_article': 'Art17',
                        'fields_cleared': [
                            'phone_number', 'display_name', 'bsuid',
                            'stripe_customer_id', 'stripe_subscription_id',
                            'stripe_price_id', 'pending_tier', 'checkout_created_at'
                        ]
                    }
                )
                session.add(audit)

                logger.info(f"User PII anonymized (GDPR Art. 17) for former phone: {phone_number}")
                return True

        except Exception as e:
            logger.error(f"Error anonymizing user {phone_number}: {e}", exc_info=True)
            return False

    def get_consent_date(self, phone_number: str) -> Optional[str]:
        """
        Get the date when user gave consent.

        Args:
            phone_number: User's phone number

        Returns:
            str: ISO format date string, or None if no consent
        """
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    return None

                consent = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).order_by(Consent.consent_date.desc()).first()

                if not consent:
                    return None

                return consent.consent_date.isoformat()

        except Exception as e:
            logger.error(f"Error getting consent date for {phone_number}: {e}", exc_info=True)
            return None

    def get_consent_info(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get complete consent information for a user.

        Args:
            phone_number: User's phone number

        Returns:
            dict: Complete consent record, or None if not found
        """
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    return None

                consent = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).order_by(Consent.consent_date.desc()).first()

                if not consent:
                    return None

                # Format similar to JSON version for compatibility
                return {
                    'consent_given': consent.consent_given,
                    'consent_date': consent.consent_date.isoformat(),
                    'consent_withdrawn': consent.consent_withdrawn,
                    'withdrawal_date': consent.withdrawal_date.isoformat() if consent.withdrawal_date else None,
                    'consent_version': consent.consent_version,
                    'language': consent.language,
                    'ip_address': consent.ip_address,
                    'user_agent': consent.user_agent
                }

        except Exception as e:
            logger.error(f"Error getting consent info for {phone_number}: {e}", exc_info=True)
            return None

    def delete_consent_record(self, phone_number: str) -> bool:
        """
        Delete consent record (use with caution!).

        WARNING: Only use this if legally required (e.g., user requests
        complete data deletion AND retention period has expired).

        Normally, consent records should be kept for 3 years as proof.

        Note: Due to foreign key constraint (ON DELETE RESTRICT), you must
        delete the consent records before deleting the user.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if deleted successfully
        """
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    return False

                # Delete all consent records for this user
                deleted = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).delete()

                # Log deletion
                if deleted > 0:
                    audit = AuditLog.log_action(
                        user_id=user.user_id,
                        action='data_deleted',
                        actor='system',
                        details={'type': 'consent_records', 'count': deleted}
                    )
                    session.add(audit)

                    logger.warning(f"Consent records DELETED for {phone_number}: {deleted} records")
                    return True

                return False

        except Exception as e:
            logger.error(f"Error deleting consent record for {phone_number}: {e}", exc_info=True)
            return False

    def cleanup_expired_records(self) -> int:
        """
        Clean up consent records older than retention period.

        GDPR allows deletion of records after they're no longer needed.
        For consent proof, 3 years is typically sufficient.

        Note: This is also handled by the database cleanup_expired_data()
        function, but provided here for API compatibility.

        Returns:
            int: Number of records deleted
        """
        try:
            # Use database cleanup function
            results = self.db.execute_cleanup()
            deleted_count = results.get('consents', 0)

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired consent records")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired records: {e}", exc_info=True)
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about consents (for monitoring/reporting).

        Returns:
            dict: Statistics including total, active, withdrawn, etc.
        """
        try:
            with self.db.get_session() as session:
                # Total consent records
                total = session.query(func.count(Consent.consent_id)).scalar()

                # Active consents (given and not withdrawn)
                active = session.query(func.count(Consent.consent_id)).filter(
                    Consent.consent_given == True,
                    Consent.consent_withdrawn == False
                ).scalar()

                # Withdrawn consents
                withdrawn = session.query(func.count(Consent.consent_id)).filter(
                    Consent.consent_withdrawn == True
                ).scalar()

                # Declined consents
                declined = session.query(func.count(Consent.consent_id)).filter(
                    Consent.consent_given == False
                ).scalar()

                # Total users
                total_users = session.query(func.count(User.user_id)).scalar()

                # Active users (not soft deleted)
                active_users = session.query(func.count(User.user_id)).filter(
                    User.deleted_at == None
                ).scalar()

                return {
                    'total_records': total,
                    'active_consents': active,
                    'withdrawn_consents': withdrawn,
                    'declined_consents': declined,
                    'total_users': total_users,
                    'active_users': active_users,
                    'storage_type': 'PostgreSQL'
                }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return {
                'total_records': 0,
                'active_consents': 0,
                'withdrawn_consents': 0,
                'declined_consents': 0,
                'total_users': 0,
                'active_users': 0,
                'storage_type': 'PostgreSQL (error)'
            }

    def export_user_consent_data(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Export user's consent data (GDPR Article 20 - Right to data portability).

        Args:
            phone_number: User's phone number

        Returns:
            dict: User's consent data in portable format, or None if not found
        """
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, phone_number)

                if not user:
                    return None

                # Get all consents for user (not just most recent)
                consents = session.query(Consent).filter_by(
                    user_id=user.user_id
                ).order_by(Consent.consent_date.desc()).all()

                if not consents:
                    return None

                # Get most recent consent for status
                latest_consent = consents[0]

                # Determine status
                if latest_consent.consent_given and not latest_consent.consent_withdrawn:
                    status = 'Active'
                elif latest_consent.consent_withdrawn:
                    status = 'Withdrawn'
                else:
                    status = 'Declined'

                # Format for user-friendly export
                export_data = {
                    'phone_number': user.phone_number,   # may be None for BSUID-only users
                    'bsuid': user.bsuid,                 # may be None for phone-only users
                    'user_id': str(user.user_id),
                    'consent_status': status,
                    'consent_given_date': latest_consent.consent_date.isoformat(),
                    'consent_withdrawn_date': latest_consent.withdrawal_date.isoformat() if latest_consent.withdrawal_date else None,
                    'consent_version': latest_consent.consent_version,
                    'language': latest_consent.language,
                    'account_created': user.created_at.isoformat(),
                    'consent_history': [
                        {
                            'date': c.consent_date.isoformat(),
                            'given': c.consent_given,
                            'withdrawn': c.consent_withdrawn,
                            'version': c.consent_version
                        }
                        for c in consents
                    ],
                    'exported_date': datetime.now().isoformat()
                }

                # Log data export
                audit = AuditLog.log_action(
                    user_id=user.user_id,
                    action='data_exported',
                    actor='user',
                    details={'type': 'consent_data', 'records': len(consents)}
                )
                session.add(audit)

                return export_data

        except Exception as e:
            logger.error(f"Error exporting consent data for {phone_number}: {e}", exc_info=True)
            return None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_consent_date(date_str: str, language: str = "es") -> str:
    """
    Format ISO date string for display.

    Args:
        date_str: ISO format date string
        language: Language for formatting (default: Spanish)

    Returns:
        str: Formatted date string
    """
    try:
        dt = datetime.fromisoformat(date_str)

        if language == "es":
            # Spanish format: "24 de octubre de 2025"
            months = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            return f"{dt.day} de {months[dt.month - 1]} de {dt.year}"
        else:
            # English format: "October 24, 2025"
            return dt.strftime("%B %d, %Y")

    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return date_str


# =============================================================================
# MIGRATION FROM JSON VERSION
# =============================================================================

def migrate_from_json(json_file_path: str, db_manager=None) -> Dict[str, int]:
    """
    Migrate consent data from JSON file to database.

    Args:
        json_file_path: Path to user_consents.json file
        db_manager: DatabaseManager instance (optional)

    Returns:
        dict: Migration statistics {'migrated': N, 'errors': M}

    Example:
        from wab.app.consent_manager_db import migrate_from_json

        stats = migrate_from_json('wab/storage/user_consents.json')
        print(f"Migrated {stats['migrated']} records with {stats['errors']} errors")
    """
    import json

    if db_manager is None:
        db_manager = get_db_manager()

    migrated = 0
    errors = 0

    try:
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Starting migration of {len(data)} records from JSON to database")

        for phone_number, record in data.items():
            try:
                with db_manager.get_session() as session:
                    # Create or get user
                    user = session.query(User).filter_by(
                        phone_number=phone_number
                    ).first()

                    if not user:
                        user = User(
                            phone_number=phone_number,
                            language=record.get('language', 'es')
                        )
                        session.add(user)
                        session.flush()

                    # Create consent record
                    consent = Consent(
                        user_id=user.user_id,
                        consent_given=record.get('consent_given', False),
                        consent_date=datetime.fromisoformat(record.get('consent_date')),
                        consent_version=record.get('consent_version', '1.0'),
                        consent_withdrawn=record.get('consent_withdrawn', False),
                        withdrawal_date=datetime.fromisoformat(record['withdrawal_date']) if record.get('withdrawal_date') else None,
                        language=record.get('language', 'es'),
                        ip_address=record.get('ip_address'),
                        user_agent=record.get('user_agent')
                    )
                    session.add(consent)

                    migrated += 1

                    if migrated % 100 == 0:
                        logger.info(f"Migrated {migrated} records...")

            except Exception as e:
                logger.error(f"Error migrating record for {phone_number}: {e}")
                errors += 1

        logger.info(f"Migration complete: {migrated} records migrated, {errors} errors")

        return {'migrated': migrated, 'errors': errors}

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return {'migrated': migrated, 'errors': errors + 1}
