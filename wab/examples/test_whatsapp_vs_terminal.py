#!/usr/bin/env python3
"""
Test WhatsApp vs Terminal Consistency
Compare results from WhatsApp bridge vs direct terminal optimizer.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.integration.route_optimizer_bridge import route_bridge
from route_optimizer.api import optimize_route as api_optimize_route

def compare_routes(addresses, test_name):
    """Compare WhatsApp and Terminal results for given addresses."""

    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print("=" * 70)

    print("\nInput addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")

    # Terminal method (direct API call - same as run_optimizer.py)
    print("\n--- TERMINAL METHOD (run_optimizer.py) ---")
    original_term, optimized_term = api_optimize_route(addresses)

    print(f"Addresses in result: {len(optimized_term['addresses'])}")
    for i, addr in enumerate(optimized_term['addresses'], 1):
        print(f"  {i}. {addr}")
    print(f"Distance: {optimized_term['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_term['duration_s']//60} min {optimized_term['duration_s']%60} sec")

    # WhatsApp method (via bridge - same as WhatsApp uses)
    print("\n--- WHATSAPP METHOD (via bridge) ---")
    result_wa = route_bridge.optimize_route(addresses)

    if not result_wa['success']:
        print(f"ERROR: {result_wa['error_message']}")
        return False

    optimized_wa = result_wa['optimized_route']

    print(f"Addresses in result: {len(optimized_wa['addresses'])}")
    for i, addr in enumerate(optimized_wa['addresses'], 1):
        print(f"  {i}. {addr}")
    print(f"Distance: {optimized_wa['distance_m']/1000:.2f} km")
    print(f"Duration: {optimized_wa['duration_s']//60} min {optimized_wa['duration_s']%60} sec")

    # Compare results
    print("\n--- COMPARISON ---")

    all_match = True

    # Distance
    if optimized_term['distance_m'] == optimized_wa['distance_m']:
        print(f"[PASS] Distance matches: {optimized_term['distance_m']/1000:.2f} km")
    else:
        print(f"[FAIL] Distance mismatch!")
        print(f"  Terminal: {optimized_term['distance_m']/1000:.2f} km")
        print(f"  WhatsApp: {optimized_wa['distance_m']/1000:.2f} km")
        print(f"  Difference: {abs(optimized_term['distance_m'] - optimized_wa['distance_m'])/1000:.2f} km")
        all_match = False

    # Duration
    if optimized_term['duration_s'] == optimized_wa['duration_s']:
        print(f"[PASS] Duration matches: {optimized_term['duration_s']//60} min")
    else:
        print(f"[FAIL] Duration mismatch!")
        print(f"  Terminal: {optimized_term['duration_s']//60} min {optimized_term['duration_s']%60} sec")
        print(f"  WhatsApp: {optimized_wa['duration_s']//60} min {optimized_wa['duration_s']%60} sec")
        print(f"  Difference: {abs(optimized_term['duration_s'] - optimized_wa['duration_s'])} seconds")
        all_match = False

    # Address count
    if len(optimized_term['addresses']) == len(optimized_wa['addresses']):
        print(f"[PASS] Address count matches: {len(optimized_term['addresses'])}")
    else:
        print(f"[FAIL] Address count mismatch!")
        print(f"  Terminal: {len(optimized_term['addresses'])} addresses")
        print(f"  WhatsApp: {len(optimized_wa['addresses'])} addresses")
        all_match = False

    # Address order
    addresses_match = True
    for i, (term_addr, wa_addr) in enumerate(zip(optimized_term['addresses'], optimized_wa['addresses']), 1):
        if term_addr != wa_addr:
            print(f"[FAIL] Address {i} mismatch!")
            print(f"  Terminal: {term_addr}")
            print(f"  WhatsApp: {wa_addr}")
            addresses_match = False
            all_match = False

    if addresses_match and len(optimized_term['addresses']) == len(optimized_wa['addresses']):
        print(f"[PASS] All addresses match in same order")

    return all_match


def main():
    print("=" * 70)
    print("WhatsApp vs Terminal Consistency Test")
    print("=" * 70)
    print()
    print("This test compares results from:")
    print("  1. Terminal: Direct call to optimize_route() (same as run_optimizer.py)")
    print("  2. WhatsApp: Via route_bridge (same as WhatsApp interface)")
    print()
    print("Both should produce IDENTICAL results.")

    all_tests_passed = True

    # Test 1: Simple 3-address route
    test1_passed = compare_routes(
        [
            "Calle Alcalá 100, Madrid",
            "Paseo de la Castellana 50, Madrid",
            "Calle Serrano 20, Madrid"
        ],
        "Simple Route (3 addresses)"
    )
    all_tests_passed = all_tests_passed and test1_passed

    # Test 2: Round trip (4 addresses, first = last)
    test2_passed = compare_routes(
        [
            "Calle Alcalá 100, Madrid",
            "Paseo de la Castellana 50, Madrid",
            "Calle Serrano 20, Madrid",
            "Calle Alcalá 100, Madrid"
        ],
        "Round Trip (4 addresses, first = last)"
    )
    all_tests_passed = all_tests_passed and test2_passed

    # Test 3: Longer route (5 addresses)
    test3_passed = compare_routes(
        [
            "Plaza Mayor, Madrid",
            "Puerta del Sol, Madrid",
            "Gran Vía 50, Madrid",
            "Retiro Park, Madrid",
            "Atocha Station, Madrid"
        ],
        "Longer Route (5 addresses)"
    )
    all_tests_passed = all_tests_passed and test3_passed

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    if all_tests_passed:
        print("\n[PASS] ALL TESTS PASSED!")
        print("WhatsApp and Terminal produce IDENTICAL results.")
        print("The bug fix is working correctly.")
    else:
        print("\n[FAIL] SOME TESTS FAILED!")
        print("There are still discrepancies between WhatsApp and Terminal.")
        print("Please review the differences above.")

    print()


if __name__ == '__main__':
    main()
