#!/usr/bin/env python3
"""
WhatsApp Webhook Server - Entry Point
Main script to start the WhatsApp webhook server.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from wab.app.webhook_server import run_server
from wab.config.config import Config
from wab.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function to start the webhook server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='WhatsApp Business Webhook Server')
    parser.add_argument('--host', default=None, help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None, help='Port to listen on (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Load configuration
    config = Config()

    # Check if configuration is valid
    if not config.is_configured():
        logger.error("WhatsApp webhook is not properly configured!")
        logger.error("Please update your .env file with valid WhatsApp credentials.")
        logger.error("See .env.example for required configuration.")
        sys.exit(1)

    # Get server settings
    host = args.host or config.WEBHOOK_HOST
    port = args.port or config.WEBHOOK_PORT
    debug = args.debug or config.DEBUG_MODE

    # Display startup information
    print("\n" + "=" * 60)
    print("WhatsApp Business Webhook Server")
    print("=" * 60)
    print(f"Server starting on {host}:{port}")
    print(f"Debug mode: {'ON' if debug else 'OFF'}")
    print(f"Phone Number ID: ...{config.WHATSAPP_PHONE_NUMBER_ID[-8:] if config.WHATSAPP_PHONE_NUMBER_ID else 'NOT_SET'}")
    print("=" * 60)
    print()
    print("Webhook endpoints:")
    print(f"  GET  http://{host}:{port}/webhook  (verification)")
    print(f"  POST http://{host}:{port}/webhook  (receive messages)")
    print(f"  GET  http://{host}:{port}/health   (health check)")
    print()
    print("For local testing with ngrok:")
    print(f"  1. Run: ngrok http {port}")
    print(f"  2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
    print(f"  3. Set webhook URL in Meta Developer Portal: <ngrok_url>/webhook")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()

    try:
        # Start the server
        run_server(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
