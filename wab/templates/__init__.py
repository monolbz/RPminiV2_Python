"""
GDPR Consent Message Templates and Privacy Policy
"""

from .consent_messages import (
    CONSENT_REQUEST,
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_REVOKED,
    CONSENT_ALREADY_GIVEN,
    CONSENT_REQUIRED_FOR_ROUTE,
    PENDING_CONSENT_RESPONSE,
    DATA_CONTROLLER_INFO,
    get_consent_keywords
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
    'CONSENT_REQUEST',
    'CONSENT_ACCEPTED',
    'CONSENT_DECLINED',
    'CONSENT_REVOKED',
    'CONSENT_ALREADY_GIVEN',
    'CONSENT_REQUIRED_FOR_ROUTE',
    'PENDING_CONSENT_RESPONSE',
    'DATA_CONTROLLER_INFO',
    'get_consent_keywords',
    # Privacy policy
    'PRIVACY_POLICY_SHORT',
    'PRIVACY_SUMMARY',
    'PRIVACY_KEY_POINTS',
    'AEPD_INFO',
    'get_privacy_message',
]
