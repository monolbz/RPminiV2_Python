#!/usr/bin/env python3
"""
WhatsApp Webhook Server
Main Flask application for receiving and handling WhatsApp webhook events.
"""

import os
import threading
import time
from flask import Flask, request, jsonify
from ..utils.logger import setup_logger
from ..utils.validators import verify_webhook_signature
from ..utils.rate_limiter import RateLimiter, MessageLoopDetector, GlobalRateLimiter
from ..config.config import Config
from .message_processor import MessageProcessor
from .message_sender import MessageSender

# Initialize Flask app
app = Flask(__name__)
config = Config()
logger = setup_logger(__name__)

# Initialize message processor and sender
message_processor = MessageProcessor()
message_sender = MessageSender()

# Initialize rate limiters
# Per-user: 10 messages per minute
user_rate_limiter = RateLimiter(max_requests=10, window_minutes=1)

# Loop detection: 3 identical messages in 5 minutes
loop_detector = MessageLoopDetector(threshold=3, window_minutes=5)

# Global: 500 messages per hour (across all users)
global_rate_limiter = GlobalRateLimiter(max_requests=500, window_minutes=60)


def cleanup_rate_limiters():
    """
    Background task to periodically clean up old rate limiter entries.
    Runs every hour to prevent memory bloat.
    """
    while True:
        try:
            time.sleep(3600)  # Sleep for 1 hour
            logger.info("Running rate limiter cleanup...")
            user_rate_limiter.cleanup_old_entries(max_age_hours=24)
            loop_detector.cleanup_old_entries(max_age_hours=24)
            logger.info("Rate limiter cleanup completed")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_rate_limiters, daemon=True)
cleanup_thread.start()
logger.info("Rate limiter cleanup thread started")


@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Webhook verification endpoint for WhatsApp.
    WhatsApp will send a GET request with verification parameters.
    """
    try:
        # Get verification parameters from query string
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        logger.info(f"Webhook verification attempt - Mode: {mode}")

        # Check if verification parameters are present
        if mode and token:
            # Verify the mode is 'subscribe' and token matches
            if mode == 'subscribe' and token == config.WHATSAPP_VERIFY_TOKEN:
                logger.info("Webhook verified successfully")
                # Respond with the challenge to complete verification
                return challenge, 200
            else:
                logger.warning(f"Webhook verification failed - Invalid token")
                return 'Forbidden', 403
        else:
            logger.warning("Webhook verification failed - Missing parameters")
            return 'Bad Request', 400

    except Exception as e:
        logger.error(f"Error during webhook verification: {e}")
        return 'Internal Server Error', 500


@app.route('/webhook', methods=['POST'])
def webhook_receive():
    """
    Webhook receiver endpoint for WhatsApp messages.
    Receives POST requests with message data from WhatsApp.
    """
    try:
        # Check global rate limit first (protect server resources)
        is_allowed, global_info = global_rate_limiter.check_limit()
        if not is_allowed:
            logger.error(f"Global rate limit exceeded: {global_info['current']}/{global_info['limit']} requests")
            return jsonify({
                'status': 'error',
                'message': 'Service temporarily unavailable - too many requests'
            }), 429

        # Get request body
        body = request.get_json()

        # Log incoming webhook (without sensitive data)
        logger.info(f"Webhook received - Entry count: {len(body.get('entry', []))}")

        # Verify webhook signature for security
        signature = request.headers.get('X-Hub-Signature-256', '')
        try:
            if not verify_webhook_signature(request.get_data(), signature, config.WHATSAPP_APP_SECRET):
                logger.warning("Invalid webhook signature")
                return jsonify({'status': 'error', 'message': 'Invalid signature'}), 403
        except ValueError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return jsonify({'status': 'error', 'message': 'Signature verification required'}), 403

        # Process webhook entries
        if body.get('object') == 'whatsapp_business_account':
            for entry in body.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        # Extract message data
                        value = change.get('value', {})

                        # Process incoming messages
                        if 'messages' in value:
                            for message in value['messages']:
                                process_incoming_message(message, value)

                        # Process message status updates (delivered, read, etc.)
                        if 'statuses' in value:
                            for status in value['statuses']:
                                process_status_update(status)

            # Return success response
            return jsonify({'status': 'success'}), 200
        else:
            logger.warning(f"Unknown webhook object type: {body.get('object')}")
            return jsonify({'status': 'error', 'message': 'Unknown object type'}), 400

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


def process_incoming_message(message, value):
    """
    Process an incoming WhatsApp message.

    Args:
        message (dict): Message data from webhook
        value (dict): Additional value data containing metadata
    """
    try:
        # Extract message details
        message_id = message.get('id')
        from_number = message.get('from')
        timestamp = message.get('timestamp')
        message_type = message.get('type')

        logger.info(f"Processing message {message_id} from {from_number} (type: {message_type})")

        # Check per-user rate limit
        is_allowed, rate_info = user_rate_limiter.check_limit(from_number)
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {from_number}: "
                f"{rate_info['current']}/{rate_info['limit']} messages. "
                f"Resets at {rate_info['reset_time']}"
            )
            # Optionally send a rate limit message to user (uncomment if desired)
            # message_sender.send_text_message(
            #     from_number,
            #     "You're sending messages too quickly. Please wait a moment and try again."
            # )
            return

        # Check for message loops (only for text messages)
        if message_type == 'text':
            message_text = message.get('text', {}).get('body', '')

            is_loop, loop_info = loop_detector.check_loop(from_number, message_text)
            if is_loop:
                logger.warning(
                    f"Message loop detected for {from_number}: "
                    f"'{loop_info['message_preview']}' sent {loop_info['count']} times"
                )
                # Optionally send loop warning to user (uncomment if desired)
                # message_sender.send_text_message(
                #     from_number,
                #     "It looks like you're repeating the same message. "
                #     "If you need assistance, please try asking in a different way."
                # )
                return

        # Process the message using MessageProcessor
        processed_data = message_processor.process_message(message, value)

        if processed_data:
            # Send reply using MessageSender
            message_sender.send_reply(processed_data)
        else:
            logger.warning(f"Message {message_id} could not be processed")

    except Exception as e:
        logger.error(f"Error processing incoming message: {e}", exc_info=True)


def process_status_update(status):
    """
    Process message status updates (delivered, read, failed, etc.).

    Args:
        status (dict): Status update data
    """
    try:
        message_id = status.get('id')
        status_type = status.get('status')
        recipient = status.get('recipient_id')

        logger.info(f"Status update for message {message_id}: {status_type} (recipient: {recipient})")

        # You can add logic here to track message delivery status
        # For now, we just log it

    except Exception as e:
        logger.error(f"Error processing status update: {e}", exc_info=True)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running."""
    return jsonify({
        'status': 'healthy',
        'service': 'WhatsApp Webhook Server',
        'version': '1.0.0',
        'rate_limiting': {
            'user_limit': f"{user_rate_limiter.max_requests} per {user_rate_limiter.window.total_seconds() / 60} min",
            'global_limit': f"{global_rate_limiter.max_requests} per {global_rate_limiter.window.total_seconds() / 60} min",
            'loop_detection': f"{loop_detector.threshold} identical messages in {loop_detector.window.total_seconds() / 60} min"
        }
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with basic information."""
    return jsonify({
        'service': 'WhatsApp Business Webhook Server',
        'version': '1.0.0',
        'endpoints': {
            'webhook_verify': 'GET /webhook',
            'webhook_receive': 'POST /webhook',
            'health': 'GET /health'
        }
    }), 200


def run_server(host='0.0.0.0', port=5000, debug=False):
    """
    Run the Flask webhook server.

    Args:
        host (str): Host to bind to
        port (int): Port to listen on
        debug (bool): Enable debug mode
    """
    logger.info(f"Starting WhatsApp Webhook Server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('WEBHOOK_PORT', 5000))
    run_server(port=port, debug=True)
