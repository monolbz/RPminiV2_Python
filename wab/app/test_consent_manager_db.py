#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for database-backed ConsentManager.

Verifies that the database version maintains API compatibility
with the JSON version while providing database benefits.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.consent_manager_db import ConsentManager


def test_consent_flow():
    """Test complete consent flow."""
    print("\n" + "="*60)
    print("TEST: Complete Consent Flow")
    print("="*60)

    cm = ConsentManager()
    test_phone = '+34600000001'

    # Test 1: Check initial state (should have no consent)
    print("\n1. Checking initial state...")
    has_consent = cm.has_consent(test_phone)
    print(f"   Has consent: {has_consent}")
    assert has_consent == False, "New user should not have consent"
    print("   PASS: New user has no consent")

    # Test 2: Save consent
    print("\n2. Saving consent...")
    success = cm.save_consent(
        phone_number=test_phone,
        consent_given=True,
        ip_address='192.168.1.1',
        user_agent='WhatsApp/2.0',
        language='es'
    )
    print(f"   Save successful: {success}")
    assert success == True, "Consent save should succeed"
    print("   PASS: Consent saved successfully")

    # Test 3: Check consent after saving
    print("\n3. Checking consent after saving...")
    has_consent = cm.has_consent(test_phone)
    print(f"   Has consent: {has_consent}")
    assert has_consent == True, "User should have consent after saving"
    print("   PASS: User has valid consent")

    # Test 4: Get consent info
    print("\n4. Getting consent info...")
    info = cm.get_consent_info(test_phone)
    print(f"   Consent info:")
    print(f"     - Given: {info['consent_given']}")
    print(f"     - Date: {info['consent_date']}")
    print(f"     - Withdrawn: {info['consent_withdrawn']}")
    print(f"     - Version: {info['consent_version']}")
    assert info['consent_given'] == True, "Consent should be given"
    assert info['consent_withdrawn'] == False, "Consent should not be withdrawn"
    print("   PASS: Consent info retrieved correctly")

    # Test 5: Get consent date
    print("\n5. Getting consent date...")
    date = cm.get_consent_date(test_phone)
    print(f"   Consent date: {date}")
    assert date is not None, "Consent date should exist"
    print("   PASS: Consent date retrieved")

    # Test 6: Revoke consent
    print("\n6. Revoking consent...")
    success = cm.revoke_consent(test_phone)
    print(f"   Revoke successful: {success}")
    assert success == True, "Consent revocation should succeed"
    print("   PASS: Consent revoked successfully")

    # Test 7: Check consent after revocation
    print("\n7. Checking consent after revocation...")
    has_consent = cm.has_consent(test_phone)
    print(f"   Has consent: {has_consent}")
    assert has_consent == False, "User should not have consent after revocation"
    print("   PASS: Consent correctly revoked")

    # Test 8: Verify revocation in info
    print("\n8. Verifying revocation in consent info...")
    info = cm.get_consent_info(test_phone)
    print(f"   Consent withdrawn: {info['consent_withdrawn']}")
    print(f"   Withdrawal date: {info['withdrawal_date']}")
    assert info['consent_withdrawn'] == True, "Consent should be marked as withdrawn"
    assert info['withdrawal_date'] is not None, "Withdrawal date should exist"
    print("   PASS: Revocation recorded correctly")

    # Test 9: Export data
    print("\n9. Exporting user data...")
    export = cm.export_user_consent_data(test_phone)
    print(f"   Export data:")
    print(f"     - Phone: {export['phone_number']}")
    print(f"     - Status: {export['consent_status']}")
    print(f"     - History: {len(export['consent_history'])} records")
    assert export['consent_status'] == 'Withdrawn', "Status should be Withdrawn"
    assert len(export['consent_history']) >= 1, "Should have consent history"
    print("   PASS: Data exported successfully")

    # Test 10: Get statistics
    print("\n10. Getting statistics...")
    stats = cm.get_statistics()
    print(f"   Statistics:")
    print(f"     - Total records: {stats['total_records']}")
    print(f"     - Active consents: {stats['active_consents']}")
    print(f"     - Withdrawn consents: {stats['withdrawn_consents']}")
    print(f"     - Total users: {stats['total_users']}")
    assert stats['total_records'] >= 1, "Should have at least one record"
    print("   PASS: Statistics retrieved")

    # Cleanup
    print("\n11. Cleaning up test data...")
    cm.delete_consent_record(test_phone)
    print("   PASS: Test data cleaned up")

    print("\n" + "="*60)
    print("ALL TESTS PASSED!")
    print("="*60)


def test_multiple_users():
    """Test handling multiple users."""
    print("\n" + "="*60)
    print("TEST: Multiple Users")
    print("="*60)

    cm = ConsentManager()

    # Create multiple users
    users = [
        ('+34600000010', True, 'es'),
        ('+34600000020', True, 'en'),
        ('+34600000030', False, 'es'),
    ]

    print("\n1. Creating multiple users...")
    for phone, consent, lang in users:
        cm.save_consent(phone, consent, language=lang)
        print(f"   Created: {phone} (consent: {consent}, lang: {lang})")

    print("   PASS: Multiple users created")

    # Check each user
    print("\n2. Verifying each user...")
    for phone, expected_consent, lang in users:
        has_consent = cm.has_consent(phone)
        assert has_consent == expected_consent, f"User {phone} consent mismatch"
        print(f"   {phone}: consent={has_consent} (expected={expected_consent})")

    print("   PASS: All users verified")

    # Get statistics
    print("\n3. Getting statistics...")
    stats = cm.get_statistics()
    print(f"   Active consents: {stats['active_consents']}")
    print(f"   Declined consents: {stats['declined_consents']}")
    assert stats['active_consents'] >= 2, "Should have at least 2 active consents"
    assert stats['declined_consents'] >= 1, "Should have at least 1 declined consent"
    print("   PASS: Statistics correct")

    # Cleanup
    print("\n4. Cleaning up...")
    for phone, _, _ in users:
        cm.delete_consent_record(phone)
    print("   PASS: Test data cleaned up")

    print("\n" + "="*60)
    print("MULTIPLE USERS TEST PASSED!")
    print("="*60)


def test_consent_version_tracking():
    """Test consent version tracking."""
    print("\n" + "="*60)
    print("TEST: Consent Version Tracking")
    print("="*60)

    cm = ConsentManager()
    test_phone = '+34600000099'

    # Give consent with version 1.0
    print("\n1. Giving consent with version 1.0...")
    cm.save_consent(test_phone, True, language='es')
    info = cm.get_consent_info(test_phone)
    print(f"   Version: {info['consent_version']}")
    assert info['consent_version'] == '1.0', "Should be version 1.0"
    print("   PASS: Version 1.0 recorded")

    # Export shows version
    print("\n2. Verifying version in export...")
    export = cm.export_user_consent_data(test_phone)
    print(f"   Export version: {export['consent_version']}")
    assert export['consent_version'] == '1.0', "Export should show version 1.0"
    print("   PASS: Version in export correct")

    # Cleanup
    print("\n3. Cleaning up...")
    cm.delete_consent_record(test_phone)
    print("   PASS: Test data cleaned up")

    print("\n" + "="*60)
    print("VERSION TRACKING TEST PASSED!")
    print("="*60)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DATABASE CONSENT MANAGER TEST SUITE")
    print("="*60)

    try:
        test_consent_flow()
        test_multiple_users()
        test_consent_version_tracking()

        print("\n" + "="*60)
        print("ALL TEST SUITES PASSED!")
        print("="*60)
        print("\nDatabase-backed ConsentManager is working correctly!")
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
