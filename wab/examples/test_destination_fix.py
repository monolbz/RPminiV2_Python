#!/usr/bin/env python3
"""
Test Destination Fix
Tests the fix for duplicate destination bug that was causing incorrect distances.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.integration.route_optimizer_bridge import route_bridge

def test_destination_fix():
    """Test the problematic addresses that showed wrong distance."""

    print("=" * 70)
    print("Destination Fix Test")
    print("=" * 70)

    # The problematic case from user's report
    message_text = """Paseo santa María de la cabeza, 21, Madrid
Calle Bailen 32, Madrid
Calle Jesús 2, Madrid
Avenida de Abrantes 8, Madrid
Calle de Santa Isabel 46, Madrid"""

    print("\nInput addresses:")
    for i, line in enumerate(message_text.strip().split('\n'), 1):
        print(f"{i}. {line}")

    print("\nStep 1: Parse addresses")
    print("-" * 70)
    parser = AddressParser()
    addresses, error = parser.parse_addresses(message_text)

    if error:
        print(f"[FAIL] Parsing error: {error}")
        return

    print(f"[PASS] Parsed {len(addresses)} addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")

    print("\nStep 2: Optimize route")
    print("-" * 70)

    result = route_bridge.optimize_route(addresses)

    if not result['success']:
        print(f"[FAIL] Route optimization failed: {result['error_message']}")
        return

    print("[PASS] Route optimization successful!")

    # Check routes
    original = result['original_route']
    optimized = result['optimized_route']

    print(f"\nOriginal route ({len(original['addresses'])} stops):")
    for i, addr in enumerate(original['addresses'], 1):
        print(f"  {i}. {addr}")

    print(f"\nOptimized route ({len(optimized['addresses'])} stops):")
    for i, addr in enumerate(optimized['addresses'], 1):
        print(f"  {i}. {addr}")

    # Check metrics
    original_distance_km = original['distance_m'] / 1000
    optimized_distance_km = optimized['distance_m'] / 1000
    distance_saved_km = original_distance_km - optimized_distance_km

    original_duration_min = original['duration_s'] / 60
    optimized_duration_min = optimized['duration_s'] / 60

    print("\n" + "=" * 70)
    print("Route Metrics")
    print("=" * 70)
    print(f"Original route:  {original_distance_km:.2f} km, {original_duration_min:.0f} min")
    print(f"Optimized route: {optimized_distance_km:.2f} km, {optimized_duration_min:.0f} min")
    print(f"Savings:         {distance_saved_km:.2f} km")

    # Verification checks
    print("\n" + "=" * 70)
    print("Verification")
    print("=" * 70)

    # Check 1: Distance should be reasonable (around 15km, not 60km)
    if 10 <= optimized_distance_km <= 20:
        print(f"[PASS] Distance looks reasonable: {optimized_distance_km:.2f} km")
        print(f"       (Expected: ~14.8 km from Google Maps URL)")
    else:
        print(f"[FAIL] Distance still looks wrong: {optimized_distance_km:.2f} km")
        print(f"       (Expected: ~14.8 km, NOT ~60 km)")

    # Check 2: Duration should be reasonable (around 53min, not 72min)
    if 40 <= optimized_duration_min <= 65:
        print(f"[PASS] Duration looks reasonable: {optimized_duration_min:.0f} min")
        print(f"       (Expected: ~53 min from Google Maps URL)")
    else:
        print(f"[FAIL] Duration still looks wrong: {optimized_duration_min:.0f} min")
        print(f"       (Expected: ~53 min, NOT ~72 min)")

    # Check 3: Both routes should have same number of stops (5)
    if len(original['addresses']) == len(optimized['addresses']) == 5:
        print(f"[PASS] Both routes have correct number of stops: 5")
    else:
        print(f"[FAIL] Route length mismatch:")
        print(f"       Original: {len(original['addresses'])} stops")
        print(f"       Optimized: {len(optimized['addresses'])} stops")
        print(f"       Expected: 5 stops for both")

    # Check 4: First address should be same in both routes
    if original['addresses'][0] == optimized['addresses'][0]:
        print(f"[PASS] Both routes start at same address")
    else:
        print(f"[FAIL] Routes start at different addresses")

    # Check 5: Last address should be same in both routes
    if original['addresses'][-1] == optimized['addresses'][-1]:
        print(f"[PASS] Both routes end at same address")
    else:
        print(f"[FAIL] Routes end at different addresses")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)
    print()


if __name__ == '__main__':
    test_destination_fix()
