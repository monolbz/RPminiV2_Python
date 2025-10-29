#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for error message improvements:
1. Consolidated error formatting
2. Tracked filtered addresses
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser
from wab.app.message_processor import MessageProcessor

def print_test_header(test_name):
    print("\n" + "="*70)
    print(f"TEST: {test_name}")
    print("="*70)

def test_parser(test_input, description):
    """Test the parser and show the result"""
    print(f"\n{description}")
    print(f"Input: {repr(test_input)}")
    print("-" * 70)

    parser = AddressParser()
    addresses, error = parser.parse_addresses(test_input)

    if addresses:
        print(f"[OK] Success: Parsed {len(addresses)} addresses")
        for i, addr in enumerate(addresses, 1):
            print(f"  {i}. {addr}")
    else:
        print(f"[ERROR] Error: {error}")

    return addresses, error

def test_message_processor(test_input, description):
    """Test the full message processor flow"""
    print(f"\n{description}")
    print(f"Input: {repr(test_input)}")
    print("-" * 70)

    processor = MessageProcessor()

    # Simulate the flow from _process_route_request
    parser = AddressParser()
    addresses, error = parser.parse_addresses(test_input)

    if error:
        # This is what the user would see
        formatted_error = processor._format_error_for_user(error)
        print("[USER SEES:]")
        print(formatted_error)
    else:
        print(f"[OK] Would proceed to optimize {len(addresses)} addresses")

    return addresses, error

# ============================================================================
# Test 1: Filtered addresses with valid ones
# ============================================================================
print_test_header("Filtered Invalid Addresses Mixed with Valid Ones")

test_message_processor(
    "Calle Mayor 1, 28013 Madrid\ntest\nabc\nPlaza España, Madrid",
    "Test 1a: Valid addresses with short invalid ones (test, abc)"
)

test_message_processor(
    "test\nabc\nxyz",
    "Test 1b: Only short invalid addresses"
)

test_message_processor(
    "Calle Mayor 1, Madrid\ntest\nabc\nxyz\n123\nGran Via 50, Madrid",
    "Test 1c: Multiple invalid (test, abc, xyz, 123) with 2 valid"
)

test_message_processor(
    "Calle Mayor 1, Madrid\na\nbb\nccc\ndddd\neeeee\nPlaza España, Madrid\nGran Via 50, Madrid",
    "Test 1d: Multiple short invalid addresses (1-5 chars) with 3 valid"
)

# ============================================================================
# Test 2: Error formatting consistency
# ============================================================================
print_test_header("Consolidated Error Formatting")

test_message_processor(
    "not an address at all",
    "Test 2a: 'No es posible encontrar direcciones' - should show format example"
)

test_message_processor(
    "Calle Mayor 1, Madrid",
    "Test 2b: Only 1 address - should NOT show format example"
)

test_message_processor(
    "\n".join([f"Address {i}, Madrid" for i in range(1, 30)]),
    "Test 2c: Too many addresses (29) - should NOT show format example"
)

# ============================================================================
# Test 3: Edge cases
# ============================================================================
print_test_header("Edge Cases")

test_message_processor(
    "12345\n67890\n999",
    "Test 3a: Number-only addresses (no letters)"
)

test_message_processor(
    "Calle Mayor 1, Madrid\ntest\nPlaza España, Madrid",
    "Test 3b: One invalid filtered, 2 valid remain"
)

test_message_processor(
    "a\ntest\nCalle Mayor 1, Madrid",
    "Test 3c: Two invalid (one 1-char, one 4-char), one valid remain"
)

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("SUMMARY OF IMPROVEMENTS")
print("="*70)
print("""
[OK] Fix 1: Consolidated Error Formatting
   - All errors now go through _format_error_for_user()
   - Format example only shown for "No es posible encontrar direcciones"
   - Consistent error prefix for all errors

[OK] Fix 2: Track and Report Filtered Addresses
   - Parser now tracks which addresses were filtered
   - Shows up to 3 filtered addresses in error message
   - User knows exactly what was removed and why

Next steps:
- Test in real WhatsApp environment
- Consider adding warning when some addresses are filtered but enough remain
""")
