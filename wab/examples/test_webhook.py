#!/usr/bin/env python3
"""
Test Webhook
Script to test the webhook server locally by simulating WhatsApp webhook calls.
"""

import sys
import json
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


def test_webhook_verification(base_url="http://localhost:5000"):
    """
    Test webhook verification (GET request).
    This simulates WhatsApp's verification request.
    """
    print("\n" + "=" * 60)
    print("TEST 1: Webhook Verification")
    print("=" * 60)

    # Get verify token from environment
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'your_verify_token_here')

    if verify_token == 'your_verify_token_here':
        print("⚠️  WARNING: WHATSAPP_VERIFY_TOKEN not set in .env file")
        print("   Using placeholder token - this test will fail")
    else:
        print(f"Using verify token from .env: {verify_token[:10]}...")

    # Verification parameters
    params = {
        'hub.mode': 'subscribe',
        'hub.verify_token': verify_token,
        'hub.challenge': 'test_challenge_string_12345'
    }

    try:
        response = requests.get(f"{base_url}/webhook", params=params)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("✅ Verification successful!")
        else:
            print("❌ Verification failed!")
            if verify_token == 'your_verify_token_here':
                print("   → Please set WHATSAPP_VERIFY_TOKEN in your .env file")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_incoming_message(base_url="http://localhost:5000"):
    """
    Test incoming message webhook (POST request).
    This simulates WhatsApp sending a message to your webhook.

    Note: This test will fail signature verification in production mode.
    For local testing without WhatsApp, signature verification is bypassed
    when WHATSAPP_APP_SECRET is not set or is placeholder value.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Incoming Message")
    print("=" * 60)

    # Check if app secret is configured
    app_secret = os.getenv('WHATSAPP_APP_SECRET', 'your_app_secret_here')

    if app_secret == 'your_app_secret_here':
        print("ℹ️  WHATSAPP_APP_SECRET not set - signature verification will be skipped")
        print("   This is OK for local testing without real WhatsApp webhooks")
    else:
        print("⚠️  WHATSAPP_APP_SECRET is set - signature verification is enabled")
        print("   This test may fail because we're not signing the request")
        print("   For testing with real WhatsApp, send actual messages to your number")

    # Load sample payload
    sample_payload_file = Path(__file__).parent / 'sample_payload.json'

    try:
        with open(sample_payload_file, 'r') as f:
            payload = json.load(f)

        print("\nSending sample message payload...")

        response = requests.post(
            f"{base_url}/webhook",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            print("✅ Message received successfully!")
        elif response.status_code == 403:
            print("❌ Message rejected (403 Forbidden)")
            if app_secret != 'your_app_secret_here':
                print("   → Signature verification failed (expected for local testing)")
                print("   → To test locally, temporarily use placeholder value in .env:")
                print("      WHATSAPP_APP_SECRET=your_app_secret_here")
        else:
            print("❌ Message processing failed!")

    except FileNotFoundError:
        print(f"❌ Sample payload file not found: {sample_payload_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_health_check(base_url="http://localhost:5000"):
    """Test health check endpoint."""
    print("\n" + "=" * 60)
    print("TEST 3: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{base_url}/health")

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("✅ Server is healthy!")
        else:
            print("❌ Health check failed!")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(description='Test WhatsApp Webhook Server')
    parser.add_argument('--url', default='http://localhost:5000',
                        help='Base URL of webhook server (default: http://localhost:5000)')
    args = parser.parse_args()

    base_url = args.url.rstrip('/')

    print("\n" + "=" * 60)
    print("WhatsApp Webhook Test Suite")
    print("=" * 60)
    print(f"Testing server at: {base_url}")

    # Run tests
    test_health_check(base_url)
    test_webhook_verification(base_url)
    test_incoming_message(base_url)

    print("\n" + "=" * 60)
    print("Tests Complete")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
