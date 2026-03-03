"""
Meta WhatsApp Cloud API Provider Adapter

Handles webhook verification, incoming payload parsing, and outgoing message
sending for the Meta (Facebook) WhatsApp Cloud API.
"""

import requests
from ..utils.validators import verify_webhook_signature
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class MetaAdapter:
    """
    Provider adapter for Meta WhatsApp Cloud API.

    Webhook format  : JSON (application/json)
    Verification    : GET with hub.mode / hub.verify_token / hub.challenge
    Signature       : X-Hub-Signature-256 (HMAC-SHA256)
    Outgoing auth   : Bearer token
    Outgoing URL    : https://graph.facebook.com/v18.0/{phone_number_id}/messages
    """

    def __init__(self):
        # Import lazily to avoid circular imports at module load
        from ..config.config import Config
        self.config = Config()

    # ------------------------------------------------------------------
    # Webhook verification (GET)
    # ------------------------------------------------------------------

    def verify_get(self, request):
        """
        Validate Meta's GET webhook verification challenge.

        Args:
            request: Flask request object

        Returns:
            tuple: (response_body, status_code)
        """
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == self.config.WHATSAPP_VERIFY_TOKEN:
            logger.info("[Meta] Webhook GET verification successful")
            return challenge, 200

        logger.warning("[Meta] Webhook GET verification failed - invalid token or mode")
        return 'Forbidden', 403

    # ------------------------------------------------------------------
    # Incoming POST signature validation
    # ------------------------------------------------------------------

    def verify_post_signature(self, request):
        """
        Validate the X-Hub-Signature-256 header on an incoming POST.

        Args:
            request: Flask request object

        Returns:
            bool: True if valid

        Raises:
            ValueError: if WHATSAPP_APP_SECRET is not configured
        """
        signature = request.headers.get('X-Hub-Signature-256', '')
        return verify_webhook_signature(
            request.get_data(), signature, self.config.WHATSAPP_APP_SECRET
        )

    # ------------------------------------------------------------------
    # Incoming payload parsing
    # ------------------------------------------------------------------

    def parse_incoming(self, request):
        """
        Parse incoming Meta webhook POST body.

        Normalises the sender phone number to +NUMBER format (E.164).

        Args:
            request: Flask request object

        Returns:
            list of (message_dict, value_dict) tuples, one per message.
            Empty list if no messages found or wrong object type.
        """
        body = request.get_json()
        if not body:
            return []

        results = []
        if body.get('object') != 'whatsapp_business_account':
            return []

        for entry in body.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') == 'messages':
                    value = change.get('value', {})
                    for message in value.get('messages', []):
                        # Normalise phone to +NUMBER (Meta sends without +)
                        raw_from = message.get('from', '')
                        if raw_from and not raw_from.startswith('+'):
                            message = dict(message)
                            message['from'] = '+' + raw_from
                        results.append((message, value))

        return results

    def parse_status_updates(self, request):
        """
        Extract message status updates from a Meta POST body.

        Args:
            request: Flask request object

        Returns:
            list of status dicts
        """
        body = request.get_json()
        if not body:
            return []

        statuses = []
        if body.get('object') == 'whatsapp_business_account':
            for entry in body.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        statuses.extend(value.get('statuses', []))
        return statuses

    # ------------------------------------------------------------------
    # Outgoing messages
    # ------------------------------------------------------------------

    def send(self, to_number, message_text):
        """
        Send a free-form text message via Meta Cloud API.

        Args:
            to_number (str): Recipient phone in +NUMBER format
            message_text (str): Text to send

        Returns:
            bool: True if sent successfully
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message_text
                }
            }
            response = requests.post(
                self.config.get_api_url(),
                headers={
                    'Authorization': f'Bearer {self.config.WHATSAPP_ACCESS_TOKEN}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                message_id = response.json().get('messages', [{}])[0].get('id')
                logger.info(f"[Meta] Message sent to {to_number} (ID: {message_id})")
                return True
            else:
                logger.error(
                    f"[Meta] Send failed. Status: {response.status_code}, "
                    f"Body: {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"[Meta] Request error: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"[Meta] Error sending message: {e}", exc_info=True)
            return False
