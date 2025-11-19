"""
Test script for database models and manager.

This script tests:
1. Database connection via DatabaseManager
2. CRUD operations on all models
3. Relationships between models
4. GDPR cleanup function
5. Soft delete functionality

Run this script to verify the database setup is working correctly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from database.models import User, Consent, Session, AuditLog


def test_database_connection():
    """Test database connection."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)

    db = DatabaseManager()
    if db.test_connection():
        print("✅ Database connection successful")
        print(f"Pool status: {db.get_pool_status()}")
        return db
    else:
        print("❌ Database connection failed")
        sys.exit(1)


def test_user_crud(db: DatabaseManager):
    """Test User CRUD operations."""
    print("\n" + "="*60)
    print("TEST 2: User CRUD Operations")
    print("="*60)

    with db.get_session() as session:
        # Create user
        user = User(
            phone_number='+34644252886',
            display_name='Test User',
            language='es'
        )
        session.add(user)
        session.flush()  # Get user_id without committing

        user_id = user.user_id
        print(f"✅ User created: {user}")
        print(f"   User ID: {user_id}")
        print(f"   Is active: {user.is_active}")

    # Read user
    with db.get_session() as session:
        user = session.query(User).filter_by(phone_number='+34644252886').first()
        print(f"✅ User retrieved: {user.display_name}")

        # Update user
        user.display_name = 'Updated Test User'
        session.flush()
        print(f"✅ User updated: {user.display_name}")

    return user_id


def test_consent_crud(db: DatabaseManager, user_id):
    """Test Consent CRUD operations."""
    print("\n" + "="*60)
    print("TEST 3: Consent CRUD Operations")
    print("="*60)

    with db.get_session() as session:
        # Create consent
        consent = Consent(
            user_id=user_id,
            consent_given=True,
            consent_version='1.0',
            language='es'
        )
        session.add(consent)
        session.flush()

        consent_id = consent.consent_id
        print(f"✅ Consent created: {consent}")
        print(f"   Consent ID: {consent_id}")
        print(f"   Is active: {consent.is_active}")
        print(f"   Expires at: {consent.expires_at}")

    # Test consent withdrawal
    with db.get_session() as session:
        consent = session.query(Consent).filter_by(consent_id=consent_id).first()
        consent.withdraw()
        session.flush()
        print(f"✅ Consent withdrawn: {consent}")
        print(f"   Withdrawn at: {consent.withdrawal_date}")
        print(f"   Is active: {consent.is_active}")

    return consent_id


def test_session_crud(db: DatabaseManager, user_id):
    """Test Session CRUD operations."""
    print("\n" + "="*60)
    print("TEST 4: Session CRUD Operations")
    print("="*60)

    with db.get_session() as session_db:
        # Create session using helper method
        conv_session = Session.create_new(user_id=user_id, expiry_hours=24)
        session_db.add(conv_session)
        session_db.flush()

        session_id = conv_session.session_id
        print(f"✅ Session created: {conv_session}")
        print(f"   Session ID: {session_id}")
        print(f"   Is active: {conv_session.is_active}")
        print(f"   Expires at: {conv_session.expires_at}")

    # Update session activity
    with db.get_session() as session_db:
        conv_session = session_db.query(Session).filter_by(session_id=session_id).first()
        old_expiry = conv_session.expires_at
        conv_session.update_activity(expiry_hours=24)
        session_db.flush()

        print(f"✅ Session activity updated")
        print(f"   Old expiry: {old_expiry}")
        print(f"   New expiry: {conv_session.expires_at}")

    return session_id


def test_audit_log_crud(db: DatabaseManager, user_id):
    """Test AuditLog CRUD operations."""
    print("\n" + "="*60)
    print("TEST 5: Audit Log CRUD Operations")
    print("="*60)

    with db.get_session() as session:
        # Create audit logs using helper method
        logs = [
            AuditLog.log_action(
                user_id=user_id,
                action='user_created',
                actor='system',
                details={'source': 'whatsapp'}
            ),
            AuditLog.log_action(
                user_id=user_id,
                action='consent_given',
                actor='user',
                details={'version': '1.0'}
            ),
            AuditLog.log_action(
                user_id=user_id,
                action='route_requested',
                actor='user',
                details={'addresses': ['Address 1', 'Address 2']}
            )
        ]

        for log in logs:
            session.add(log)

        session.flush()
        print(f"✅ Created {len(logs)} audit log entries")

        for log in logs:
            print(f"   - {log.action}: {log.details}")
            print(f"     Expires at: {log.expires_at}")


def test_relationships(db: DatabaseManager, user_id):
    """Test relationships between models."""
    print("\n" + "="*60)
    print("TEST 6: Model Relationships")
    print("="*60)

    with db.get_session() as session:
        user = session.query(User).filter_by(user_id=user_id).first()

        print(f"✅ User: {user.phone_number}")
        print(f"   Consents: {len(user.consents)}")
        for consent in user.consents:
            print(f"     - Given: {consent.consent_given}, Withdrawn: {consent.consent_withdrawn}")

        print(f"   Sessions: {len(user.sessions)}")
        for sess in user.sessions:
            print(f"     - Expires: {sess.expires_at}, Active: {sess.is_active}")

        print(f"   Audit Logs: {len(user.audit_logs)}")
        for log in user.audit_logs:
            print(f"     - Action: {log.action}, Time: {log.created_at}")


def test_soft_delete(db: DatabaseManager, user_id):
    """Test soft delete functionality."""
    print("\n" + "="*60)
    print("TEST 7: Soft Delete")
    print("="*60)

    with db.get_session() as session:
        user = session.query(User).filter_by(user_id=user_id).first()
        print(f"Before soft delete - Is active: {user.is_active}")

        user.soft_delete()
        session.flush()

        print(f"✅ User soft deleted")
        print(f"   Deleted at: {user.deleted_at}")
        print(f"   Is active: {user.is_active}")

    # Verify soft delete
    with db.get_session() as session:
        user = session.query(User).filter_by(user_id=user_id).first()
        print(f"✅ Soft delete persisted: deleted_at = {user.deleted_at}")


def test_cleanup_function(db: DatabaseManager):
    """Test GDPR cleanup function."""
    print("\n" + "="*60)
    print("TEST 8: GDPR Cleanup Function")
    print("="*60)

    results = db.execute_cleanup()
    print("✅ Cleanup function executed successfully")
    print("   Results:")
    for table, count in results.items():
        print(f"     - {table}: {count} records processed")


def cleanup_test_data(db: DatabaseManager):
    """Clean up test data."""
    print("\n" + "="*60)
    print("Cleaning up test data...")
    print("="*60)

    with db.get_session() as session:
        # Delete test user and all related data (cascades)
        user = session.query(User).filter_by(phone_number='+34644252886').first()
        if user:
            # First delete consents (RESTRICT requires manual deletion)
            session.query(Consent).filter_by(user_id=user.user_id).delete()
            # Then delete user (will cascade to sessions and set audit_logs.user_id to NULL)
            session.delete(user)
            session.flush()
            print("✅ Test data cleaned up")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DATABASE MODELS AND MANAGER TEST SUITE")
    print("="*60)

    try:
        # Initialize database
        db = test_database_connection()

        # Run tests
        user_id = test_user_crud(db)
        consent_id = test_consent_crud(db, user_id)
        session_id = test_session_crud(db, user_id)
        test_audit_log_crud(db, user_id)
        test_relationships(db, user_id)
        test_soft_delete(db, user_id)
        test_cleanup_function(db)

        # Cleanup
        cleanup_test_data(db)

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)

        # Close database
        db.close()

    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
