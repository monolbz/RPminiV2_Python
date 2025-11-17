#!/usr/bin/env python3
"""
Rate Limiter
Implements per-user rate limiting and message loop detection for webhook requests.
"""

from collections import defaultdict
from datetime import datetime, timedelta
import time
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """
    Per-user rate limiter to prevent spam and abuse.

    Tracks requests per user and enforces configurable limits.
    """

    def __init__(self, max_requests=10, window_minutes=1):
        """
        Initialize rate limiter.

        Args:
            max_requests (int): Maximum requests allowed per window
            window_minutes (int): Time window in minutes
        """
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.request_history = defaultdict(list)

        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_minutes} minute(s)")

    def check_limit(self, user_id):
        """
        Check if user has exceeded rate limit.

        Args:
            user_id (str): Unique identifier for user (e.g., phone number)

        Returns:
            tuple: (bool, dict) - (is_allowed, info_dict)
                is_allowed: True if request should be allowed
                info_dict: Contains 'remaining', 'reset_time', 'limit'
        """
        now = datetime.now()
        cutoff = now - self.window

        # Clean old requests outside the window
        self.request_history[user_id] = [
            timestamp for timestamp in self.request_history[user_id]
            if timestamp > cutoff
        ]

        current_count = len(self.request_history[user_id])
        remaining = max(0, self.max_requests - current_count)

        # Calculate reset time (oldest request + window)
        if self.request_history[user_id]:
            reset_time = self.request_history[user_id][0] + self.window
        else:
            reset_time = now + self.window

        # Check if limit exceeded
        if current_count >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {user_id}: "
                f"{current_count}/{self.max_requests} requests in window"
            )
            return False, {
                'remaining': 0,
                'reset_time': reset_time,
                'limit': self.max_requests,
                'current': current_count
            }

        # Add current request to history
        self.request_history[user_id].append(now)

        logger.debug(
            f"Rate limit check for {user_id}: "
            f"{current_count + 1}/{self.max_requests} requests, "
            f"{remaining - 1} remaining"
        )

        return True, {
            'remaining': remaining - 1,
            'reset_time': reset_time,
            'limit': self.max_requests,
            'current': current_count + 1
        }

    def cleanup_old_entries(self, max_age_hours=24):
        """
        Clean up old entries to prevent memory bloat.
        Call this periodically (e.g., hourly).

        Args:
            max_age_hours (int): Remove entries older than this many hours
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        users_to_remove = []

        for user_id, timestamps in self.request_history.items():
            # Remove old timestamps
            self.request_history[user_id] = [
                ts for ts in timestamps if ts > cutoff
            ]

            # Mark empty entries for removal
            if not self.request_history[user_id]:
                users_to_remove.append(user_id)

        # Remove empty entries
        for user_id in users_to_remove:
            del self.request_history[user_id]

        if users_to_remove:
            logger.info(f"Cleaned up {len(users_to_remove)} old rate limit entries")

    def get_user_stats(self, user_id):
        """
        Get current rate limit stats for a user.

        Args:
            user_id (str): User identifier

        Returns:
            dict: Stats including request count, limit, window
        """
        now = datetime.now()
        cutoff = now - self.window

        # Count recent requests
        recent_requests = [
            ts for ts in self.request_history.get(user_id, [])
            if ts > cutoff
        ]

        return {
            'user_id': user_id,
            'requests_in_window': len(recent_requests),
            'limit': self.max_requests,
            'window_minutes': self.window.total_seconds() / 60,
            'remaining': max(0, self.max_requests - len(recent_requests))
        }


class MessageLoopDetector:
    """
    Detects message loops where user sends same message repeatedly.

    Prevents infinite loops and spam by detecting repetitive patterns.
    """

    def __init__(self, threshold=3, window_minutes=5):
        """
        Initialize loop detector.

        Args:
            threshold (int): Number of identical messages that trigger detection
            window_minutes (int): Time window for counting messages
        """
        self.threshold = threshold
        self.window = timedelta(minutes=window_minutes)
        self.message_history = defaultdict(lambda: defaultdict(list))

        logger.info(
            f"Loop detector initialized: {threshold} identical messages "
            f"in {window_minutes} minutes triggers detection"
        )

    def check_loop(self, user_id, message_text):
        """
        Check if user is in a message loop.

        Args:
            user_id (str): User identifier
            message_text (str): Message content to check

        Returns:
            tuple: (bool, dict) - (is_loop_detected, info_dict)
        """
        # Create hash of message text for comparison
        message_hash = hash(message_text)
        now = datetime.now()
        cutoff = now - self.window

        # Clean old messages outside window
        for msg_hash in list(self.message_history[user_id].keys()):
            self.message_history[user_id][msg_hash] = [
                ts for ts in self.message_history[user_id][msg_hash]
                if ts > cutoff
            ]

            # Remove empty entries
            if not self.message_history[user_id][msg_hash]:
                del self.message_history[user_id][msg_hash]

        # Get current count for this message
        current_count = len(self.message_history[user_id][message_hash])

        # Add current message
        self.message_history[user_id][message_hash].append(now)

        # Check if loop detected
        if current_count + 1 >= self.threshold:
            logger.warning(
                f"Message loop detected for {user_id}: "
                f"'{message_text[:50]}...' sent {current_count + 1} times "
                f"in {self.window.total_seconds() / 60} minutes"
            )
            return True, {
                'user_id': user_id,
                'message_preview': message_text[:50],
                'count': current_count + 1,
                'threshold': self.threshold
            }

        return False, {
            'user_id': user_id,
            'message_preview': message_text[:50],
            'count': current_count + 1,
            'threshold': self.threshold
        }

    def reset_user(self, user_id):
        """
        Reset loop detection for a user.

        Args:
            user_id (str): User identifier
        """
        if user_id in self.message_history:
            del self.message_history[user_id]
            logger.info(f"Reset loop detection for {user_id}")

    def cleanup_old_entries(self, max_age_hours=24):
        """
        Clean up old entries to prevent memory bloat.

        Args:
            max_age_hours (int): Remove entries older than this many hours
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        users_to_remove = []

        for user_id, messages in self.message_history.items():
            for msg_hash in list(messages.keys()):
                # Remove old timestamps
                messages[msg_hash] = [
                    ts for ts in messages[msg_hash]
                    if ts > cutoff
                ]

                # Remove empty message entries
                if not messages[msg_hash]:
                    del messages[msg_hash]

            # Mark empty user entries for removal
            if not messages:
                users_to_remove.append(user_id)

        # Remove empty user entries
        for user_id in users_to_remove:
            del self.message_history[user_id]

        if users_to_remove:
            logger.info(f"Cleaned up {len(users_to_remove)} old loop detection entries")


class GlobalRateLimiter:
    """
    Global rate limiter for total server load protection.

    Limits total requests across all users to prevent server overload.
    """

    def __init__(self, max_requests=500, window_minutes=60):
        """
        Initialize global rate limiter.

        Args:
            max_requests (int): Maximum total requests allowed per window
            window_minutes (int): Time window in minutes
        """
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.request_history = []

        logger.info(
            f"Global rate limiter initialized: {max_requests} total requests "
            f"per {window_minutes} minutes"
        )

    def check_limit(self):
        """
        Check if global rate limit has been exceeded.

        Returns:
            tuple: (bool, dict) - (is_allowed, info_dict)
        """
        now = datetime.now()
        cutoff = now - self.window

        # Clean old requests
        self.request_history = [
            ts for ts in self.request_history
            if ts > cutoff
        ]

        current_count = len(self.request_history)
        remaining = max(0, self.max_requests - current_count)

        # Check if limit exceeded
        if current_count >= self.max_requests:
            logger.error(
                f"Global rate limit exceeded: {current_count}/{self.max_requests} "
                f"requests in {self.window.total_seconds() / 60} minutes"
            )
            return False, {
                'remaining': 0,
                'limit': self.max_requests,
                'current': current_count
            }

        # Add current request
        self.request_history.append(now)

        return True, {
            'remaining': remaining - 1,
            'limit': self.max_requests,
            'current': current_count + 1
        }
