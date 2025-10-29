#!/usr/bin/env python3
"""
Test Round Trip Consistency Between WhatsApp and Terminal
Verifies that WhatsApp bridge produces same results as terminal.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.integration.route_optimizer_bridge import route_bridge
from route_optimizer.api import optimize_route as api_optimize_route

def test_consistency():
    """Test that WhatsApp and terminal produce same results."""

    print("=" * 70)
    print("Round Trip Consistency Test")
    print("=" * 70)

    # Test Case 1: Regular route (no round trip)
    print("\n" + "=" * 70)
    print("TEST 1: Regular Route (3 addresses, no round trip)")
    print("=" * 70)

    addresses_case1 = [
        "Calle Alcalá 100, Madrid",
        "Paseo de la Castellana 50, Madrid",
        "Calle Serrano 20, Madrid"
    ]

    print("\nAddresses:")
    for i, addr in enumerate(addresses_case1, 1):
        print(f"  {i}. {addr}")

    # Terminal method (direct API call)
    print("\n--- Terminal Method (Direct API) ---")
    original_term, optimized_term = api_optimize_route(addresses_case1)
    print(f"Distance: {optimized_term['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_term['duration_s']//60} min")

    # WhatsApp method (via bridge)
    print("\n--- WhatsApp Method (Via Bridge) ---")
    result_wa = route_bridge.optimize_route(addresses_case1)
    optimized_wa = result_wa['optimized_route']
    print(f"Distance: {optimized_wa['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_wa['duration_s']//60} min")

    # Verify consistency
    if optimized_term['distance_m'] == optimized_wa['distance_m']:
        print("\n[PASS] Distances match!")
    else:
        print(f"\n[FAIL] Distance mismatch!")
        print(f"  Terminal: {optimized_term['distance_m']/1000:.2f} km")
        print(f"  WhatsApp: {optimized_wa['distance_m']/1000:.2f} km")

    # Test Case 2: Round trip
    print("\n" + "=" * 70)
    print("TEST 2: Round Trip (4 addresses, first = last)")
    print("=" * 70)

    addresses_case2 = [
        "Calle Alcalá 100, Madrid",
        "Paseo de la Castellana 50, Madrid",
        "Calle Serrano 20, Madrid",
        "Calle Alcalá 100, Madrid"  # Round trip!
    ]

    print("\nAddresses:")
    for i, addr in enumerate(addresses_case2, 1):
        print(f"  {i}. {addr}")

    # Terminal method (direct API call)
    print("\n--- Terminal Method (Direct API) ---")
    original_term2, optimized_term2 = api_optimize_route(addresses_case2)
    print(f"Distance: {optimized_term2['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_term2['duration_s']//60} min")
    print(f"Addresses: {len(optimized_term2['addresses'])}")

    # WhatsApp method (via bridge)
    print("\n--- WhatsApp Method (Via Bridge) ---")
    result_wa2 = route_bridge.optimize_route(addresses_case2)
    optimized_wa2 = result_wa2['optimized_route']
    print(f"Distance: {optimized_wa2['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_wa2['duration_s']//60} min")
    print(f"Addresses: {len(optimized_wa2['addresses'])}")

    # Verify consistency
    print("\n--- Verification ---")
    distance_match = optimized_term2['distance_m'] == optimized_wa2['distance_m']
    duration_match = optimized_term2['duration_s'] == optimized_wa2['duration_s']
    address_count_match = len(optimized_term2['addresses']) == len(optimized_wa2['addresses'])

    if distance_match:
        print("[PASS] Round trip distances match!")
    else:
        print(f"[FAIL] Round trip distance mismatch!")
        print(f"  Terminal: {optimized_term2['distance_m']/1000:.2f} km")
        print(f"  WhatsApp: {optimized_wa2['distance_m']/1000:.2f} km")

    if duration_match:
        print("[PASS] Round trip durations match!")
    else:
        print(f"[FAIL] Round trip duration mismatch!")
        print(f"  Terminal: {optimized_term2['duration_s']//60} min")
        print(f"  WhatsApp: {optimized_wa2['duration_s']//60} min")

    if address_count_match:
        print("[PASS] Address counts match!")
    else:
        print(f"[FAIL] Address count mismatch!")
        print(f"  Terminal: {len(optimized_term2['addresses'])} addresses")
        print(f"  WhatsApp: {len(optimized_wa2['addresses'])} addresses")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if distance_match and duration_match and address_count_match:
        print("✅ ALL TESTS PASSED - WhatsApp and Terminal are consistent!")
    else:
        print("❌ TESTS FAILED - Inconsistency detected")

    print("\nExpected values from user's terminal tests:")
    print("  Regular route: 8.32 km, 24 min")
    print("  Round trip:    9.64 km, 29 min")
    print()


if __name__ == '__main__':
    test_consistency()
