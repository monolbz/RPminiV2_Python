#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Route Integration
Tests the route optimizer integration without WhatsApp.
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.integration.route_optimizer_bridge import route_bridge


def test_address_parsing():
    """Test address parsing with various formats."""
    print("\n" + "=" * 60)
    print("TEST 1: Address Parsing")
    print("=" * 60)

    parser = AddressParser()

    test_messages = [
        # Line-separated
        """Calle Mayor 1, Madrid
Plaza España, Madrid
Gran Via 50, Madrid""",

        # Comma-separated
        "Calle Mayor 1 Madrid, Plaza España Madrid, Gran Via 50 Madrid",

        # Numbered list
        """1. Calle Mayor 1, Madrid
2. Plaza España, Madrid
3. Gran Via 50, Madrid"""
    ]

    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Test Message {i} ---")
        print(f"Input:\n{msg}\n")

        addresses, error = parser.parse_addresses(msg)

        if error:
            print(f"[FAIL] Error: {error}")
        else:
            print(f"[PASS] Parsed {len(addresses)} addresses:")
            for j, addr in enumerate(addresses, 1):
                print(f"  {j}. {addr}")


def test_route_request_detection():
    """Test detecting route requests."""
    print("\n" + "=" * 60)
    print("TEST 2: Route Request Detection")
    print("=" * 60)

    parser = AddressParser()

    test_cases = [
        ("Hello!", False),
        ("Help me optimize a route", True),
        ("Calle Mayor 1\nPlaza España\nGran Via", True),
        ("Thanks", False),
        ("ruta Madrid", True),
    ]

    for msg, expected in test_cases:
        is_route = parser.is_route_request(msg)
        status = "[PASS]" if is_route == expected else "[FAIL]"
        print(f"{status} '{msg[:30]}...' -> {is_route} (expected {expected})")


def test_route_optimization():
    """Test actual route optimization."""
    print("\n" + "=" * 60)
    print("TEST 3: Route Optimization")
    print("=" * 60)

    addresses = [
        "Puerta del Sol, Madrid",
        "Plaza Mayor, Madrid",
        "Palacio Real, Madrid"
    ]

    print(f"\nOptimizing route with {len(addresses)} addresses:")
    for i, addr in enumerate(addresses, 1):
        print(f"  {i}. {addr}")

    print("\nCalling route optimizer...")
    result = route_bridge.optimize_route(addresses)

    if result['success']:
        print("\n[SUCCESS] Optimization succeeded!")
        print(f"\nFormatted result:\n")
        formatted = route_bridge.format_route_result_for_whatsapp(result)
        print(formatted)
    else:
        print(f"\n[FAIL] Optimization failed: {result['error_message']}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WhatsApp Route Integration Test Suite")
    print("=" * 60)

    try:
        test_address_parsing()
        test_route_request_detection()

        # Only test optimization if user confirms (uses API)
        response = input("\n\nTest actual route optimization? This will use Google Maps API. (y/n): ")

        if response.lower() == 'y':
            test_route_optimization()
        else:
            print("\nSkipping route optimization test.")

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error during tests: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Tests Complete")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
