"""
Input handling module for route optimizer.
Handles reading and validating addresses from files.
"""

import re
from pathlib import Path


def validate_address(address, line_number=None):
    """
    Validate a single address for common formatting errors.

    Args:
        address: The address string to validate
        line_number: Optional line number for error messages

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    location_prefix = f"Line {line_number}: " if line_number else ""

    # Check 1: Length validation
    if len(address) < 5:
        return False, f"{location_prefix}Address too short (minimum 5 characters): '{address}'"

    if len(address) > 200:
        return False, f"{location_prefix}Address too long (maximum 200 characters, got {len(address)})"

    # Check 2: Must contain at least some letters
    if not re.search(r'[a-zA-Z]', address):
        return False, f"{location_prefix}Address must contain letters: '{address}'"

    # Check 3: Must contain at least one digit (typical for street numbers)
    if not re.search(r'\d', address):
        return False, f"{location_prefix}Address should contain a street number: '{address}'"

    # Check 4: Cannot be only special characters and numbers
    # Remove all letters, digits, and common address punctuation
    cleaned = re.sub(r'[a-zA-Z0-9\s,.\-/]', '', address)
    if len(cleaned) > len(address) * 0.3:  # More than 30% special chars
        return False, f"{location_prefix}Address contains too many special characters: '{address}'"

    # Check 5: Detect suspicious patterns (repeated characters)
    # Check for 5+ consecutive identical characters
    if re.search(r'(.)\1{4,}', address):
        return False, f"{location_prefix}Address contains suspicious repeated characters: '{address}'"

    # Check 6: Must not be only whitespace (already handled by strip, but double-check)
    if not address.strip():
        return False, f"{location_prefix}Address cannot be empty or only whitespace"

    return True, None


def read_addresses_from_file(filename='input.txt'):
    """
    Read addresses from a text file.

    Args:
        filename: Path to the input file (default: 'input.txt')

    Returns:
        List of addresses (strings)

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is empty, has less than 2 addresses,
                   more than 26 addresses, or contains duplicates
    """
    filepath = Path(filename)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file '{filename}' not found")

    addresses = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace and skip empty lines
            line = line.strip()
            if line:
                # Validate address format before adding
                is_valid, error_msg = validate_address(line, line_num)
                if not is_valid:
                    raise ValueError(f"Invalid address format:\n{error_msg}")

                addresses.append(line)

    if len(addresses) < 2:
        raise ValueError(f"Input file must contain at least 2 addresses (found {len(addresses)})")

    if len(addresses) > 26:
        raise ValueError(
            f"Input file cannot contain more than 26 addresses (found {len(addresses)}). "
            f"Google Maps API supports a maximum of 25 waypoints plus 1 origin."
        )

    # Check for duplicate addresses (case-insensitive, whitespace-normalized)
    normalized_addresses = {}
    duplicates = []

    for i, addr in enumerate(addresses, 1):
        # Normalize: lowercase and strip extra whitespace
        normalized = ' '.join(addr.lower().split())

        if normalized in normalized_addresses:
            # Found duplicate
            original_line = normalized_addresses[normalized]
            duplicates.append(f"  - Line {original_line}: {addresses[original_line - 1]}")
            duplicates.append(f"  - Line {i}: {addr}")
        else:
            normalized_addresses[normalized] = i

    if duplicates:
        duplicates_str = '\n'.join(duplicates)
        raise ValueError(f"Duplicate addresses found in input file:\n{duplicates_str}")

    return addresses
