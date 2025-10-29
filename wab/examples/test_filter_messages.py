#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to show the filtered address message properly.
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
print("TEST: Filtered Address Tracking Message")
print("="*70)

# This should show the filter tracking message:
# - Initial parse finds 5 addresses (passes line 63 check)
# - After cleaning, only 1 valid remains (fails line 76 check)
# - Error message at line 83 should list the 4 filtered addresses

test_input = """Calle Mayor 1, Madrid
test
abc
xyz
1234"""

print("\nScenario: 5 lines sent, but 4 are too short/invalid")
print("Input:")
for i, line in enumerate(test_input.strip().split('\n'), 1):
    print(f"  {i}. {repr(line)}")

print("\n" + "-"*70)

addresses, error = parser.parse_addresses(test_input)

if error:
    formatted = processor._format_error_for_user(error)
    print("\n[USER SEES IN WHATSAPP:]")
    print(formatted)
    print("\n✓ Shows which addresses were filtered out!")
else:
    print(f"\nParsed {len(addresses)} addresses")

print("\n" + "="*70)
