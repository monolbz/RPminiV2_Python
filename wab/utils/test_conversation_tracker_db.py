#!/usr/bin/env python3
"""
Test script for database-backed ConversationTracker.

Verifies that the database version maintains API compatibility
with the JSON version while providing database benefits.
"""

import sys
from pathlib import Path
from time import sleep

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.utils.conversation_tracker_db import ConversationTracker


def test_session_lifecycle():
    """Test complete session lifecycle."""
    print("\n" + "="*60)
    print("TEST: Session Lifecycle")
    print("="*60)

    tracker = ConversationTracker(window_hours=24)
    test_phone = '+34700000001'

    # Test 1: Check initial state (should have no session)
    print("\n1. Checking initial state...")
    is_active = tracker.is_within_window(test_phone)
    print(f"   Is within window: {is_active}")
    assert is_active == False, "New user should not have active session"
    print("   PASS: New user has no active session")

    # Test 2: Update conversation
    print("\n2. Updating conversation...")
    tracker.update_conversation(test_phone)
    print("   PASS: Conversation updated")

    # Test 3: Check session is now active
    print("\n3. Checking session after update...")
    is_active = tracker.is_within_window(test_phone)
    print(f"   Is within window: {is_active}")
    assert is_active == True, "User should have active session after update"
    print("   PASS: Session is now active")

    # Test 4: Get remaining time
    print("\n4. Getting remaining time...")
    remaining = tracker.get_remaining_time(test_phone)
    print(f"   Remaining time: {remaining}")
    assert remaining is not None, "Remaining time should exist"
    assert remaining.total_seconds() > 0, "Remaining time should be positive"
    print("   PASS: Remaining time retrieved")

    # Test 5: Get session info
    print("\n5. Getting session info...")
    info = tracker.get_session_info(test_phone)
    print(f"   Session info:")
    print(f"     - Phone: {info['phone_number']}")
    print(f"     - Active: {info['is_active']}")
    print(f"     - Remaining: {info['remaining_time']}")
    assert info is not None, "Session info should exist"
    assert info['is_active'] == True, "Session should be active"
    print("   PASS: Session info retrieved")

    # Test 6: Update conversation again
    print("\n6. Updating conversation again...")
    tracker.update_conversation(test_phone)
    print("   PASS: Conversation updated again")

    # Test 7: Verify still active
    print("\n7. Verifying still active...")
    is_active = tracker.is_within_window(test_phone)
    print(f"   Is within window: {is_active}")
    assert is_active == True, "Session should still be active"
    print("   PASS: Session still active")

    # Test 8: Get active sessions count
    print("\n8. Getting active sessions count...")
    count = tracker.get_active_sessions_count()
    print(f"   Active sessions: {count}")
    assert count >= 1, "Should have at least 1 active session"
    print("   PASS: Active sessions counted")

    # Cleanup
    print("\n9. Cleaning up...")
    tracker.clear_all_sessions()
    count = tracker.get_active_sessions_count()
    print(f"   Active sessions after cleanup: {count}")
    assert count == 0, "Should have no active sessions after cleanup"
    print("   PASS: Sessions cleared")

    print("\n" + "="*60)
    print("SESSION LIFECYCLE TEST PASSED!")
    print("="*60)


def test_multiple_sessions():
    """Test handling multiple concurrent sessions."""
    print("\n" + "="*60)
    print("TEST: Multiple Sessions")
    print("="*60)

    tracker = ConversationTracker(window_hours=24)

    # Create multiple sessions
    phones = [
        '+34700000010',
        '+34700000020',
        '+34700000030',
    ]

    print("\n1. Creating multiple sessions...")
    for phone in phones:
        tracker.update_conversation(phone)
        print(f"   Created session for: {phone}")
    print("   PASS: Multiple sessions created")

    # Check each session
    print("\n2. Verifying each session...")
    for phone in phones:
        is_active = tracker.is_within_window(phone)
        print(f"   {phone}: active={is_active}")
        assert is_active == True, f"Session for {phone} should be active"
    print("   PASS: All sessions verified")

    # Get count
    print("\n3. Getting active sessions count...")
    count = tracker.get_active_sessions_count()
    print(f"   Active sessions: {count}")
    assert count >= 3, "Should have at least 3 active sessions"
    print("   PASS: Session count correct")

    # Cleanup
    print("\n4. Cleaning up...")
    tracker.clear_all_sessions()
    print("   PASS: Sessions cleared")

    print("\n" + "="*60)
    print("MULTIPLE SESSIONS TEST PASSED!")
    print("="*60)


def test_session_expiry():
    """Test session expiry with short window."""
    print("\n" + "="*60)
    print("TEST: Session Expiry")
    print("="*60)

    # Use very short window for testing (3 seconds)
    tracker = ConversationTracker(window_hours=3/3600)  # 3 seconds
    test_phone = '+34700000099'

    print("\n1. Creating session with 3-second window...")
    tracker.update_conversation(test_phone)
    is_active = tracker.is_within_window(test_phone)
    print(f"   Is active: {is_active}")
    assert is_active == True, "Session should be active immediately"
    print("   PASS: Session created and active")

    print("\n2. Waiting 4 seconds for expiry...")
    sleep(4)
    print("   Wait complete")

    print("\n3. Checking if session expired...")
    is_active = tracker.is_within_window(test_phone)
    print(f"   Is active: {is_active}")
    assert is_active == False, "Session should be expired after 4 seconds"
    print("   PASS: Session correctly expired")

    # Cleanup
    print("\n4. Cleaning up...")
    tracker.clear_all_sessions()
    print("   PASS: Sessions cleared")

    print("\n" + "="*60)
    print("SESSION EXPIRY TEST PASSED!")
    print("="*60)


def test_remaining_time_calculation():
    """Test remaining time calculation."""
    print("\n" + "="*60)
    print("TEST: Remaining Time Calculation")
    print("="*60)

    tracker = ConversationTracker(window_hours=24)
    test_phone = '+34700000088'

    print("\n1. Creating session...")
    tracker.update_conversation(test_phone)
    print("   PASS: Session created")

    print("\n2. Getting remaining time...")
    remaining = tracker.get_remaining_time(test_phone)
    print(f"   Remaining time: {remaining}")
    assert remaining is not None, "Should have remaining time"

    # Should be close to 24 hours (within 1 minute tolerance)
    total_hours = remaining.total_seconds() / 3600
    print(f"   Remaining hours: {total_hours:.2f}")
    assert 23.9 < total_hours <= 24.0, "Should have approximately 24 hours remaining"
    print("   PASS: Remaining time calculated correctly")

    # Cleanup
    print("\n3. Cleaning up...")
    tracker.clear_all_sessions()
    print("   PASS: Sessions cleared")

    print("\n" + "="*60)
    print("REMAINING TIME TEST PASSED!")
    print("="*60)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DATABASE CONVERSATION TRACKER TEST SUITE")
    print("="*60)

    try:
        test_session_lifecycle()
        test_multiple_sessions()
        test_session_expiry()
        test_remaining_time_calculation()

        print("\n" + "="*60)
        print("ALL TEST SUITES PASSED!")
        print("="*60)
        print("\nDatabase-backed ConversationTracker is working correctly!")
        print("API is compatible with JSON version.")

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
