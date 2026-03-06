#!/usr/bin/env python3
"""
Address Parser
Extracts and validates addresses from WhatsApp messages.
"""

import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Spanish road types for address detection
SPANISH_ROAD_TYPES = [
    'ALAMEDA', 'AVENIDA', 'CALLE', 'CAMINO', 'COSTANILLA', 'COLONIA',
    'CARRERA', 'CARRETERA', 'ESTRADA', 'GLORIETA', 'MANZANA', 'PASEO',
    'PLAZOLETA', 'PLAZA', 'POLÍGONO', 'PASILLO', 'PASAJE', 'PARQUE',
    'PLAZUELA', 'RAMAL', 'RAMBLA', 'RONDA', 'RIBERA', 'TRANSVERSAL',
    'TRAVESÍA', 'URBANIZACIÓN', 'VIA', 'ZONA'
]


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
                return None, "Mensaje vacío. Por favor, envíame las direcciones."

            # Clean the message
            text = message_text.strip()

            # Check if this looks like an address input attempt
            # Require at least ONE strong indicator to avoid treating gibberish as addresses
            has_multiple_lines = '\n' in text
            has_commas = ',' in text

            # Check for Spanish road types (case-insensitive)
            text_upper = text.upper()
            has_spanish_road_type = any(road_type in text_upper for road_type in SPANISH_ROAD_TYPES)

            # Check for Spanish ZIP code pattern (01000-52999)
            # First 2 digits: province code 01-52
            # Last 3 digits: any number 000-999
            has_spanish_zipcode = bool(re.search(r'\b(0[1-9]|[1-4][0-9]|5[0-2])\d{3}\b', text))

            # Check for common city names and English road types (for international addresses)
            address_keywords = ['madrid', 'barcelona', 'valencia', 'sevilla', 'bilbao',
                               'street', 'avenue', 'road']
            has_keywords = any(keyword in text.lower() for keyword in address_keywords)

            # If no indicators present, this is probably not an address attempt
            # Return (None, None) to trigger fallback message in message_processor
            if not (has_multiple_lines or has_commas or has_spanish_road_type or
                    has_spanish_zipcode or has_keywords):
                logger.info(f"Text lacks address indicators, returning None to trigger fallback")
                return None, None

            # Try different parsing methods
            addresses = None

            # Method 1: Line-separated addresses
            addresses = self._parse_line_separated(text)

            # Method 2: If method 1 failed, try numbered list
            if not addresses:
                addresses = self._parse_numbered_list(text)

            # Validate results
            if not addresses:
                return None, "No fue posible encontrar las direcciones. Por favor ingrésalas en el formato correcto."

            if len(addresses) < self.min_addresses or len(addresses) > self.max_addresses:
                return None, f"Recuerda ingresar entre {self.min_addresses} y {self.max_addresses} direcciones. Has enviado {len(addresses)}."

            # Clean addresses and track filtered ones
            cleaned_addresses = []
            filtered_addresses = []
            for addr in addresses:
                cleaned = self._clean_address(addr)
                if cleaned:
                    cleaned_addresses.append(cleaned)
                else:
                    filtered_addresses.append(addr)

            if len(cleaned_addresses) < self.min_addresses:
                # Build error message with info about filtered addresses
                if filtered_addresses:
                    # Show up to 3 filtered addresses
                    filtered_sample = ', '.join([f'"{a}"' for a in filtered_addresses[:3]])
                    if len(filtered_addresses) > 3:
                        filtered_sample += f" (y {len(filtered_addresses) - 3} más)"
                    return None, f"Después de verificar, solo {len(cleaned_addresses)} direcciones válidas encontradas. Se eliminaron: {filtered_sample}. Necesitas al menos {self.min_addresses} direcciones válidas."
                else:
                    return None, f"Después de verificar, solo {len(cleaned_addresses)} direcciones válidas encontradas. Necesitas al menos {self.min_addresses}."

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
                return None, f"Tras eliminar duplicados, solo quedan {len(final_addresses)} direcciones únicas. Necesitas al menos {self.min_addresses}."

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
            return None, "Error al procesar las direcciones. Por favor, inténtalo de nuevo."

    def _parse_line_separated(self, text):
        """Parse addresses separated by newlines."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Filter out lines that are too short to be addresses
        addresses = [line for line in lines if len(line) > 5]

        return addresses if len(addresses) > 0 else None

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

        return addresses if len(addresses) > 0 else None

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
