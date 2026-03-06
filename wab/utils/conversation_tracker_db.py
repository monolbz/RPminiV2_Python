#!/usr/bin/env python3
"""
Conversation Tracker - Database Version

Database-backed implementation of ConversationTracker using PostgreSQL.
Maintains the same API as the JSON-based version for easy migration.

Tracks 24-hour conversation windows for WhatsApp messaging with:
- Automatic session expiry (48 hours)
- Thread-safe operations
- High performance with database indexes
- GDPR-compliant data lifecycle
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import get_db_manager
from database.models import User, Session, AuditLog
from ..utils.logger import setup_logger
from ..app import usage_manager

logger = setup_logger(__name__)


class ConversationTracker:
    """
    Tracks conversation windows using PostgreSQL database.

    This is a database-backed implementation suitable for:
    - Any scale (handles millions of sessions)
    - Multi-server deployment
    - High concurrency
    - Production environments

    Features:
    - Automatic session cleanup (48 hours)
    - Thread-safe operations
    - Same API as JSON version (drop-in replacement)
    """

    def __init__(self, database_url: Optional[str] = None, window_hours: int = 24):
        """
        Initialize conversation tracker.

        Args:
            database_url: PostgreSQL connection URL (optional)
            window_hours: Length of conversation window in hours (default: 24)
        """
        self.window_hours = window_hours

        try:
            self.db = get_db_manager(database_url=database_url)
            logger.info("ConversationTracker initialized with database backend")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def update_conversation(self, phone_number: str):
        """
        Update conversation timestamp for a phone number.
        Call this when receiving a message from the user.

        Args:
            phone_number: User's phone number
        """
        try:
            with self.db.get_session() as session_db:
                # Get or create user
                user = session_db.query(User).filter_by(
                    phone_number=phone_number
                ).first()

                if not user:
                    # Create user if doesn't exist
                    user = User(phone_number=phone_number)
                    session_db.add(user)
                    session_db.flush()

                    # Assign default tier at creation time
                    usage_manager.assign_default_tier(user, session_db)

                    logger.info(f"Created new user: {phone_number}")

                # Get or create session
                conv_session = session_db.query(Session).filter_by(
                    user_id=user.user_id
                ).first()

                if conv_session:
                    # Update existing session
                    conv_session.update_activity(expiry_hours=self.window_hours)
                    logger.info(f"Updated conversation window for {phone_number}")
                else:
                    # Create new session
                    conv_session = Session.create_new(
                        user_id=user.user_id,
                        expiry_hours=self.window_hours
                    )
                    session_db.add(conv_session)
                    logger.info(f"Created new conversation window for {phone_number}")

                    # Log session start
                    audit = AuditLog.log_action(
                        user_id=user.user_id,
                        action='session_started',
                        actor='system',
                        details={'window_hours': self.window_hours}
                    )
                    session_db.add(audit)

        except Exception as e:
            logger.error(f"Error updating conversation: {e}", exc_info=True)

    def is_within_window(self, phone_number: str) -> bool:
        """
        Check if a conversation is within the 24-hour window.

        Args:
            phone_number: User's phone number

        Returns:
            bool: True if within window, False otherwise
        """
        try:
            with self.db.get_session() as session_db:
                # Get user
                user = session_db.query(User).filter_by(
                    phone_number=phone_number
                ).first()

                if not user:
                    logger.info(f"No active session for {phone_number}")
                    return False

                # Get session
                conv_session = session_db.query(Session).filter_by(
                    user_id=user.user_id
                ).first()

                if not conv_session:
                    logger.info(f"No active session for {phone_number}")
                    return False

                # Check if session is active
                if conv_session.is_active:
                    remaining = conv_session.expires_at - datetime.now(conv_session.expires_at.tzinfo)
                    logger.info(f"Session active for {phone_number} - {remaining} remaining")
                    return True
                else:
                    expired_ago = datetime.now(conv_session.expires_at.tzinfo) - conv_session.expires_at
                    logger.info(f"Session expired for {phone_number} - expired {expired_ago} ago")
                    return False

        except Exception as e:
            logger.error(f"Error checking conversation window: {e}", exc_info=True)
            return False

    def get_remaining_time(self, phone_number: str) -> Optional[timedelta]:
        """
        Get remaining time in conversation window.

        Args:
            phone_number: User's phone number

        Returns:
            timedelta: Remaining time, or None if no active session
        """
        try:
            with self.db.get_session() as session_db:
                # Get user
                user = session_db.query(User).filter_by(
                    phone_number=phone_number
                ).first()

                if not user:
                    return None

                # Get session
                conv_session = session_db.query(Session).filter_by(
                    user_id=user.user_id
                ).first()

                if not conv_session:
                    return None

                # Calculate remaining time
                current_time = datetime.now(conv_session.expires_at.tzinfo)
                remaining = conv_session.expires_at - current_time

                if remaining.total_seconds() > 0:
                    return remaining
                else:
                    return timedelta(0)

        except Exception as e:
            logger.error(f"Error getting remaining time: {e}", exc_info=True)
            return None

    def get_active_sessions_count(self) -> int:
        """
        Get count of currently active sessions.

        Returns:
            int: Number of active sessions
        """
        try:
            with self.db.get_session() as session_db:
                # Count sessions that haven't expired
                current_time = datetime.now()
                count = session_db.query(Session).filter(
                    Session.expires_at > current_time
                ).count()

                return count

        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}", exc_info=True)
            return 0

    def clear_all_sessions(self):
        """
        Clear all sessions (for testing/debugging).

        Warning: This deletes all session data!
        """
        try:
            with self.db.get_session() as session_db:
                deleted = session_db.query(Session).delete()
                logger.info(f"Cleared {deleted} sessions")

        except Exception as e:
            logger.error(f"Error clearing sessions: {e}", exc_info=True)

    def cleanup_expired_sessions(self) -> int:
        """
        Manually trigger cleanup of expired sessions.

        Note: This is also handled automatically by the database
        cleanup_expired_data() function, but provided here for API compatibility.

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            # Use database cleanup function
            results = self.db.execute_cleanup()
            deleted_count = results.get('sessions', 0)

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}", exc_info=True)
            return 0

    def get_session_info(self, phone_number: str) -> Optional[dict]:
        """
        Get detailed session information for a user.

        Args:
            phone_number: User's phone number

        Returns:
            dict: Session information, or None if no session
        """
        try:
            with self.db.get_session() as session_db:
                # Get user
                user = session_db.query(User).filter_by(
                    phone_number=phone_number
                ).first()

                if not user:
                    return None

                # Get session
                conv_session = session_db.query(Session).filter_by(
                    user_id=user.user_id
                ).first()

                if not conv_session:
                    return None

                # Format session info
                return {
                    'session_id': str(conv_session.session_id),
                    'phone_number': phone_number,
                    'last_message_at': conv_session.last_message_at.isoformat(),
                    'expires_at': conv_session.expires_at.isoformat(),
                    'created_at': conv_session.created_at.isoformat(),
                    'is_active': conv_session.is_active,
                    'remaining_time': str(self.get_remaining_time(phone_number))
                }

        except Exception as e:
            logger.error(f"Error getting session info: {e}", exc_info=True)
            return None


# =============================================================================
# MIGRATION FROM JSON VERSION
# =============================================================================

def migrate_from_json(json_file_path: str, db_manager=None, window_hours: int = 24) -> dict:
    """
    Migrate session data from JSON file to database.

    Args:
        json_file_path: Path to sessions.json file
        db_manager: DatabaseManager instance (optional)
        window_hours: Session window duration in hours

    Returns:
        dict: Migration statistics {'migrated': N, 'errors': M, 'skipped': K}

    Example:
        from wab.utils.conversation_tracker_db import migrate_from_json

        stats = migrate_from_json('wab/data/sessions.json')
        print(f"Migrated {stats['migrated']} sessions with {stats['errors']} errors")
    """
    import json

    if db_manager is None:
        db_manager = get_db_manager()

    migrated = 0
    errors = 0
    skipped = 0

    try:
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Starting migration of {len(data)} sessions from JSON to database")

        for phone_number, last_message_str in data.items():
            try:
                with db_manager.get_session() as session_db:
                    # Parse timestamp
                    last_message_time = datetime.fromisoformat(last_message_str)

                    # Check if session is still valid (not expired)
                    current_time = datetime.now()
                    time_diff = current_time - last_message_time

                    if time_diff > timedelta(hours=window_hours * 2):
                        # Skip expired sessions (older than 48 hours)
                        skipped += 1
                        continue

                    # Get or create user
                    user = session_db.query(User).filter_by(
                        phone_number=phone_number
                    ).first()

                    if not user:
                        user = User(phone_number=phone_number)
                        session_db.add(user)
                        session_db.flush()

                    # Calculate expiry time
                    expires_at = last_message_time + timedelta(hours=window_hours)

                    # Create session
                    conv_session = Session(
                        user_id=user.user_id,
                        last_message_at=last_message_time,
                        expires_at=expires_at,
                        created_at=last_message_time
                    )
                    session_db.add(conv_session)

                    migrated += 1

                    if migrated % 100 == 0:
                        logger.info(f"Migrated {migrated} sessions...")

            except Exception as e:
                logger.error(f"Error migrating session for {phone_number}: {e}")
                errors += 1

        logger.info(f"Migration complete: {migrated} sessions migrated, {skipped} skipped (expired), {errors} errors")

        return {'migrated': migrated, 'errors': errors, 'skipped': skipped}

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return {'migrated': migrated, 'errors': errors + 1, 'skipped': skipped}
