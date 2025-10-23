#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to demonstrate the current issue with number-containing gibberish.
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

print("="*70)
print("CURRENT ISSUE: Number-containing gibberish treated as address attempt")
print("="*70)

test_cases = [
    ("asdf123", "Gibberish with number"),
    ("123test", "Number + gibberish"),
    ("hello123world", "Words with number"),
    ("abc456def", "Mixed alphanumeric gibberish"),
    ("test 123", "Gibberish with space and number"),
]

for input_text, description in test_cases:
    print(f"\n{'-'*70}")
    print(f"Test: {description}")
    print(f"Input: '{input_text}'")

    addresses, error = parser.parse_addresses(input_text)

    print(f"Result: addresses={addresses}, error={error}")

    if addresses or error:
        print("→ Treated as ADDRESS ATTEMPT (because has numbers)")
        if error:
            print(f"   User sees: {error}")
    else:
        print("→ Triggers FALLBACK")

print("\n" + "="*70)
print("PROBLEM:")
print("="*70)
print("""
Any text with a number is treated as an address attempt, even if it's
clearly not an address (like "asdf123" or "hello123world").

This shows confusing error messages to users who send random text that
happens to contain a number.
""")
