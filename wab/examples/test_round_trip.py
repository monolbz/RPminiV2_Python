#!/usr/bin/env python3
"""
Test Round Trip Support
Tests that first and last address can be the same (round trip)
while middle waypoints cannot have duplicates.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_round_trip_scenarios():
    """Test various round trip and duplicate scenarios."""

    parser = AddressParser()

    print("=" * 70)
    print("TEST 1: Valid Round Trip (First and Last Same)")
    print("=" * 70)

    test_input_1 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89
Calle del General Pardiñas 45"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_1.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 5 addresses (first and last are same)")

    addresses, error = parser.parse_addresses(test_input_1)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should keep all 5 for round trip):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 5:
            print(f"\n[PASS] Round trip preserved - all 5 addresses kept")
        else:
            print(f"\n[FAIL] Expected 5 addresses, got {len(addresses)}")

        # Check first and last are same
        first_norm = ' '.join(addresses[0].lower().split())
        last_norm = ' '.join(addresses[-1].lower().split())
        if first_norm == last_norm:
            print(f"[PASS] First and last addresses match (round trip confirmed)")
        else:
            print(f"[FAIL] First and last addresses don't match!")

    print("\n" + "=" * 70)
    print("TEST 2: Duplicate in Middle Waypoints (Should Remove)")
    print("=" * 70)

    test_input_2 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle Santa Engracia 79
Calle de López de Hoyos 89
Calle del General Pardiñas 45"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_2.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 6 addresses (positions 2 and 4 are duplicates)")

    addresses, error = parser.parse_addresses(test_input_2)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should remove duplicate at position 4, keep round trip):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 5:
            print(f"\n[PASS] Removed 1 duplicate from middle, kept round trip (6 -> 5)")
        else:
            print(f"\n[FAIL] Expected 5 addresses, got {len(addresses)}")

        # Verify no duplicates in middle waypoints
        middle_waypoints = addresses[1:-1]  # Exclude first and last
        middle_normalized = [' '.join(addr.lower().split()) for addr in middle_waypoints]
        if len(middle_normalized) == len(set(middle_normalized)):
            print(f"[PASS] No duplicates in middle waypoints")
        else:
            print(f"[FAIL] Still has duplicates in middle waypoints!")

    print("\n" + "=" * 70)
    print("TEST 3: No Round Trip, Just Duplicate Last (Should Remove)")
    print("=" * 70)

    test_input_3 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89
Calle de López de Hoyos 89"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_3.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 5 addresses (last is duplicate of 4th, not first)")

    addresses, error = parser.parse_addresses(test_input_3)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should remove duplicate - NOT a round trip):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 4:
            print(f"\n[PASS] Removed duplicate (5 -> 4)")
        else:
            print(f"\n[FAIL] Expected 4 addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("TEST 4: Case Insensitive Round Trip")
    print("=" * 70)

    test_input_4 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
CALLE DEL GENERAL PARDIÑAS 45"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_4.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 4 addresses (first and last are same, different case)")

    addresses, error = parser.parse_addresses(test_input_4)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should recognize as round trip despite case difference):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 4:
            print(f"\n[PASS] Case-insensitive round trip works (4 addresses kept)")
        else:
            print(f"\n[FAIL] Expected 4 addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("TEST 5: Multiple Middle Duplicates with Round Trip")
    print("=" * 70)

    test_input_5 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle Santa Engracia 79
Calle de López de Hoyos 89
Calle de Bravo Murillo 185
Calle de Diego de León 47
Calle del General Pardiñas 45"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_5.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 8 addresses (positions 2,4 and 3,6 are duplicates)")

    addresses, error = parser.parse_addresses(test_input_5)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should remove 2 middle duplicates, keep round trip):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 6:
            print(f"\n[PASS] Removed 2 middle duplicates, kept round trip (8 -> 6)")
        else:
            print(f"\n[FAIL] Expected 6 addresses, got {len(addresses)}")

        # Verify round trip preserved
        first_norm = ' '.join(addresses[0].lower().split())
        last_norm = ' '.join(addresses[-1].lower().split())
        if first_norm == last_norm:
            print(f"[PASS] Round trip still preserved after cleaning")
        else:
            print(f"[FAIL] Round trip lost!")

    print("\n" + "=" * 70)
    print("TEST 6: No Duplicates at All (Normal Route)")
    print("=" * 70)

    test_input_6 = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de López de Hoyos 89"""

    print("\nInput addresses:")
    for i, line in enumerate(test_input_6.strip().split('\n'), 1):
        print(f"{i}. {line}")
    print(f"\nTotal: 4 addresses (all unique)")

    addresses, error = parser.parse_addresses(test_input_6)

    if error:
        print(f"\n[FAIL] Error: {error}")
    else:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses")
        print("\nResult (should keep all 4):")
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")

        if len(addresses) == 4:
            print(f"\n[PASS] All unique addresses preserved")
        else:
            print(f"\n[FAIL] Expected 4 addresses, got {len(addresses)}")

    print("\n" + "=" * 70)
    print("All Tests Complete")
    print("=" * 70)
    print()


if __name__ == '__main__':
    test_round_trip_scenarios()
