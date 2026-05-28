#!/usr/bin/env python3
"""
WhatsApp Webhook Server
Main Flask application for receiving and handling WhatsApp webhook events.
"""

import os
import threading
import time
from functools import wraps
from flask import Flask, request, jsonify, make_response
from werkzeug.middleware.proxy_fix import ProxyFix
from ..utils.logger import setup_logger
from ..utils.rate_limiter import RateLimiter, MessageLoopDetector, GlobalRateLimiter
from ..config.config import Config
from ..providers import get_provider
from .message_processor import MessageProcessor
from .message_sender import MessageSender
from .feedback_manager import feedback_manager
from .stripe_manager import StripeManager

# Initialize Flask app
app = Flask(__name__)
# Trust X-Forwarded-Proto and X-Forwarded-Host from reverse proxies (ngrok, Railway).
# Required for correct Twilio signature validation behind a proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
config = Config()
provider = get_provider()
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
    Webhook verification endpoint.
    Meta sends a GET challenge; Twilio does not use GET verification.
    Delegated entirely to the active provider adapter.
    """
    try:
        logger.info(f"Webhook GET verification attempt [{config.MESSAGING_PROVIDER}]")
        response_body, status_code = provider.verify_get(request)
        return response_body, status_code
    except Exception as e:
        logger.error(f"Error during webhook verification: {e}")
        return 'Internal Server Error', 500


@app.route('/webhook', methods=['POST'])
def webhook_receive():
    """
    Webhook receiver endpoint for incoming messages.
    Signature verification and payload parsing delegated to the active provider adapter.
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

        # Verify webhook signature for security
        try:
            if not provider.verify_post_signature(request):
                logger.warning(f"[{config.MESSAGING_PROVIDER}] Invalid webhook signature")
                return jsonify({'status': 'error', 'message': 'Invalid signature'}), 403
        except ValueError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return jsonify({'status': 'error', 'message': 'Signature verification required'}), 403

        # Parse incoming messages via provider adapter.
        # Each message is processed in a background thread so the 200 response
        # is returned immediately (required by Twilio's 15-second webhook timeout).
        messages = provider.parse_incoming(request)
        for message, value in messages:
            t = threading.Thread(target=process_incoming_message, args=(message, value), daemon=True)
            t.start()

        # Parse and log status updates
        for status in provider.parse_status_updates(request):
            process_status_update(status)

        return jsonify({'status': 'success'}), 200

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


def _require_internal_token(f):
    """Decorator: require Authorization: Bearer <INTERNAL_API_SECRET> header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = config.INTERNAL_API_SECRET
        if not secret:
            logger.error("INTERNAL_API_SECRET not configured — rejecting internal request")
            return jsonify({'status': 'error', 'message': 'Internal auth not configured'}), 500
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'status': 'error', 'message': 'Missing Authorization header'}), 401
        token = auth_header[len('Bearer '):]
        if token != secret:
            logger.warning("Internal cron request with wrong token")
            return jsonify({'status': 'error', 'message': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


@app.route('/internal/cron/send-feedback', methods=['POST'])
@_require_internal_token
def cron_send_feedback():
    """
    Internal cron endpoint — triggered daily at 08:00 UTC by cron-job.org.
    Finds eligible users and sends (or queues) the NPS survey Q1.
    """
    logger.info("Cron: send-feedback triggered")
    eligible = feedback_manager.find_eligible_users()
    sent = 0
    pending = 0
    errors = 0

    for phone in eligible:
        try:
            created = feedback_manager.create_pending_survey(phone)
            if not created:
                errors += 1
                continue
            delivered = feedback_manager.send_q1(phone, message_sender)
            if delivered:
                sent += 1
            else:
                pending += 1
        except Exception as e:
            logger.error(f"Cron: error processing {phone}: {e}", exc_info=True)
            errors += 1

    logger.info(f"Cron send-feedback: eligible={len(eligible)}, sent={sent}, pending={pending}, errors={errors}")
    return jsonify({
        'status': 'ok',
        'eligible': len(eligible),
        'sent': sent,
        'pending': pending,
        'errors': errors,
    }), 200


@app.route('/internal/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """
    Stripe webhook endpoint.
    Auth is via Stripe-Signature header (STRIPE_WEBHOOK_SECRET).
    Raw bytes required for signature verification — do NOT parse JSON first.
    """
    payload = request.get_data()  # raw bytes — critical for sig verification
    sig_header = request.headers.get('Stripe-Signature', '')

    if not sig_header:
        logger.warning("Stripe webhook received without Stripe-Signature header")
        return jsonify({'status': 'error', 'message': 'Missing signature'}), 400

    try:
        stripe_mgr = StripeManager()
    except RuntimeError as e:
        logger.error(f"Stripe not configured: {e}")
        return jsonify({'status': 'error', 'message': 'Stripe not configured'}), 500

    success, message = stripe_mgr.handle_webhook_event(payload, sig_header)

    if not success:
        if message == 'invalid_signature':
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        logger.error(f"Stripe webhook error: {message}")
        return jsonify({'status': 'error', 'message': message}), 400

    return jsonify({'status': 'ok'}), 200


@app.route('/payment/success', methods=['GET'])
def payment_success():
    """Stripe redirects here after successful checkout."""
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Pago completado</title>"
        "<style>body{font-family:sans-serif;text-align:center;padding:60px 20px;color:#1a1a2e;}"
        "h1{font-size:2.5em;margin-bottom:10px;} p{font-size:1.1em;color:#555;}</style></head>"
        "<body><h1>✅ Pago completado</h1>"
        "<p>Tu plan ha sido activado. Vuelve a WhatsApp para continuar.</p></body></html>"
    )
    return make_response(html, 200)


@app.route('/payment/cancel', methods=['GET'])
def payment_cancel():
    """Stripe redirects here if user cancels checkout."""
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Pago cancelado</title>"
        "<style>body{font-family:sans-serif;text-align:center;padding:60px 20px;color:#1a1a2e;}"
        "h1{font-size:2.5em;margin-bottom:10px;} p{font-size:1.1em;color:#555;}</style></head>"
        "<body><h1>❌ Pago cancelado</h1>"
        "<p>No se ha realizado ningún cargo. Vuelve a WhatsApp cuando quieras.</p></body></html>"
    )
    return make_response(html, 200)


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
