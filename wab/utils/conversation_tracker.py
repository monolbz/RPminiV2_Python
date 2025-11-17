#!/usr/bin/env python3
"""
Conversation Tracker
Tracks 24-hour conversation windows for WhatsApp messaging.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from ..utils.logger import setup_logger
from ..utils.encryption import DataEncryptor

logger = setup_logger(__name__)


class ConversationTracker:
    """
    Tracks conversation windows to determine if free-form or template messages are needed.

    Phone numbers are hashed for privacy (GDPR compliance).
    Timestamps remain in plaintext for debugging.
    """

    def __init__(self, session_file=None, window_hours=24):
        """
        Initialize conversation tracker.

        Args:
            session_file (str, optional): Path to session storage file
            window_hours (int): Length of conversation window in hours (default: 24)
        """
        self.window_hours = window_hours

        # Initialize encryptor for phone number hashing
        try:
            self.encryptor = DataEncryptor()
            logger.info("Encryption enabled for conversation tracker")
        except Exception as e:
            logger.warning(f"Encryption not available: {e}. Phone numbers will not be hashed.")
            self.encryptor = None

        # Set session file path
        if session_file is None:
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            self.session_file = data_dir / 'sessions.json'
        else:
            self.session_file = Path(session_file)

        # Load existing sessions
        self.sessions = self._load_sessions()

    def _load_sessions(self):
        """
        Load sessions from file.

        Returns:
            dict: Dictionary of phone_number -> last_message_time
        """
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    sessions = json.load(f)
                    logger.info(f"Loaded {len(sessions)} existing sessions")
                    return sessions
            else:
                logger.info("No existing sessions file found, starting fresh")
                return {}
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            return {}

    def _save_sessions(self):
        """Save sessions to file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
            logger.debug(f"Saved {len(self.sessions)} sessions to file")
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")

    def _get_session_key(self, phone_number):
        """
        Get session key for a phone number.

        If encryption is enabled, returns hashed key (phone_xxx).
        Otherwise returns plain phone number (fallback).

        Args:
            phone_number (str): Plain phone number

        Returns:
            str: Hashed key or plain phone number
        """
        if self.encryptor:
            return self.encryptor.hash_phone(phone_number)
        else:
            return phone_number

    def update_conversation(self, phone_number):
        """
        Update conversation timestamp for a phone number.
        Call this when receiving a message from the user.

        Args:
            phone_number (str): User's phone number (plain text)

        Note:
            Phone number is hashed before storage for privacy.
            Timestamp is stored in plaintext for debugging.
        """
        try:
            # Get hashed key for storage
            session_key = self._get_session_key(phone_number)

            # Store current time (plaintext for debugging)
            current_time = datetime.now().isoformat()
            self.sessions[session_key] = current_time

            logger.info(f"Updated conversation window (hashed key: {session_key[:20]}...)")

            # Save to file
            self._save_sessions()

            # Clean up old sessions
            self._cleanup_old_sessions()

        except Exception as e:
            logger.error(f"Error updating conversation: {e}")

    def is_within_window(self, phone_number):
        """
        Check if a conversation is within the 24-hour window.

        Args:
            phone_number (str): User's phone number (plain text)

        Returns:
            bool: True if within window, False otherwise
        """
        try:
            # Reload sessions from file to get latest data
            self.sessions = self._load_sessions()

            # Get hashed key for lookup
            session_key = self._get_session_key(phone_number)

            # Check if session exists
            if session_key not in self.sessions:
                logger.info(f"No active session (hashed key: {session_key[:20]}...)")
                return False

            # Get last message time
            last_message_str = self.sessions[session_key]
            last_message_time = datetime.fromisoformat(last_message_str)

            # Calculate time difference
            current_time = datetime.now()
            time_diff = current_time - last_message_time

            # Check if within window
            window_duration = timedelta(hours=self.window_hours)
            is_within = time_diff < window_duration

            if is_within:
                remaining = window_duration - time_diff
                logger.info(f"Session active (hashed key: {session_key[:20]}...) - {remaining} remaining")
            else:
                logger.info(f"Session expired (hashed key: {session_key[:20]}...) - expired {time_diff - window_duration} ago")

            return is_within

        except Exception as e:
            logger.error(f"Error checking conversation window: {e}")
            return False

    def get_remaining_time(self, phone_number):
        """
        Get remaining time in conversation window.

        Args:
            phone_number (str): User's phone number (plain text)

        Returns:
            timedelta: Remaining time, or None if no active session
        """
        try:
            # Get hashed key for lookup
            session_key = self._get_session_key(phone_number)

            if session_key not in self.sessions:
                return None

            last_message_str = self.sessions[session_key]
            last_message_time = datetime.fromisoformat(last_message_str)

            current_time = datetime.now()
            window_duration = timedelta(hours=self.window_hours)
            expiry_time = last_message_time + window_duration

            remaining = expiry_time - current_time

            if remaining.total_seconds() > 0:
                return remaining
            else:
                return timedelta(0)

        except Exception as e:
            logger.error(f"Error getting remaining time: {e}")
            return None

    def _cleanup_old_sessions(self):
        """Remove expired sessions to keep storage clean."""
        try:
            current_time = datetime.now()
            expired_numbers = []

            for phone_number, last_message_str in self.sessions.items():
                try:
                    last_message_time = datetime.fromisoformat(last_message_str)
                    time_diff = current_time - last_message_time

                    # Remove sessions older than 48 hours (2x window)
                    if time_diff > timedelta(hours=self.window_hours * 2):
                        expired_numbers.append(phone_number)

                except Exception as e:
                    logger.warning(f"Invalid session data for {phone_number}: {e}")
                    expired_numbers.append(phone_number)

            # Remove expired sessions
            for phone_number in expired_numbers:
                del self.sessions[phone_number]

            if expired_numbers:
                logger.info(f"Cleaned up {len(expired_numbers)} expired sessions")
                self._save_sessions()

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")

    def get_active_sessions_count(self):
        """
        Get count of currently active sessions.

        Returns:
            int: Number of active sessions
        """
        count = 0
        for phone_number in self.sessions.keys():
            if self.is_within_window(phone_number):
                count += 1
        return count

    def clear_all_sessions(self):
        """Clear all sessions (for testing/debugging)."""
        self.sessions = {}
        self._save_sessions()
        logger.info("Cleared all sessions")
