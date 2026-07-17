"""
GDPR Consent Message Templates and Privacy Policy
"""

from .consent_messages import (
    CONSENT_REVOKED,
    DATA_CONTROLLER_INFO,
)

from .privacy_policy_short import (
    PRIVACY_POLICY_SHORT,
    PRIVACY_SUMMARY,
    PRIVACY_KEY_POINTS,
    AEPD_INFO,
    get_privacy_message
)

__all__ = [
    # Consent messages
    'CONSENT_REVOKED',
    'DATA_CONTROLLER_INFO',
    # Privacy policy
    'PRIVACY_POLICY_SHORT',
    'PRIVACY_SUMMARY',
    'PRIVACY_KEY_POINTS',
    'AEPD_INFO',
    'get_privacy_message',
]
