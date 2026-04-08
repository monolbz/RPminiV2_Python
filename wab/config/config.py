#!/usr/bin/env python3
"""
Configuration Manager
Manages configuration and environment variables for WhatsApp webhook.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class for WhatsApp webhook server."""

    def __init__(self):
        # Messaging provider: 'meta' (default) or 'twilio'
        self.MESSAGING_PROVIDER = os.getenv('MESSAGING_PROVIDER', 'meta').lower()

        # WhatsApp Cloud API Configuration (Meta)
        self.WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', '')
        self.WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', '')
        self.WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
        self.WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
        self.WHATSAPP_APP_SECRET = os.getenv('WHATSAPP_APP_SECRET', '')

        # Twilio WhatsApp Sandbox Configuration
        self.TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

        # Server Configuration
        self.WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
        self.WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

        # Session Configuration
        self.SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', 24))
        self.SESSION_STORE_TYPE = os.getenv('SESSION_STORE_TYPE', 'json')
        self.SESSION_STORE_PATH = os.getenv('SESSION_STORE_PATH', 'wab/data/sessions.json')

        # Template Configuration
        self.WHATSAPP_DEFAULT_TEMPLATE = os.getenv('WHATSAPP_DEFAULT_TEMPLATE', 'hello_world')
        self.WHATSAPP_TEMPLATES_CONFIG = os.getenv('WHATSAPP_TEMPLATES_CONFIG', 'wab/config/templates.json')

        # Tier / Usage limits
        self.BTESTER_MAX_USERS = int(os.getenv('BTESTER_MAX_USERS', '20'))
        self.FREE_TIER_MAX_USERS = int(os.getenv('FREE_TIER_MAX_USERS', '150'))

        # Superuser phones — comma-separated E.164 numbers that bypass all limits
        raw = os.getenv('SUPERUSER_PHONES', '')
        self.SUPERUSER_PHONES = {p.strip() for p in raw.split(',') if p.strip()}

        # Internal cron endpoint auth token
        self.INTERNAL_API_SECRET = os.getenv('INTERNAL_API_SECRET', '')

        # Stripe Configuration (app boots without these — StripeManager validates on use)
        self.STRIPE_SECRET_KEY     = os.getenv('STRIPE_SECRET_KEY', '')
        self.STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
        self.STRIPE_PRICE_PPU      = os.getenv('STRIPE_PRICE_PPU', '')
        self.STRIPE_PRICE_PREMIUM  = os.getenv('STRIPE_PRICE_PREMIUM', '')
        self.STRIPE_PRICE_PLUS     = os.getenv('STRIPE_PRICE_PLUS', '')
        self.STRIPE_SUCCESS_URL    = os.getenv('STRIPE_SUCCESS_URL', '')
        self.STRIPE_CANCEL_URL     = os.getenv('STRIPE_CANCEL_URL', '')

        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # Validate required configuration
        self._validate_config()

    def _validate_config(self):
        """Validate that required configuration is present for the active provider."""
        if self.MESSAGING_PROVIDER == 'twilio':
            required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']
        else:
            required_vars = [
                'WHATSAPP_VERIFY_TOKEN',
                'WHATSAPP_ACCESS_TOKEN',
                'WHATSAPP_PHONE_NUMBER_ID'
            ]

        missing_vars = []
        for var in required_vars:
            value = getattr(self, var)
            if not value or value == 'your_value_here':
                missing_vars.append(var)

        if missing_vars:
            print(f"\n⚠️  WARNING: Missing or invalid configuration for provider '{self.MESSAGING_PROVIDER}':")
            for var in missing_vars:
                print(f"   - {var}")
            print(f"\nPlease update your .env file with valid credentials.")
            print(f"See .env.example for required variables.\n")

    def is_configured(self):
        """
        Check if all required configuration is present for the active provider.

        Returns:
            bool: True if configured, False otherwise
        """
        if self.MESSAGING_PROVIDER == 'twilio':
            return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN)
        return all([
            self.WHATSAPP_VERIFY_TOKEN,
            self.WHATSAPP_ACCESS_TOKEN,
            self.WHATSAPP_PHONE_NUMBER_ID,
            self.WHATSAPP_VERIFY_TOKEN != 'your_verify_token_here',
            self.WHATSAPP_ACCESS_TOKEN != 'your_access_token_here'
        ])

    def get_api_url(self):
        """
        Get the WhatsApp Cloud API URL.

        Returns:
            str: API URL
        """
        return f"https://graph.facebook.com/v18.0/{self.WHATSAPP_PHONE_NUMBER_ID}/messages"

    def __repr__(self):
        """String representation (without sensitive data)."""
        return (
            f"Config("
            f"phone_number_id={'*' * 8 if self.WHATSAPP_PHONE_NUMBER_ID else 'NOT_SET'}, "
            f"port={self.WEBHOOK_PORT}, "
            f"debug={self.DEBUG_MODE}"
            f")"
        )
