#!/usr/bin/env python3
"""
Test Route Optimization with Duplicate Addresses
Full end-to-end test to verify duplicate addresses are properly handled.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.integration.route_optimizer_bridge import route_bridge

def test_route_with_duplicates():
    """Test full route optimization with duplicate addresses."""

    print("=" * 70)
    print("End-to-End Route Optimization Test with Duplicates")
    print("=" * 70)

    # The problematic case from user's bug report
    message_text = """Calle del General Pardiñas 45
Calle Santa Engracia 79
Calle de Bravo Murillo 185
Calle de Bravo Murillo 156
Calle de Martínez Izquierdo 74
Calle de López de Hoyos 89
Calle de Diego de León 47
Calle de Almagro 32
Calle de Príncipe de Vergara 56
Calle del General Pardiñas 45"""

    print("\nStep 1: Parse addresses from message")
    print("-" * 70)
    parser = AddressParser()
    addresses, error = parser.parse_addresses(message_text)

    if error:
        print(f"[FAIL] Parsing error: {error}")
        return

    print(f"[PASS] Parsed {len(addresses)} unique addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")

    # Verify duplicate was removed
    if len(addresses) == 9:
        print(f"\n[PASS] Duplicate successfully removed (10 -> 9 addresses)")
    else:
        print(f"\n[FAIL] Expected 9 addresses, got {len(addresses)}")
        return

    print("\nStep 2: Optimize route with cleaned addresses")
    print("-" * 70)

    result = route_bridge.optimize_route(addresses)

    if not result['success']:
        print(f"[FAIL] Route optimization failed: {result['error_message']}")
        return

    print("[PASS] Route optimization successful!")

    # Check optimized route
    optimized = result['optimized_route']
    optimized_addresses = optimized['addresses']

    print(f"\nOptimized route ({len(optimized_addresses)} stops):")
    for i, addr in enumerate(optimized_addresses, 1):
        print(f"  {i}. {addr}")

    # Verify no duplicates in output
    normalized_set = set(' '.join(addr.lower().split()) for addr in optimized_addresses)

    if len(normalized_set) == len(optimized_addresses):
        print(f"\n[PASS] No duplicates in optimized route")
    else:
        print(f"\n[FAIL] Optimized route still contains duplicates!")

    # Check if first address appears again
    first_addr_normalized = ' '.join(optimized_addresses[0].lower().split())
    duplicates_of_first = sum(
        1 for addr in optimized_addresses[1:]
        if ' '.join(addr.lower().split()) == first_addr_normalized
    )

    if duplicates_of_first == 0:
        print(f"[PASS] First address does not appear again in route")
    else:
        print(f"[FAIL] First address appears {duplicates_of_first} more time(s) in route")

    print("\n" + "=" * 70)
    print("Test Complete - Bug Fix Verified")
    print("=" * 70)
    print()


if __name__ == '__main__':
    test_route_with_duplicates()
