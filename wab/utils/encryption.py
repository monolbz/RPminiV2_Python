#!/usr/bin/env python3
"""
Data Encryption Utility
Provides field-level encryption for sensitive user data (phone numbers).

GDPR Compliance:
- Encrypts PII (Personally Identifiable Information) at rest
- Uses Fernet (symmetric encryption) from cryptography library
- Supports key rotation for enhanced security
- Provides deterministic hashing for lookups

Architecture:
- Phone numbers: Encrypted (reversible) for storage
- Lookup keys: Hashed (one-way) with SHA256 for fast lookups
- Metadata: Plain text (timestamps, flags) for debugging

Example Usage:
    >>> encryptor = DataEncryptor()
    >>> encrypted_phone = encryptor.encrypt_phone("+34644252886")
    >>> lookup_key = encryptor.hash_phone("+34644252886")
    >>> original = encryptor.decrypt_phone(encrypted_phone)
"""

import os
import hashlib
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

# Handle imports for both module usage and standalone execution
try:
    from ..utils.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class DataEncryptor:
    """
    Handles encryption/decryption of sensitive data.

    Uses Fernet symmetric encryption:
    - AES 128-bit encryption in CBC mode
    - HMAC authentication for integrity
    - Timestamped tokens (can verify age)
    - URL-safe base64 encoding
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryptor with encryption key.

        Args:
            encryption_key: Base64-encoded Fernet key.
                           If None, loads from ENCRYPTION_KEY environment variable.

        Raises:
            ValueError: If no encryption key is provided or found.
        """
        # Get encryption key from parameter or environment
        if encryption_key is None:
            encryption_key = os.getenv('ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError(
                "No encryption key provided. "
                "Set ENCRYPTION_KEY environment variable or pass key to constructor."
            )

        try:
            # Initialize Fernet cipher
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            logger.info("Data encryptor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryptor: {e}")
            raise ValueError(f"Invalid encryption key: {e}")

    # ========================================================================
    # Phone Number Encryption (Reversible)
    # ========================================================================

    def encrypt_phone(self, phone_number: str) -> str:
        """
        Encrypt a phone number for secure storage.

        Args:
            phone_number: Plain phone number (e.g., "+34644252886")

        Returns:
            Encrypted phone number as base64 string
            Format: "gAAAAABh1x2y..." (Fernet token)

        Example:
            >>> encryptor.encrypt_phone("+34644252886")
            'gAAAAABh1x2yK8...'
        """
        try:
            # Normalize phone number (remove spaces, ensure string)
            normalized = str(phone_number).strip()

            # Encrypt using Fernet
            encrypted_bytes = self.cipher.encrypt(normalized.encode('utf-8'))
            encrypted_str = encrypted_bytes.decode('utf-8')

            logger.debug(f"Encrypted phone number (length: {len(normalized)})")
            return encrypted_str

        except Exception as e:
            logger.error(f"Error encrypting phone number: {e}")
            raise

    def decrypt_phone(self, encrypted_phone: str) -> str:
        """
        Decrypt an encrypted phone number.

        Args:
            encrypted_phone: Encrypted phone number from encrypt_phone()

        Returns:
            Original plain phone number

        Raises:
            InvalidToken: If encrypted data is corrupted or key is wrong

        Example:
            >>> encryptor.decrypt_phone('gAAAAABh1x2yK8...')
            '+34644252886'
        """
        try:
            # Decrypt using Fernet
            decrypted_bytes = self.cipher.decrypt(encrypted_phone.encode('utf-8'))
            phone_number = decrypted_bytes.decode('utf-8')

            logger.debug(f"Decrypted phone number (length: {len(phone_number)})")
            return phone_number

        except InvalidToken:
            logger.error("Failed to decrypt phone number - invalid token or wrong key")
            raise ValueError("Decryption failed - data may be corrupted or key is incorrect")
        except Exception as e:
            logger.error(f"Error decrypting phone number: {e}")
            raise

    # ========================================================================
    # Phone Number Hashing (One-way, for lookups)
    # ========================================================================

    def hash_phone(self, phone_number: str) -> str:
        """
        Create a one-way hash of phone number for use as lookup key.

        This is used for dictionary/JSON keys where we need to:
        1. Look up data by phone number
        2. Keep keys consistent
        3. Protect the actual phone number

        Args:
            phone_number: Plain phone number

        Returns:
            SHA256 hash as hex string (64 characters)
            Format: "phone_a1b2c3d4e5f6..."

        Example:
            >>> encryptor.hash_phone("+34644252886")
            'phone_a3f5b9d2c8e1...'

        Note: This is deterministic - same input always produces same hash.
              This allows lookups but prevents reverse engineering.
        """
        try:
            # Normalize phone number
            normalized = str(phone_number).strip()

            # Create SHA256 hash
            hash_obj = hashlib.sha256(normalized.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()

            # Prefix with "phone_" for clarity in JSON files
            hash_key = f"phone_{hash_hex[:16]}"  # Use first 16 chars for brevity

            logger.debug(f"Hashed phone number to key: {hash_key}")
            return hash_key

        except Exception as e:
            logger.error(f"Error hashing phone number: {e}")
            raise

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def encrypt_dict_phones(self, data: dict) -> dict:
        """
        Encrypt phone numbers in a dictionary (keys and/or values).

        This is useful for migrating existing data files.

        Args:
            data: Dictionary with phone numbers as keys
                  Example: {"+34644252886": "2025-11-14T08:50:19.226032"}

        Returns:
            Dictionary with encrypted phones as keys, original values preserved
            Example: {"phone_a1b2c3": "2025-11-14T08:50:19.226032"}

        Example:
            >>> original = {"+34644252886": "2025-11-14T08:50:19.226032"}
            >>> encrypted = encryptor.encrypt_dict_phones(original)
            >>> # Keys are hashed, values unchanged
        """
        encrypted_data = {}

        for phone, value in data.items():
            try:
                # Hash phone for key (deterministic lookup)
                hashed_key = self.hash_phone(phone)
                encrypted_data[hashed_key] = value
                logger.debug(f"Encrypted key: {phone} -> {hashed_key}")
            except Exception as e:
                logger.warning(f"Failed to encrypt phone {phone}: {e}")
                # Skip this entry rather than failing entirely
                continue

        logger.info(f"Encrypted {len(encrypted_data)} phone number keys")
        return encrypted_data

    # ========================================================================
    # Key Management
    # ========================================================================

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key (44 characters)

        Usage:
            1. Generate key: key = DataEncryptor.generate_key()
            2. Save to .env: ENCRYPTION_KEY={key}
            3. NEVER commit .env to git
            4. Back up key securely (losing key = losing data)

        Example:
            >>> key = DataEncryptor.generate_key()
            >>> print(key)
            'xK8vQ2L9mP5nR7sT1uW3yZ6bC4eF8hJ0kM2oP5qR9sT='
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')

    def verify_key(self) -> bool:
        """
        Verify that the encryption key is valid.

        Returns:
            True if key can encrypt/decrypt, False otherwise

        Example:
            >>> encryptor = DataEncryptor()
            >>> encryptor.verify_key()
            True
        """
        try:
            test_data = "test_phone_+1234567890"
            encrypted = self.encrypt_phone(test_data)
            decrypted = self.decrypt_phone(encrypted)
            return decrypted == test_data
        except Exception as e:
            logger.error(f"Key verification failed: {e}")
            return False

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a string appears to be Fernet-encrypted data.

        Args:
            value: String to check

        Returns:
            True if value looks like encrypted data, False otherwise

        Example:
            >>> encryptor.is_encrypted("gAAAAABh1x2y...")
            True
            >>> encryptor.is_encrypted("+34644252886")
            False
        """
        # Fernet tokens start with "gAAAAA" (base64 encoded)
        # and are typically 100+ characters
        return (
            isinstance(value, str) and
            value.startswith('gAAAAA') and
            len(value) > 50
        )

    def is_hashed_key(self, key: str) -> bool:
        """
        Check if a string is a hashed phone key.

        Args:
            key: String to check

        Returns:
            True if key is in our hashed format, False otherwise

        Example:
            >>> encryptor.is_hashed_key("phone_a1b2c3d4")
            True
            >>> encryptor.is_hashed_key("+34644252886")
            False
        """
        return isinstance(key, str) and key.startswith('phone_')


# ========================================================================
# Command-line utility for key generation and testing
# ========================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Load .env file for standalone execution
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
    except ImportError:
        pass  # dotenv not installed, rely on system env vars

    print("\nData Encryption Utility")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == '--generate-key':
        # Generate new encryption key
        print("\nGenerating new encryption key...")
        key = DataEncryptor.generate_key()
        print(f"\nENCRYPTION_KEY={key}")
        print("\nIMPORTANT:")
        print("1. Add this to your .env file")
        print("2. NEVER commit .env to git")
        print("3. Back up this key securely (losing it = losing data)")
        print("4. Use same key across all environments for same data")

    elif len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test encryption with current key
        print("\nTesting encryption with current ENCRYPTION_KEY...")
        try:
            encryptor = DataEncryptor()

            # Test phone encryption
            test_phone = "+34644252886"
            print(f"\nOriginal phone: {test_phone}")

            encrypted = encryptor.encrypt_phone(test_phone)
            print(f"Encrypted: {encrypted[:50]}...")

            hashed = encryptor.hash_phone(test_phone)
            print(f"Hashed key: {hashed}")

            decrypted = encryptor.decrypt_phone(encrypted)
            print(f"Decrypted: {decrypted}")

            if decrypted == test_phone:
                print("\n[OK] Encryption test PASSED")
            else:
                print("\n[FAIL] Encryption test FAILED")

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            print("\nMake sure ENCRYPTION_KEY is set in .env")

    else:
        # Show usage
        print("\nUsage:")
        print("  python wab/utils/encryption.py --generate-key")
        print("      Generate a new encryption key for .env")
        print("\n  python wab/utils/encryption.py --test")
        print("      Test encryption with current ENCRYPTION_KEY")
        print()
