#!/usr/bin/env python3
"""
Webhook Validators
Validates WhatsApp webhook signatures and data.
"""

import hmac
import hashlib
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def verify_webhook_signature(payload, signature, app_secret):
    """
    Verify the webhook signature from WhatsApp.
    This ensures the webhook request is actually from WhatsApp.

    Args:
        payload (bytes): Raw request body
        signature (str): Signature from X-Hub-Signature-256 header
        app_secret (str): WhatsApp App Secret from Meta Developer Portal

    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # App secret is mandatory for security - reject if not configured
        if not app_secret or app_secret == 'your_app_secret_here' or app_secret.strip() == '':
            logger.error("App secret not configured - REJECTING request for security")
            raise ValueError("Webhook signature verification requires valid WHATSAPP_APP_SECRET")

        # Check if signature exists
        if not signature:
            logger.warning("No signature provided in request")
            return False

        # Extract signature (format: sha256=<signature>)
        if signature.startswith('sha256='):
            signature = signature[7:]
        else:
            logger.warning("Invalid signature format")
            return False

        # Calculate expected signature
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures (constant time comparison to prevent timing attacks)
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning("Signature verification failed")

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}", exc_info=True)
        return False


def validate_phone_number(phone_number):
    """
    Validate phone number format.

    Args:
        phone_number (str): Phone number to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Remove any spaces or special characters
        cleaned = phone_number.strip().replace(' ', '').replace('-', '').replace('+', '')

        # Check if it's all digits
        if not cleaned.isdigit():
            return False

        # Check minimum length (at least 10 digits)
        if len(cleaned) < 10:
            return False

        # Check maximum length (max 15 digits per E.164 standard)
        if len(cleaned) > 15:
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating phone number: {e}")
        return False


def validate_message_text(text, max_length=4096):
    """
    Validate message text length and content.
    WhatsApp has a 4096 character limit for text messages.

    Args:
        text (str): Message text to validate
        max_length (int): Maximum allowed length (default: 4096)

    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    try:
        if not text:
            return False, "Message text is empty"

        if not isinstance(text, str):
            return False, "Message text must be a string"

        if len(text) > max_length:
            return False, f"Message text exceeds maximum length of {max_length} characters"

        return True, ""

    except Exception as e:
        logger.error(f"Error validating message text: {e}")
        return False, f"Validation error: {str(e)}"
