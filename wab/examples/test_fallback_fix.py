#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the fallback message fix for gibberish inputs.
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

parser = AddressParser()
processor = MessageProcessor()

def test_input(description, input_text, expected_result):
    """Test an input and show what happens"""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Input: '{input_text}'")

    addresses, error = parser.parse_addresses(input_text)

    print(f"\nParser returns:")
    print(f"  addresses: {addresses}")
    print(f"  error: {error}")

    # What message_processor would do
    if addresses or error:
        print(f"\n[Route to _process_route_request()]")
        if error:
            formatted = processor._format_error_for_user(error)
            print(f"User sees:\n{formatted}")
    else:
        print(f"\n[Route to FALLBACK at line 136]")
        print(f"User sees: 'Gracias por tu mensaje... No entendí lo que me dijiste'")

    # Check expectation
    is_fallback = (addresses is None and error is None)
    if expected_result == "fallback":
        if is_fallback:
            print("\n✓ PASS - Triggers fallback as expected")
        else:
            print("\n✗ FAIL - Should trigger fallback but didn't")
    else:
        if not is_fallback:
            print("\n✓ PASS - Shows error message as expected")
        else:
            print("\n✗ FAIL - Should show error but triggered fallback")

print("="*70)
print("TESTING FALLBACK FIX - GIBBERISH vs GENUINE ADDRESS ATTEMPTS")
print("="*70)

# SHOULD TRIGGER FALLBACK (NO ADDRESS INDICATORS)
print("\n" + "="*70)
print("SECTION 1: Inputs that SHOULD trigger fallback")
print("="*70)

test_input("Random gibberish", "asdfasdf", "fallback")
test_input("Random words", "hello world", "fallback")
test_input("Random phrase", "testing testing", "fallback")
test_input("Single word", "supercalifragilisticexpialidocious", "fallback")
test_input("Lowercase gibberish", "qwerty", "fallback")
test_input("Mixed case gibberish", "AbCdEfG", "fallback")

# SHOULD SHOW ERROR (HAS ADDRESS INDICATORS)
print("\n" + "="*70)
print("SECTION 2: Inputs that SHOULD show address error (genuine attempts)")
print("="*70)

test_input("Has street keyword", "Calle Mayor", "error")
test_input("Has numbers", "123 Main", "error")
test_input("Has comma", "Madrid, España", "error")
test_input("Has multiple lines", "Address 1\nAddress 2", "error")
test_input("Has 'plaza' keyword", "plaza central", "error")
test_input("Has 'madrid' keyword", "madrid", "error")
test_input("Has 'barcelona' keyword", "barcelona city", "error")

# EDGE CASES
print("\n" + "="*70)
print("SECTION 3: Edge cases")
print("="*70)

test_input("Number only", "12345", "error")  # Has numbers -> error
test_input("Comma only", "test, test", "error")  # Has comma -> error
test_input("Multiple gibberish lines", "asdf\nqwerty\nzxcv", "error")  # Has newlines -> error

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
The fix adds a check for "address indicators" before attempting to parse.

Address indicators:
  - Multiple lines (contains \\n)
  - Contains numbers (\\d)
  - Contains commas (,)
  - Contains address keywords (calle, avenida, plaza, street, etc.)

If NONE of these indicators are present, the parser returns (None, None)
which triggers the fallback message "No entendí lo que me dijiste".

This prevents single-word gibberish like "asdfasdf" from being treated
as address attempts while still catching genuine (but incomplete) attempts
like "Calle Mayor" or "123 Main".
""")
