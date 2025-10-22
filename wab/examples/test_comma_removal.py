#!/usr/bin/env python3
"""
Test Comma-Separated Format Removal
Verify that comma-separated addresses are no longer supported.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_comma_removal():
    """Test that comma-separated format is no longer supported."""

    parser = AddressParser()

    print("=" * 70)
    print("Comma-Separated Format Removal Test")
    print("=" * 70)

    # Test 1: Line-separated (should work)
    print("\n" + "=" * 70)
    print("TEST 1: Line-Separated Format (SHOULD WORK)")
    print("=" * 70)

    input_1 = """Calle Mayor 14, Madrid
Plaza España, Madrid
Gran Via 50, Madrid"""

    print("\nInput:")
    print(input_1)

    addresses, error = parser.parse_addresses(input_1)

    if addresses:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")
    else:
        print(f"\n[FAIL] Error: {error}")

    # Test 2: Numbered list (should work)
    print("\n" + "=" * 70)
    print("TEST 2: Numbered List Format (SHOULD WORK)")
    print("=" * 70)

    input_2 = """1. Calle Mayor 14, Madrid
2. Plaza España, Madrid
3. Gran Via 50, Madrid"""

    print("\nInput:")
    print(input_2)

    addresses, error = parser.parse_addresses(input_2)

    if addresses:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")
    else:
        print(f"\n[FAIL] Error: {error}")

    # Test 3: Comma-separated (should fail)
    print("\n" + "=" * 70)
    print("TEST 3: Comma-Separated Format (SHOULD FAIL)")
    print("=" * 70)

    input_3 = "Calle Mayor 14 Madrid, Plaza España Madrid, Gran Via 50 Madrid"

    print("\nInput:")
    print(input_3)

    addresses, error = parser.parse_addresses(input_3)

    if error:
        print(f"\n[PASS] Correctly rejected comma-separated format!")
        print(f"Error message: {error}")
    else:
        print(f"\n[FAIL] Should have rejected, but parsed {len(addresses)} addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")

    # Test 4: Ambiguous case - addresses with commas in them (line-separated)
    print("\n" + "=" * 70)
    print("TEST 4: Addresses with Commas (Line-Separated) (SHOULD WORK)")
    print("=" * 70)

    input_4 = """Calle Mayor, 14, 28013 Madrid
Plaza España, 5, 28008 Madrid
Gran Via, 50, 28013 Madrid"""

    print("\nInput:")
    print(input_4)

    addresses, error = parser.parse_addresses(input_4)

    if addresses:
        print(f"\n[PASS] Successfully parsed {len(addresses)} addresses:")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")
        print("\nNote: Each address preserves its internal commas ✓")
    else:
        print(f"\n[FAIL] Error: {error}")

    # Test 5: Single line with commas (should fail - ambiguous)
    print("\n" + "=" * 70)
    print("TEST 5: Single Line with Multiple Commas (SHOULD FAIL)")
    print("=" * 70)

    input_5 = "Calle Mayor, 14, 28013 Madrid, Plaza España, 5, 28008 Madrid"

    print("\nInput:")
    print(input_5)

    addresses, error = parser.parse_addresses(input_5)

    if error:
        print(f"\n[PASS] Correctly rejected ambiguous comma-separated input!")
        print(f"Error message: {error}")
    else:
        print(f"\n[WARN] Parsed {len(addresses)} addresses (might be false positive):")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\n✓ Line-separated format: SUPPORTED")
    print("✓ Numbered list format: SUPPORTED")
    print("✗ Comma-separated format: NO LONGER SUPPORTED")
    print("\nThis prevents ambiguity when addresses contain commas.")
    print()


if __name__ == '__main__':
    test_comma_removal()
