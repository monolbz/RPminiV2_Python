#!/usr/bin/env python3
"""
Test Address Parser Error Cases
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_error_cases():
    parser = AddressParser()

    test_cases = [
        ("Empty message", ""),
        ("Only spaces", "   "),
        ("Single short word", "abc"),
        ("Only numbers", "12345"),
        ("One address only", "Calle Mayor 1, Madrid"),
        ("Too many addresses", "\n".join([f"Address {i}" for i in range(30)])),
        ("Only special chars", "!@#$%^&*()"),
        ("Random gibberish", "asdfghjkl qwertyuiop"),
    ]

    for test_name, input_text in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"Input: '{input_text[:50]}...' " if len(input_text) > 50 else f"Input: '{input_text}'")

        addresses, error = parser.parse_addresses(input_text)

        if error:
            print(f"[ERROR] {error}")
        elif addresses:
            print(f"[PASS] Parsed {len(addresses)} addresses (no error):")
            for addr in addresses:
                print(f"  - {addr}")
        else:
            print("[WARN] Neither error nor addresses returned")

if __name__ == '__main__':
    test_error_cases()
