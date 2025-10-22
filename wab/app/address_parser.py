#!/usr/bin/env python3
"""
Address Parser
Extracts and validates addresses from WhatsApp messages.
"""

import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AddressParser:
    """Parses addresses from text messages."""

    def __init__(self, min_addresses=2, max_addresses=26):
        """
        Initialize address parser.

        Args:
            min_addresses (int): Minimum number of addresses required
            max_addresses (int): Maximum number of addresses allowed (Google Maps limit)
        """
        self.min_addresses = min_addresses
        self.max_addresses = max_addresses

    def parse_addresses(self, message_text):
        """
        Parse addresses from message text.
        Supports multiple formats:
        - One address per line
        - Numbered addresses

        Args:
            message_text (str): Message text containing addresses

        Returns:
            tuple: (addresses_list, error_message)
                   Returns (list of addresses, None) on success
                   Returns (None, error string) on failure
        """
        try:
            if not message_text or not message_text.strip():
                return None, "Message is empty. Please send me addresses."

            # Clean the message
            text = message_text.strip()

            # Try different parsing methods
            addresses = None

            # Method 1: Line-separated addresses
            addresses = self._parse_line_separated(text)

            # Method 2: If method 1 failed, try numbered list
            if not addresses or len(addresses) < self.min_addresses:
                addresses = self._parse_numbered_list(text)

            # Validate results
            if not addresses:
                return None, "Could not find any addresses. Please send addresses one per line or as a numbered list."

            if len(addresses) < self.min_addresses:
                return None, f"I need at least {self.min_addresses} addresses to optimize a route. You provided {len(addresses)}."

            if len(addresses) > self.max_addresses:
                return None, f"Maximum {self.max_addresses} addresses allowed. You provided {len(addresses)}. Please reduce the list."

            # Clean addresses first
            cleaned_addresses = []
            for addr in addresses:
                cleaned = self._clean_address(addr)
                if cleaned:
                    cleaned_addresses.append(cleaned)

            if len(cleaned_addresses) < self.min_addresses:
                return None, f"After cleaning, only {len(cleaned_addresses)} valid addresses found. Need at least {self.min_addresses}."

            # Check for round trip (first and last address are the same)
            is_round_trip = False
            if len(cleaned_addresses) >= 2:
                first_normalized = ' '.join(cleaned_addresses[0].lower().split())
                last_normalized = ' '.join(cleaned_addresses[-1].lower().split())
                is_round_trip = first_normalized == last_normalized

            # Remove duplicates from middle waypoints only
            # If round trip: keep first, deduplicate middle, keep last
            # If not round trip: deduplicate all
            final_addresses = []
            seen_addresses = set()
            duplicates_removed = 0

            for idx, addr in enumerate(cleaned_addresses):
                normalized = ' '.join(addr.lower().split())

                # For round trips: skip duplicate check for the last address if it matches the first
                if is_round_trip and idx == len(cleaned_addresses) - 1:
                    final_addresses.append(addr)
                    logger.info(f"Round trip detected - keeping return to start: {addr}")
                elif normalized not in seen_addresses:
                    final_addresses.append(addr)
                    seen_addresses.add(normalized)
                else:
                    duplicates_removed += 1
                    logger.info(f"Removed duplicate waypoint: {addr}")

            if len(final_addresses) < self.min_addresses:
                return None, f"After removing duplicates, only {len(final_addresses)} unique addresses found. Need at least {self.min_addresses}."

            # Log success with duplicate info
            if is_round_trip:
                logger.info(f"Successfully parsed {len(final_addresses)} addresses (round trip detected)")
            elif duplicates_removed > 0:
                logger.info(f"Successfully parsed {len(final_addresses)} addresses ({duplicates_removed} duplicate(s) removed)")
            else:
                logger.info(f"Successfully parsed {len(final_addresses)} addresses")

            return final_addresses, None

        except Exception as e:
            logger.error(f"Error parsing addresses: {e}", exc_info=True)
            return None, "Error processing addresses. Please try again."

    def _parse_line_separated(self, text):
        """Parse addresses separated by newlines."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Filter out lines that are too short to be addresses
        addresses = [line for line in lines if len(line) > 5]

        return addresses if len(addresses) >= self.min_addresses else None

    def _parse_numbered_list(self, text):
        """Parse numbered list of addresses (1. Address, 2. Address, etc.)."""
        # Pattern for numbered lists: 1. or 1) or 1: or just 1
        pattern = r'^\s*\d+[\.\)\:]?\s*(.+)$'

        addresses = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            match = re.match(pattern, line)
            if match:
                addr = match.group(1).strip()
                if len(addr) > 5:
                    addresses.append(addr)

        return addresses if len(addresses) >= self.min_addresses else None

    def _clean_address(self, address):
        """
        Clean and validate a single address.

        Args:
            address (str): Address to clean

        Returns:
            str: Cleaned address, or None if invalid
        """
        if not address:
            return None

        # Remove extra whitespace
        cleaned = ' '.join(address.split())

        # Remove common prefixes from numbered lists
        cleaned = re.sub(r'^\d+[\.\)\:]\s*', '', cleaned)

        # Minimum length check
        if len(cleaned) < 5:
            return None

        # Check if it looks like an address (has some letters and numbers)
        has_letters = bool(re.search(r'[a-zA-Z]', cleaned))

        if not has_letters:
            return None

        return cleaned

    def format_addresses_for_display(self, addresses):
        """
        Format addresses for display in message.

        Args:
            addresses (list): List of addresses

        Returns:
            str: Formatted string with numbered addresses
        """
        if not addresses:
            return ""

        lines = []
        for i, addr in enumerate(addresses, 1):
            lines.append(f"{i}. {addr}")

        return '\n'.join(lines)

    def is_route_request(self, message_text):
        """
        Check if a message looks like a route optimization request.

        Args:
            message_text (str): Message text to check

        Returns:
            bool: True if message looks like a route request
        """
        if not message_text:
            return False

        text_lower = message_text.lower()

        # Keywords that indicate route request
        route_keywords = [
            'route', 'ruta', 'optimize', 'optimizar',
            'directions', 'direcciones', 'delivery', 'entrega'
        ]

        # Check for keywords
        has_keyword = any(keyword in text_lower for keyword in route_keywords)

        # Check if message has multiple lines (likely addresses)
        has_multiple_parts = '\n' in message_text

        # Check if we can parse addresses from it
        addresses, _ = self.parse_addresses(message_text)
        has_valid_addresses = addresses is not None and len(addresses) >= self.min_addresses

        # It's a route request if:
        # 1. Has route keywords OR
        # 2. Has multiple address-like parts and valid addresses
        return has_keyword or (has_multiple_parts and has_valid_addresses)
