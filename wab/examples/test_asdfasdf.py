#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to trace what happens with "asdfasdf"
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

parser = AddressParser()

print("="*70)
print("TRACING: What happens with 'asdfasdf'?")
print("="*70)

test_input = "asdfasdf"

print(f"\nInput: '{test_input}'")
print(f"Length: {len(test_input)} characters")
print(f"Has letters: Yes")
print(f"Has numbers: No")

print("\n" + "-"*70)
print("STEP-BY-STEP TRACE:")
print("-"*70)

# Step 1: _parse_line_separated
print("\nStep 1: _parse_line_separated()")
print(f"  - Splits by newline: ['{test_input}']")
print(f"  - Filters len > 5: ['{test_input}'] (8 chars > 5) ✓")
print(f"  - Returns: ['{test_input}']")

# Step 2: Check if addresses is None
print("\nStep 2: Check 'if not addresses'")
print(f"  - addresses = ['{test_input}']")
print(f"  - 'if not addresses' = False (has 1 item)")
print(f"  - Skips _parse_numbered_list()")

# Step 3: Check if addresses is None
print("\nStep 3: Check 'if not addresses' (line 60)")
print(f"  - addresses = ['{test_input}']")
print(f"  - 'if not addresses' = False")
print(f"  - Continues to line 63...")

# Step 4: Check count
print("\nStep 4: Check address count (line 63)")
print(f"  - len(addresses) = 1")
print(f"  - min_addresses = 2")
print(f"  - 1 < 2 = True")
print(f"  - Returns error: 'Recuerda ingresar entre 2 y 26 direcciones. Has enviado 1.'")

print("\n" + "="*70)
print("RESULT:")
print("="*70)

addresses, error = parser.parse_addresses(test_input)

print(f"\naddresses: {addresses}")
print(f"error: {error}")

print("\n" + "="*70)
print("THE PROBLEM:")
print("="*70)
print("""
"asdfasdf" is 8 characters long and has letters, so:
1. _parse_line_separated() accepts it (len > 5)
2. Parser returns error: "Recuerda ingresar entre 2 y 26 direcciones..."
3. message_processor sees error is not None
4. Line 119: 'if addresses or error:' = True
5. Routes to _process_route_request() which shows the error

EXPECTED BEHAVIOR:
"asdfasdf" should return (None, None) so it triggers the fallback
message "No entendí lo que me dijiste".

CURRENT BEHAVIOR:
"asdfasdf" returns (None, "Recuerda...") which is treated as a
route request attempt.
""")
