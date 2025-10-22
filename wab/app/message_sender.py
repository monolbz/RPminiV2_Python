#!/usr/bin/env python3
"""
Message Sender
Sends replies back to WhatsApp users via WhatsApp Cloud API.
"""

import requests
from ..utils.logger import setup_logger
from ..utils.conversation_tracker import ConversationTracker
from ..utils.template_manager import TemplateManager
from ..config.config import Config

logger = setup_logger(__name__)
config = Config()
conversation_tracker = ConversationTracker()
template_manager = TemplateManager()


class MessageSender:
    """Sends messages back to WhatsApp users."""

    def __init__(self):
        self.api_url = f"https://graph.facebook.com/v18.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        self.headers = {
            'Authorization': f'Bearer {config.WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }

    def send_reply(self, response_data):
        """
        Send a reply to a WhatsApp user.
        Automatically chooses between free-form or template based on conversation window.

        Args:
            response_data (dict): Response data containing:
                - to_number: Recipient's phone number
                - phone_number_id: WhatsApp Business phone number ID
                - message_text: Message text to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            to_number = response_data.get('to_number')
            message_text = response_data.get('message_text')

            if not to_number or not message_text:
                logger.error("Missing required fields in response_data")
                return False

            # Check if we're within the 24-hour conversation window
            is_within_window = conversation_tracker.is_within_window(to_number)

            if is_within_window:
                # Send free-form message (within 24h window)
                logger.info(f"Sending free-form message to {to_number} (within 24h window)")
                return self.send_freeform_message(to_number, message_text)
            else:
                # Must use template message (outside 24h window)
                logger.info(f"Sending template message to {to_number} (outside 24h window)")
                return self.send_template_message(to_number, 'hello_world')

        except Exception as e:
            logger.error(f"Error sending reply: {e}", exc_info=True)
            return False

    def send_freeform_message(self, to_number, message_text):
        """
        Send a free-form text message (only works within 24h window).

        Args:
            to_number (str): Recipient's phone number
            message_text (str): Message text to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Prepare message payload
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

            # Send request to WhatsApp Cloud API
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            # Check response
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')
                logger.info(f"Message sent successfully to {to_number} (ID: {message_id})")
                return True
            else:
                logger.error(f"Failed to send message. Status: {response.status_code}, Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending message: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending free-form message: {e}", exc_info=True)
            return False

    def send_template_message(self, to_number, template_name, variables=None):
        """
        Send a pre-approved template message (works anytime).

        Args:
            to_number (str): Recipient's phone number
            template_name (str): Name of the approved template
            variables (list, optional): List of variable values for template placeholders

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Get template configuration
            template_config = template_manager.get_template(template_name)

            if not template_config:
                logger.error(f"Template '{template_name}' not found")
                return False

            # Prepare template payload
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": template_config.get('language', 'en')
                    }
                }
            }

            # Add template variables if provided
            if variables and len(variables) > 0:
                payload["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(var)} for var in variables
                        ]
                    }
                ]

            # Send request to WhatsApp Cloud API
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            # Check response
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')
                logger.info(f"Template message sent successfully to {to_number} (ID: {message_id})")

                # Update conversation tracker - we've initiated contact
                conversation_tracker.update_conversation(to_number)
                return True
            else:
                logger.error(f"Failed to send template. Status: {response.status_code}, Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending template: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending template message: {e}", exc_info=True)
            return False

    def send_message_with_link(self, to_number, message_text, url):
        """
        Send a message with a clickable link (for sharing Google Maps URLs).

        Args:
            to_number (str): Recipient's phone number
            message_text (str): Message text
            url (str): URL to include (will be auto-detected as link)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # WhatsApp auto-detects URLs in text, so we just need to enable preview
            full_message = f"{message_text}\n\n{url}"

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {
                    "preview_url": True,  # Enable link preview
                    "body": full_message
                }
            }

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Message with link sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Failed to send message with link. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending message with link: {e}", exc_info=True)
            return False
