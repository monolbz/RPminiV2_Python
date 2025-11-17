#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GDPR Consent Manager

Handles storage and retrieval of user consent decisions.
Complies with GDPR Article 7 (burden of proof on controller).

Storage format:
{
    "phone_number": {
        "consent_given": true/false,
        "consent_date": "2025-10-24T10:30:00",
        "consent_withdrawn": false,
        "withdrawal_date": null,
        "ip_address": "xxx.xxx.xxx.xxx" (optional),
        "user_agent": "WhatsApp/xxx" (optional),
        "consent_version": "1.0",
        "language": "es"
    }
}

GDPR Requirements:
- Must prove consent was obtained (Article 7(1))
- Must record when consent was given
- Must allow easy withdrawal (Article 7(3))
- Must keep records even after withdrawal (for proof)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from ..utils.logger import setup_logger
from ..utils.encryption import DataEncryptor

logger = setup_logger(__name__)


class ConsentManager:
    """
    Manages GDPR consent records for WhatsApp users.

    This is a simple JSON-based implementation suitable for:
    - Small to medium scale (< 10,000 users)
    - Single server deployment

    For production at scale, consider:
    - Database storage (SQLite, PostgreSQL)
    - Encryption at rest
    - Audit logging
    - Backup strategy
    """

    # Consent record retention (GDPR Article 7 - must keep proof)
    CONSENT_RETENTION_YEARS = 3

    # Current consent version (increment when consent text changes)
    CONSENT_VERSION = "1.0"

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize ConsentManager.

        Args:
            storage_path: Path to JSON file for storing consents.
                         Defaults to wab/storage/user_consents.json
        """
        if storage_path is None:
            # Default path: wab/storage/user_consents.json
            base_dir = Path(__file__).parent.parent
            storage_dir = base_dir / 'storage'
            storage_dir.mkdir(exist_ok=True)
            storage_path = storage_dir / 'user_consents.json'

        self.storage_path = Path(storage_path)

        # Initialize encryptor for phone number hashing (GDPR compliance)
        try:
            self.encryptor = DataEncryptor()
            logger.info("Encryption enabled for consent manager")
        except Exception as e:
            logger.warning(f"Encryption not available: {e}. Phone numbers will not be hashed.")
            self.encryptor = None

        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_data({})
            logger.info(f"Created consent storage at: {self.storage_path}")

    def _load_data(self) -> Dict[str, Any]:
        """Load consent data from storage."""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error loading consent data: {e}")
            # Backup corrupted file
            backup_path = self.storage_path.with_suffix('.json.backup')
            self.storage_path.rename(backup_path)
            logger.warning(f"Corrupted file backed up to: {backup_path}")
            return {}
        except Exception as e:
            logger.error(f"Error reading consent file: {e}")
            return {}

    def _save_data(self, data: Dict[str, Any]):
        """Save consent data to storage."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving consent data: {e}", exc_info=True)
            raise

    def _get_consent_key(self, phone_number: str) -> str:
        """
        Get consent key for a phone number.

        If encryption is enabled, returns hashed key (phone_xxx).
        Otherwise returns plain phone number (fallback).

        Args:
            phone_number: Plain phone number

        Returns:
            str: Hashed key or plain phone number
        """
        if self.encryptor:
            return self.encryptor.hash_phone(phone_number)
        else:
            return phone_number

    def has_consent(self, phone_number: str) -> bool:
        """
        Check if user has given valid consent.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if user has given consent and not withdrawn it
        """
        data = self._load_data()

        # Get hashed key for lookup
        consent_key = self._get_consent_key(phone_number)

        if consent_key not in data:
            return False

        record = data[consent_key]

        # Check if consent was given and not withdrawn
        consent_given = record.get('consent_given', False)
        consent_withdrawn = record.get('consent_withdrawn', False)

        if consent_given and not consent_withdrawn:
            logger.info(f"User (hashed key: {consent_key[:20]}...) has valid consent")
            return True

        logger.info(f"User (hashed key: {consent_key[:20]}...) does not have valid consent")
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
            data = self._load_data()

            # Get hashed key for storage
            consent_key = self._get_consent_key(phone_number)

            # Create consent record
            consent_record = {
                'consent_given': consent_given,
                'consent_date': datetime.now().isoformat(),
                'consent_withdrawn': False,
                'withdrawal_date': None,
                'consent_version': self.CONSENT_VERSION,
                'language': language
            }

            # Add optional metadata
            if ip_address:
                consent_record['ip_address'] = ip_address
            if user_agent:
                consent_record['user_agent'] = user_agent

            # Store record with hashed key
            data[consent_key] = consent_record
            self._save_data(data)

            action = "granted" if consent_given else "declined"
            logger.info(f"Consent {action} (hashed key: {consent_key[:20]}...)")

            return True

        except Exception as e:
            logger.error(f"Error saving consent: {e}", exc_info=True)
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
            data = self._load_data()

            # Get hashed key for lookup
            consent_key = self._get_consent_key(phone_number)

            if consent_key not in data:
                logger.warning(f"Cannot revoke consent: no record (hashed key: {consent_key[:20]}...)")
                return False

            # Mark consent as withdrawn (keep record for legal proof)
            data[consent_key]['consent_withdrawn'] = True
            data[consent_key]['withdrawal_date'] = datetime.now().isoformat()

            self._save_data(data)
            logger.info(f"Consent revoked (hashed key: {consent_key[:20]}...)")

            return True

        except Exception as e:
            logger.error(f"Error revoking consent: {e}", exc_info=True)
            return False

    def get_consent_date(self, phone_number: str) -> Optional[str]:
        """
        Get the date when user gave consent.

        Args:
            phone_number: User's phone number

        Returns:
            str: ISO format date string, or None if no consent
        """
        data = self._load_data()

        # Get hashed key for lookup
        consent_key = self._get_consent_key(phone_number)

        if consent_key not in data:
            return None

        return data[consent_key].get('consent_date')

    def get_consent_info(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get complete consent information for a user.

        Args:
            phone_number: User's phone number

        Returns:
            dict: Complete consent record, or None if not found
        """
        data = self._load_data()

        # Get hashed key for lookup
        consent_key = self._get_consent_key(phone_number)

        return data.get(consent_key)

    def delete_consent_record(self, phone_number: str) -> bool:
        """
        Delete consent record (use with caution!).

        WARNING: Only use this if legally required (e.g., user requests
        complete data deletion AND retention period has expired).

        Normally, consent records should be kept for 3 years as proof.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if deleted successfully
        """
        try:
            data = self._load_data()

            # Get hashed key for lookup
            consent_key = self._get_consent_key(phone_number)

            if consent_key in data:
                del data[consent_key]
                self._save_data(data)
                logger.warning(f"Consent record DELETED (hashed key: {consent_key[:20]}...)")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting consent record: {e}", exc_info=True)
            return False

    def cleanup_expired_records(self) -> int:
        """
        Clean up consent records older than retention period.

        GDPR allows deletion of records after they're no longer needed.
        For consent proof, 3 years is typically sufficient.

        Returns:
            int: Number of records deleted
        """
        try:
            data = self._load_data()
            current_time = datetime.now()
            expired_users = []

            for phone_number, record in data.items():
                # Check if record is older than retention period
                consent_date_str = record.get('consent_date')
                if not consent_date_str:
                    continue

                consent_date = datetime.fromisoformat(consent_date_str)
                age = current_time - consent_date

                if age > timedelta(days=365 * self.CONSENT_RETENTION_YEARS):
                    expired_users.append(phone_number)

            # Delete expired records
            for phone_number in expired_users:
                del data[phone_number]

            if expired_users:
                self._save_data(data)
                logger.info(f"Cleaned up {len(expired_users)} expired consent records")

            return len(expired_users)

        except Exception as e:
            logger.error(f"Error cleaning up expired records: {e}", exc_info=True)
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about consents (for monitoring/reporting).

        Returns:
            dict: Statistics including total, active, withdrawn, etc.
        """
        data = self._load_data()

        total = len(data)
        active = sum(1 for r in data.values()
                    if r.get('consent_given') and not r.get('consent_withdrawn'))
        withdrawn = sum(1 for r in data.values()
                       if r.get('consent_withdrawn'))
        declined = sum(1 for r in data.values()
                      if not r.get('consent_given'))

        return {
            'total_records': total,
            'active_consents': active,
            'withdrawn_consents': withdrawn,
            'declined_consents': declined,
            'storage_path': str(self.storage_path)
        }

    def export_user_consent_data(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Export user's consent data (GDPR Article 20 - Right to data portability).

        Args:
            phone_number: User's phone number

        Returns:
            dict: User's consent data in portable format, or None if not found
        """
        data = self._load_data()

        # Get hashed key for lookup
        consent_key = self._get_consent_key(phone_number)

        if consent_key not in data:
            return None

        record = data[consent_key]

        # Format for user-friendly export
        export_data = {
            'phone_number': phone_number,
            'consent_status': 'Active' if (record.get('consent_given') and not record.get('consent_withdrawn')) else 'Withdrawn' if record.get('consent_withdrawn') else 'Declined',
            'consent_given_date': record.get('consent_date'),
            'consent_withdrawn_date': record.get('withdrawal_date'),
            'consent_version': record.get('consent_version'),
            'language': record.get('language'),
            'exported_date': datetime.now().isoformat()
        }

        return export_data


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
# NOTES FOR PRODUCTION
# =============================================================================

"""
PRODUCTION CONSIDERATIONS:

1. SCALE:
   - JSON file is fine for < 10,000 users
   - For larger scale, migrate to:
     * SQLite (< 100,000 users)
     * PostgreSQL (> 100,000 users)

2. SECURITY:
   - Consider encrypting the JSON file
   - Restrict file permissions (chmod 600)
   - Use environment variables for paths
   - Implement audit logging

3. BACKUP:
   - Automatic backups (daily)
   - Store backups securely
   - Test restore procedures

4. MONITORING:
   - Track consent rates
   - Monitor withdrawal rates
   - Alert on unusual patterns

5. LEGAL:
   - Consult lawyer for retention periods
   - Document your data protection measures
   - Register with AEPD if required

6. MIGRATION PATH:
   This JSON implementation can be replaced with a database
   without changing the API:

   class ConsentManager:
       def __init__(self, db_connection):
           self.db = db_connection

       def has_consent(self, phone_number):
           return self.db.query("SELECT ...")

   All calling code remains the same!
"""
