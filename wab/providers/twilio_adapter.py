"""
Twilio WhatsApp Sandbox Provider Adapter

Handles webhook verification, incoming payload parsing, and outgoing message
sending for the Twilio WhatsApp Sandbox.

Key differences from Meta:
  - Webhook is form-encoded POST (not JSON)
  - No GET challenge verification
  - Signature uses X-Twilio-Signature (HMAC-SHA1 via Twilio SDK)
  - No 24-hour conversation window — free-form messages always allowed in sandbox
  - Sender number format: 'whatsapp:+NUMBER'
"""

import time
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TwilioAdapter:
    """
    Provider adapter for Twilio WhatsApp Sandbox.

    Webhook format  : Form POST (application/x-www-form-urlencoded)
    Verification    : No GET challenge — Twilio verifies every POST via signature
    Signature       : X-Twilio-Signature (HMAC-SHA1)
    Outgoing auth   : HTTP Basic (Account SID + Auth Token)
    Outgoing SDK    : twilio.rest.Client
    """

    def __init__(self):
        from ..config.config import Config
        self.config = Config()
        self.client = Client(self.config.TWILIO_ACCOUNT_SID, self.config.TWILIO_AUTH_TOKEN)
        self.validator = RequestValidator(self.config.TWILIO_AUTH_TOKEN)

    # ------------------------------------------------------------------
    # Webhook verification (GET)
    # ------------------------------------------------------------------

    def verify_get(self, request):
        """
        Twilio does not use a GET challenge. Return 200 OK.

        Args:
            request: Flask request object

        Returns:
            tuple: ('OK', 200)
        """
        return 'OK', 200

    # ------------------------------------------------------------------
    # Incoming POST signature validation
    # ------------------------------------------------------------------

    def verify_post_signature(self, request):
        """
        Validate the X-Twilio-Signature header on an incoming POST.

        Uses the full public URL (reconstructed from forwarded headers so this
        works correctly behind ngrok and Railway proxies via ProxyFix).

        Args:
            request: Flask request object

        Returns:
            bool: True if signature is valid
        """
        signature = request.headers.get('X-Twilio-Signature', '')
        if not signature:
            logger.warning("[Twilio] No X-Twilio-Signature header present")
            return False

        # request.url is correct when ProxyFix middleware is active
        url = request.url
        params = request.form.to_dict()

        is_valid = self.validator.validate(url, params, signature)
        if not is_valid:
            logger.warning(f"[Twilio] Invalid webhook signature for URL: {url}")
        return is_valid

    # ------------------------------------------------------------------
    # Incoming payload parsing
    # ------------------------------------------------------------------

    def parse_incoming(self, request):
        """
        Parse incoming Twilio WhatsApp Sandbox form POST.

        Constructs Meta-compatible (message_dict, value_dict) tuples so that
        message_processor.py requires no changes.

        Twilio form fields used:
          From        : 'whatsapp:+34644252886'
          Body        : message text
          MessageSid  : unique message ID
          ProfileName : sender's WhatsApp display name

        Args:
            request: Flask request object

        Returns:
            list of (message_dict, value_dict) tuples.
            Empty list if not a WhatsApp message.
        """
        form = request.form

        raw_from = form.get('From', '')
        if not raw_from.startswith('whatsapp:'):
            logger.debug(f"[Twilio] Ignoring non-WhatsApp message from: {raw_from}")
            return []

        # Normalise From field: 'whatsapp:+34612345678' → '+34612345678'
        #                       'whatsapp:BR.1A2B3C...' → 'BR.1A2B3C...' (BSUID-only user)
        raw_identifier = raw_from.replace('whatsapp:', '')

        # ExternalUserId is present when the sender has a WhatsApp username (phone or BSUID-only)
        bsuid_field = form.get('ExternalUserId') or None

        # Determine phone vs BSUID-only user
        stripped = raw_identifier.lstrip('+')
        if stripped.isdigit():
            from_phone = raw_identifier
            from_bsuid = bsuid_field      # may be None (no username) or a BSUID string
        else:
            from_phone = None             # BSUID-only user — no phone shared
            from_bsuid = raw_identifier   # From field itself IS the BSUID

        # Unified routing identifier: phone if available, BSUID otherwise
        identifier = from_phone if from_phone else from_bsuid

        if not identifier:
            logger.warning("[Twilio] Could not determine user identifier — message dropped")
            return []

        # Build a Meta-compatible message dict.
        # NumMedia > 0 means the user sent an image/document — map to 'image' type
        # so message_processor.py returns the correct "not supported" placeholder.
        num_media = int(form.get('NumMedia', 0))
        msg_type = 'image' if num_media > 0 else 'text'
        message = {
            'id': form.get('MessageSid', ''),
            'from': identifier,       # phone OR BSUID string — unified identifier
            'from_phone': from_phone, # None for BSUID-only users
            'bsuid': from_bsuid,      # None when user has no username
            'timestamp': str(int(time.time())),
            'type': msg_type,
            'text': {'body': form.get('Body', '')},
        }

        # Build a Meta-compatible value dict (metadata + contacts)
        value = {
            'metadata': {
                'phone_number_id': self.config.TWILIO_WHATSAPP_NUMBER
            },
            'contacts': [{
                'profile': {'name': form.get('ProfileName', '')}
            }]
        }

        logger.info(f"[Twilio] Parsed incoming message from {identifier}")
        return [(message, value)]

    def parse_status_updates(self, request):
        """
        Twilio sends status callbacks to a separate URL, not here.

        Returns:
            list: always empty
        """
        return []

    # ------------------------------------------------------------------
    # Outgoing messages
    # ------------------------------------------------------------------

    def send(self, to_number, message_text):
        """
        Send a WhatsApp message via Twilio.

        Args:
            to_number (str): Recipient phone in +NUMBER format (e.g. '+34644252886')
            message_text (str): Text to send

        Returns:
            bool: True if sent successfully
        """
        try:
            # Twilio requires 'whatsapp:+NUMBER' format for both from and to
            to_formatted = f'whatsapp:{to_number}'

            message = self.client.messages.create(
                from_=self.config.TWILIO_WHATSAPP_NUMBER,
                to=to_formatted,
                body=message_text
            )

            logger.info(f"[Twilio] Message sent to {to_number} (SID: {message.sid})")
            return True

        except Exception as e:
            logger.error(f"[Twilio] Error sending message to {to_number}: {e}", exc_info=True)
            return False
