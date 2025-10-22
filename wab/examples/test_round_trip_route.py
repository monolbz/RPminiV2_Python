#!/usr/bin/env python3
"""
Test Round Trip Route Optimization
Full end-to-end test with Google Maps API for round trip routes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.integration.route_optimizer_bridge import route_bridge

def test_round_trip_optimization():
    """Test full route optimization with round trip."""

    print("=" * 70)
    print("Round Trip Route Optimization Test")
    print("=" * 70)

    # Round trip case
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

    print(f"[PASS] Parsed {len(addresses)} addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")

    # Verify round trip
    first_norm = ' '.join(addresses[0].lower().split())
    last_norm = ' '.join(addresses[-1].lower().split())

    if first_norm == last_norm:
        print(f"\n[PASS] Round trip confirmed - first and last address match")
        print(f"  Start: {addresses[0]}")
        print(f"  End:   {addresses[-1]}")
    else:
        print(f"\n[FAIL] Not a round trip")
        return

    if len(addresses) == 10:
        print(f"[PASS] All 10 addresses preserved (including return to start)")
    else:
        print(f"[WARN] Expected 10 addresses, got {len(addresses)}")

    print("\nStep 2: Optimize route")
    print("-" * 70)

    result = route_bridge.optimize_route(addresses)

    if not result['success']:
        print(f"[FAIL] Route optimization failed: {result['error_message']}")
        return

    print("[PASS] Route optimization successful!")

    # Check optimized route
    optimized = result['optimized_route']
    optimized_addresses = optimized['addresses']

    print(f"\nOptimized round trip route ({len(optimized_addresses)} stops):")
    for i, addr in enumerate(optimized_addresses, 1):
        print(f"  {i}. {addr}")

    # Verify round trip preserved
    first_opt_norm = ' '.join(optimized_addresses[0].lower().split())
    last_opt_norm = ' '.join(optimized_addresses[-1].lower().split())

    if first_opt_norm == last_opt_norm:
        print(f"\n[PASS] Round trip preserved in optimized route")
        print(f"  Optimized Start: {optimized_addresses[0]}")
        print(f"  Optimized End:   {optimized_addresses[-1]}")
    else:
        print(f"\n[FAIL] Round trip lost during optimization!")

    # Check route efficiency
    original_distance = result.get('original_route', {}).get('total_distance_km', 0)
    optimized_distance = optimized.get('total_distance_km', 0)
    distance_saved = original_distance - optimized_distance

    print(f"\nRoute Metrics:")
    print(f"  Original distance:  {original_distance:.2f} km")
    print(f"  Optimized distance: {optimized_distance:.2f} km")
    print(f"  Distance saved:     {distance_saved:.2f} km")

    if distance_saved >= 0:
        print(f"\n[PASS] Route optimization found efficient path")
    else:
        print(f"\n[WARN] Optimized route longer than original")

    print("\n" + "=" * 70)
    print("Round Trip Test Complete")
    print("=" * 70)
    print()


if __name__ == '__main__':
    test_round_trip_optimization()
