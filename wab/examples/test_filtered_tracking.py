#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Specific test to demonstrate filtered address tracking.
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

print("="*70)
print("TESTING FILTERED ADDRESS TRACKING")
print("="*70)

processor = MessageProcessor()
parser = AddressParser()

# Test case: One valid address + multiple invalid ones
# This should trigger the filtered address error message
test_input = """Calle Mayor 1, Madrid
test
abc
xyz
123"""

print("\nInput:")
print(test_input)
print("\n" + "-"*70)

addresses, error = parser.parse_addresses(test_input)

if error:
    formatted_error = processor._format_error_for_user(error)
    print("\nUser would see:")
    print(formatted_error)
else:
    print(f"\nSuccess: {len(addresses)} addresses parsed")

print("\n" + "="*70)

# Test case 2: Zero valid + multiple invalid
test_input2 = """test
abc
xyz
ab"""

print("\nInput 2:")
print(test_input2)
print("\n" + "-"*70)

addresses2, error2 = parser.parse_addresses(test_input2)

if error2:
    formatted_error2 = processor._format_error_for_user(error2)
    print("\nUser would see:")
    print(formatted_error2)
else:
    print(f"\nSuccess: {len(addresses2)} addresses parsed")

print("\n" + "="*70)

# Test case 3: Multiple valid addresses with some filtered
test_input3 = """Calle Mayor 1, Madrid
test
Plaza España, Madrid
abc
Gran Via 50, Madrid"""

print("\nInput 3:")
print(test_input3)
print("\n" + "-"*70)

addresses3, error3 = parser.parse_addresses(test_input3)

if error3:
    formatted_error3 = processor._format_error_for_user(error3)
    print("\nUser would see:")
    print(formatted_error3)
else:
    print(f"\nSuccess: {len(addresses3)} addresses parsed")
    print("Note: Invalid addresses 'test' and 'abc' were silently filtered")
    print("(They don't appear in final list, but no error shown since we have enough valid ones)")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
The filtering tracker now shows users WHICH addresses were removed
when the count drops below minimum after cleaning.

When enough valid addresses remain (>=2), filtering happens silently
which is acceptable - users get their route and can see what addresses
were used in the output.
""")
