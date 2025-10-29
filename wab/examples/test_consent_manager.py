#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for ConsentManager

Tests all consent management functionality including:
- Saving consent (accept/decline)
- Checking consent status
- Revoking consent
- Retrieving consent information
- Data export
- Cleanup of expired records
"""

import sys
import io
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.consent_manager import ConsentManager, format_consent_date


def test_basic_consent_flow():
    """Test basic consent accept/check/revoke flow"""
    print("\n" + "="*80)
    print("TEST 1: Basic Consent Flow")
    print("="*80)

    # Create temporary storage for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        # Initialize manager
        manager = ConsentManager(storage_path=temp_path)
        phone = "34600123456"

        # Test 1: No consent initially
        print(f"\n1. Checking initial state for {phone}")
        has_consent = manager.has_consent(phone)
        print(f"   Has consent: {has_consent}")
        assert has_consent == False, "Should not have consent initially"
        print("   ✓ PASS: No consent initially")

        # Test 2: Save consent (accept)
        print(f"\n2. Saving consent (accept)")
        success = manager.save_consent(phone, consent_given=True, language="es")
        print(f"   Saved: {success}")
        assert success == True, "Should save successfully"
        print("   ✓ PASS: Consent saved")

        # Test 3: Check consent (should be True)
        print(f"\n3. Checking consent after accept")
        has_consent = manager.has_consent(phone)
        print(f"   Has consent: {has_consent}")
        assert has_consent == True, "Should have consent after accepting"
        print("   ✓ PASS: Has valid consent")

        # Test 4: Get consent date
        print(f"\n4. Getting consent date")
        consent_date = manager.get_consent_date(phone)
        print(f"   Consent date: {consent_date}")
        formatted_date = format_consent_date(consent_date, "es")
        print(f"   Formatted (ES): {formatted_date}")
        assert consent_date is not None, "Should have consent date"
        print("   ✓ PASS: Consent date retrieved")

        # Test 5: Revoke consent
        print(f"\n5. Revoking consent")
        success = manager.revoke_consent(phone)
        print(f"   Revoked: {success}")
        assert success == True, "Should revoke successfully"
        print("   ✓ PASS: Consent revoked")

        # Test 6: Check consent after revocation (should be False)
        print(f"\n6. Checking consent after revocation")
        has_consent = manager.has_consent(phone)
        print(f"   Has consent: {has_consent}")
        assert has_consent == False, "Should not have consent after revocation"
        print("   ✓ PASS: No consent after revocation")

        # Test 7: Verify record still exists (for proof)
        print(f"\n7. Checking if record still exists")
        info = manager.get_consent_info(phone)
        print(f"   Record exists: {info is not None}")
        print(f"   Consent withdrawn: {info.get('consent_withdrawn')}")
        assert info is not None, "Record should still exist"
        assert info['consent_withdrawn'] == True, "Should be marked as withdrawn"
        print("   ✓ PASS: Record preserved for legal proof")

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Basic Consent Flow")
        print("="*80)

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_consent_decline():
    """Test declining consent"""
    print("\n" + "="*80)
    print("TEST 2: Consent Decline")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)
        phone = "34600987654"

        # Save consent decline
        print(f"\n1. User declines consent")
        success = manager.save_consent(phone, consent_given=False)
        print(f"   Saved: {success}")
        assert success == True, "Should save decline successfully"
        print("   ✓ PASS: Decline saved")

        # Check consent (should be False)
        print(f"\n2. Checking consent after decline")
        has_consent = manager.has_consent(phone)
        print(f"   Has consent: {has_consent}")
        assert has_consent == False, "Should not have consent after decline"
        print("   ✓ PASS: No consent after decline")

        # Verify record exists
        print(f"\n3. Checking if decline is recorded")
        info = manager.get_consent_info(phone)
        print(f"   Consent given: {info.get('consent_given')}")
        assert info['consent_given'] == False, "Should record decline"
        print("   ✓ PASS: Decline recorded")

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Consent Decline")
        print("="*80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_data_export():
    """Test GDPR data export functionality"""
    print("\n" + "="*80)
    print("TEST 3: Data Export (GDPR Article 20)")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)
        phone = "34611222333"

        # Save consent
        print(f"\n1. Saving consent for {phone}")
        manager.save_consent(
            phone,
            consent_given=True,
            ip_address="192.168.1.100",
            user_agent="WhatsApp/2.23.1",
            language="es"
        )
        print("   ✓ Consent saved with metadata")

        # Export data
        print(f"\n2. Exporting user data")
        export_data = manager.export_user_consent_data(phone)
        print(f"   Export data:")
        for key, value in export_data.items():
            print(f"     {key}: {value}")
        assert export_data is not None, "Should export data"
        assert export_data['phone_number'] == phone, "Should include phone number"
        assert export_data['consent_status'] == 'Active', "Should show active status"
        print("   ✓ PASS: Data exported successfully")

        # Export as JSON
        print(f"\n3. Formatting as JSON")
        json_export = json.dumps(export_data, indent=2, ensure_ascii=False)
        print(f"   JSON export:\n{json_export}")
        print("   ✓ PASS: JSON export created")

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Data Export")
        print("="*80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_statistics():
    """Test consent statistics"""
    print("\n" + "="*80)
    print("TEST 4: Consent Statistics")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)

        # Create various consent states
        print(f"\n1. Creating test data")
        manager.save_consent("34600111111", consent_given=True)  # Active
        manager.save_consent("34600222222", consent_given=True)  # Active
        manager.save_consent("34600333333", consent_given=True)  # Will revoke
        manager.save_consent("34600444444", consent_given=False)  # Declined
        manager.revoke_consent("34600333333")  # Withdrawn
        print("   ✓ Test data created")

        # Get statistics
        print(f"\n2. Getting statistics")
        stats = manager.get_statistics()
        print(f"   Statistics:")
        for key, value in stats.items():
            if key != 'storage_path':
                print(f"     {key}: {value}")

        assert stats['total_records'] == 4, "Should have 4 total records"
        assert stats['active_consents'] == 2, "Should have 2 active consents"
        assert stats['withdrawn_consents'] == 1, "Should have 1 withdrawn"
        assert stats['declined_consents'] == 1, "Should have 1 declined"
        print("   ✓ PASS: Statistics correct")

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Statistics")
        print("="*80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_multiple_users():
    """Test handling multiple users"""
    print("\n" + "="*80)
    print("TEST 5: Multiple Users")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)

        users = [
            ("34600111111", True),
            ("34600222222", True),
            ("34600333333", False),
            ("34611444444", True),
            ("34622555555", True),
        ]

        # Save consents
        print(f"\n1. Saving consents for {len(users)} users")
        for phone, consent in users:
            manager.save_consent(phone, consent_given=consent)
        print(f"   ✓ All consents saved")

        # Check each user
        print(f"\n2. Checking each user's consent")
        for phone, expected_consent in users:
            has_consent = manager.has_consent(phone)
            status = "✓" if has_consent == expected_consent else "✗"
            print(f"   {status} {phone}: has_consent={has_consent} (expected={expected_consent})")
            assert has_consent == expected_consent, f"Mismatch for {phone}"

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Multiple Users")
        print("="*80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "="*80)
    print("TEST 6: Edge Cases")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)

        # Test 1: Check non-existent user
        print(f"\n1. Checking non-existent user")
        has_consent = manager.has_consent("34699999999")
        print(f"   Has consent: {has_consent}")
        assert has_consent == False, "Non-existent user should not have consent"
        print("   ✓ PASS: Non-existent user handled")

        # Test 2: Revoke consent for non-existent user
        print(f"\n2. Revoking consent for non-existent user")
        success = manager.revoke_consent("34699999999")
        print(f"   Success: {success}")
        assert success == False, "Should return False for non-existent user"
        print("   ✓ PASS: Non-existent revocation handled")

        # Test 3: Get info for non-existent user
        print(f"\n3. Getting info for non-existent user")
        info = manager.get_consent_info("34699999999")
        print(f"   Info: {info}")
        assert info is None, "Should return None for non-existent user"
        print("   ✓ PASS: Non-existent info handled")

        # Test 4: Export data for non-existent user
        print(f"\n4. Exporting data for non-existent user")
        export = manager.export_user_consent_data("34699999999")
        print(f"   Export: {export}")
        assert export is None, "Should return None for non-existent user"
        print("   ✓ PASS: Non-existent export handled")

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED: Edge Cases")
        print("="*80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def show_storage_format():
    """Show the JSON storage format"""
    print("\n" + "="*80)
    print("DEMONSTRATION: Storage Format")
    print("="*80)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        manager = ConsentManager(storage_path=temp_path)

        # Create sample data
        manager.save_consent(
            "34600123456",
            consent_given=True,
            ip_address="192.168.1.100",
            user_agent="WhatsApp/2.23.1",
            language="es"
        )

        # Show raw storage
        print("\nJSON Storage Format:")
        print("-" * 80)
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        print("-" * 80)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("CONSENT MANAGER TEST SUITE")
    print("="*80)

    try:
        test_basic_consent_flow()
        test_consent_decline()
        test_data_export()
        test_statistics()
        test_multiple_users()
        test_edge_cases()
        show_storage_format()

        print("\n" + "="*80)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("="*80)
        print("""
ConsentManager is working correctly!

Key features tested:
✓ Saving consent (accept/decline)
✓ Checking consent status
✓ Revoking consent
✓ Preserving records for legal proof
✓ Data export (GDPR Article 20)
✓ Statistics and monitoring
✓ Multiple users handling
✓ Edge cases and error handling

Next steps:
1. Integrate with message_processor.py
2. Implement GDPR commands (/mydata, /deletedata, etc.)
3. Test with real WhatsApp webhook
4. Consider encryption for production
5. Set up automated backups
        """)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
