"""
Messaging Provider Factory

Returns the active adapter based on the MESSAGING_PROVIDER environment variable.

Supported values:
  - 'meta'    (default) : WhatsApp Cloud API via Meta
  - 'twilio'            : WhatsApp Sandbox via Twilio

Switch between providers by changing MESSAGING_PROVIDER in .env.
No code changes required.
"""

import os


def get_provider():
    """
    Return the active messaging provider adapter.

    Returns:
        MetaAdapter or TwilioAdapter instance
    """
    provider = os.getenv('MESSAGING_PROVIDER', 'meta').lower()
    if provider == 'twilio':
        from .twilio_adapter import TwilioAdapter
        return TwilioAdapter()
    from .meta_adapter import MetaAdapter
    return MetaAdapter()
