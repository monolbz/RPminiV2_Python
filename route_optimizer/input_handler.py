"""
Input handling module for route optimizer.
Handles reading and validating addresses from files.
"""

from pathlib import Path


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
        for line in f:
            # Strip whitespace and skip empty lines
            line = line.strip()
            if line:
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
