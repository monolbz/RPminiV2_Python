#!/usr/bin/env python3
"""
Test Duplicate Address Fix
Tests the address parser's duplicate detection and removal.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_duplicate_removal():
    """Test that duplicate addresses are properly removed."""

    parser = AddressParser()

    print("=" * 70)
    print("TEST 1: Duplicate First and Last Address")
    print("=" * 70)

    # The problematic case from user's bug report
    test_input_1 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de Bravo Murillo 156
Calle de Martínez Izquierdo 74
Calle de López de Hoyos 89
Calle de Diego de León 47
Calle de Almagro 32
Calle de Príncipe de Vergara 56
Calle del General Pardiñas 45"""

    print("\nInput addresses:")
    print(test_input_1)
    print(f"\nTotal addresses in input: 10")

    addresses, error = parser.parse_addresses(test_input_1)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} unique addresses")
        print("\nCleaned addresses (duplicates removed):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        # Verify no duplicates
        normalized_set = set(' '.join(addr.lower().split()) for addr in addresses)
        if len(normalized_set) == len(addresses):
            print(f"\n[PASS] No duplicates in output (verified)")
        else:
            print(f"\n[FAIL] Still has duplicates!")

    print("\n" + "=" * 70)
    print("TEST 2: Multiple Duplicates")
    print("=" * 70)

    test_input_2 = """Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle Santa Engracia 79
Calle de López de Hoyos 89
Calle de Diego de León 47
Calle de Diego de León 47"""

    print("\nInput addresses:")
    print(test_input_2)
    print(f"\nTotal addresses in input: 6 (3 unique)")

    addresses, error = parser.parse_addresses(test_input_2)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} unique addresses")
        print("\nCleaned addresses (duplicates removed):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 3:
            print(f"\n[PASS] Correctly reduced 6 addresses to 3 unique ones")
        else:
            print(f"\n[FAIL] Expected 3 unique addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("TEST 3: Case Insensitive Duplicate Detection")
    print("=" * 70)

    test_input_3 = """Calle Santa Engracia 79
CALLE SANTA ENGRACIA 79
Calle de Bravo Murillo 185"""

    print("\nInput addresses (different case):")
    print(test_input_3)

    addresses, error = parser.parse_addresses(test_input_3)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} unique addresses")
        print("\nCleaned addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 2:
            print(f"\n[PASS] Case-insensitive duplicate detection works")
        else:
            print(f"\n[FAIL] Expected 2 unique addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("TEST 4: No Duplicates (Normal Case)")
    print("=" * 70)

    test_input_4 = """Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89"""

    print("\nInput addresses (all unique):")
    print(test_input_4)

    addresses, error = parser.parse_addresses(test_input_4)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nCleaned addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 3:
            print(f"\n[PASS] No false positives - all unique addresses preserved")
        else:
            print(f"\n[FAIL] Expected 3 addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("All Tests Complete")
    print("=" * 70)
    print()


if __name__ == '__main__':
    test_duplicate_removal()
