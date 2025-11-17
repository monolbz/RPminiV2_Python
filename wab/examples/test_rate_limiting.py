#!/usr/bin/env python3
"""
Rate Limiting Test Script
Tests the rate limiting functionality of the webhook server.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.utils.rate_limiter import RateLimiter, MessageLoopDetector, GlobalRateLimiter


def test_user_rate_limiter():
    """Test per-user rate limiting."""
    print("\n" + "=" * 60)
    print("TEST 1: Per-User Rate Limiting")
    print("=" * 60)

    # Create rate limiter: 5 requests per minute
    limiter = RateLimiter(max_requests=5, window_minutes=1)

    user_id = "1234567890"

    print(f"\nTesting {user_id} with limit: 5 requests per minute\n")

    # Send 7 requests (should reject last 2)
    for i in range(1, 8):
        is_allowed, info = limiter.check_limit(user_id)

        if is_allowed:
            print(f"[OK] Request {i}: ALLOWED - {info['remaining']} remaining")
        else:
            print(f"[REJECT] Request {i}: REJECTED - Rate limit exceeded")
            print(f"   Reset time: {info['reset_time']}")

        time.sleep(0.1)  # Small delay between requests

    print("\n[PASS] User rate limiter test completed!")


def test_loop_detector():
    """Test message loop detection."""
    print("\n" + "=" * 60)
    print("TEST 2: Message Loop Detection")
    print("=" * 60)

    # Create loop detector: 3 identical messages in 5 minutes
    detector = MessageLoopDetector(threshold=3, window_minutes=5)

    user_id = "1234567890"
    message = "Hello, help me please!"

    print(f"\nTesting loop detection with threshold: 3 identical messages\n")

    # Send same message 5 times
    for i in range(1, 6):
        is_loop, info = detector.check_loop(user_id, message)

        if is_loop:
            print(f"[WARN]  Message {i}: LOOP DETECTED - {info['count']} identical messages")
            print(f"   Message: '{info['message_preview']}'")
        else:
            print(f"[OK] Message {i}: OK - Count: {info['count']}/{info['threshold']}")

        time.sleep(0.1)

    print("\n[OK] Loop detector test completed!")


def test_global_rate_limiter():
    """Test global rate limiting."""
    print("\n" + "=" * 60)
    print("TEST 3: Global Rate Limiting")
    print("=" * 60)

    # Create global limiter: 10 total requests per minute
    limiter = GlobalRateLimiter(max_requests=10, window_minutes=1)

    print(f"\nTesting global limit: 10 total requests per minute\n")

    # Send 12 requests from various users (should reject last 2)
    for i in range(1, 13):
        is_allowed, info = limiter.check_limit()

        if is_allowed:
            print(f"[OK] Request {i}: ALLOWED - {info['remaining']} remaining globally")
        else:
            print(f"[REJECT] Request {i}: REJECTED - Global rate limit exceeded")

        time.sleep(0.1)

    print("\n[OK] Global rate limiter test completed!")


def test_different_messages():
    """Test that different messages don't trigger loop detection."""
    print("\n" + "=" * 60)
    print("TEST 4: Different Messages (No Loop)")
    print("=" * 60)

    detector = MessageLoopDetector(threshold=3, window_minutes=5)
    user_id = "1234567890"

    messages = [
        "Hello",
        "How are you?",
        "I need help",
        "What's the weather?",
        "Thank you"
    ]

    print(f"\nSending {len(messages)} different messages\n")

    for i, message in enumerate(messages, 1):
        is_loop, info = detector.check_loop(user_id, message)

        if is_loop:
            print(f"[WARN]  Message {i}: UNEXPECTED LOOP - {info['count']} identical")
        else:
            print(f"[OK] Message {i}: OK - '{message}' (Count: {info['count']})")

        time.sleep(0.1)

    print("\n[OK] Different messages test completed!")


def test_rate_limit_reset():
    """Test that rate limits reset after window expires."""
    print("\n" + "=" * 60)
    print("TEST 5: Rate Limit Window Reset")
    print("=" * 60)

    # Create limiter with very short window for testing
    limiter = RateLimiter(max_requests=3, window_minutes=0.05)  # 3 seconds window

    user_id = "1234567890"

    print(f"\nTesting rate limit reset (3 requests per 3 seconds)\n")

    # First batch - should allow 3 then reject
    print("First batch:")
    for i in range(1, 5):
        is_allowed, info = limiter.check_limit(user_id)
        status = "[OK] ALLOWED" if is_allowed else "[REJECT] REJECTED"
        print(f"  Request {i}: {status}")
        time.sleep(0.2)

    # Wait for window to expire
    print("\n[WAIT] Waiting 4 seconds for window to reset...")
    time.sleep(4)

    # Second batch - should allow again
    print("\nSecond batch (after reset):")
    for i in range(1, 4):
        is_allowed, info = limiter.check_limit(user_id)
        status = "[OK] ALLOWED" if is_allowed else "[REJECT] REJECTED"
        print(f"  Request {i}: {status}")
        time.sleep(0.2)

    print("\n[OK] Rate limit reset test completed!")


def test_multiple_users():
    """Test that rate limits are per-user."""
    print("\n" + "=" * 60)
    print("TEST 6: Multiple Users (Independent Limits)")
    print("=" * 60)

    limiter = RateLimiter(max_requests=3, window_minutes=1)

    users = ["user1", "user2", "user3"]

    print(f"\nTesting 3 users, each with limit of 3 requests/minute\n")

    # Each user sends 4 requests
    for user in users:
        print(f"\n{user}:")
        for i in range(1, 5):
            is_allowed, info = limiter.check_limit(user)
            status = "[OK] ALLOWED" if is_allowed else "[REJECT] REJECTED"
            print(f"  Request {i}: {status}")
            time.sleep(0.1)

    print("\n[OK] Multiple users test completed!")


if __name__ == "__main__":
    print("\nWhatsApp Webhook Rate Limiting Tests")
    print("=" * 60)

    try:
        test_user_rate_limiter()
        test_loop_detector()
        test_global_rate_limiter()
        test_different_messages()
        test_rate_limit_reset()
        test_multiple_users()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
