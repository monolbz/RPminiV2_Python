#!/usr/bin/env python3
"""
Test mixed valid and invalid addresses
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_mixed():
    parser = AddressParser()

    test_cases = [
        ("test with valid", "Calle Mayor 1, Madrid\ntest\nPlaza España, Madrid"),
        ("abc with valid", "Calle Mayor 1, Madrid\nabc\nPlaza España, Madrid"),
        ("1 with valid", "Calle Mayor 1, Madrid\n1\nPlaza España, Madrid"),
        ("xyz with valid", "Calle Mayor 1, Madrid\nxyz\nPlaza España, Madrid"),
        ("ojaouyn with valid", "Calle Mayor 1, Madrid\nojaouyn\nPlaza España, Madrid"),
        ("6taouyhg with valid", "Calle Mayor 1, Madrid\n6taouyhg\nPlaza España, Madrid"),
    ]

    for test_name, input_text in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"Input:")
        for line in input_text.split('\n'):
            print(f"  {line}")

        addresses, error = parser.parse_addresses(input_text)

        if error:
            print(f"\n[ERROR] {error}")
        elif addresses:
            print(f"\n[PARSED] {len(addresses)} addresses:")
            for i, addr in enumerate(addresses, 1):
                print(f"  {i}. {addr}")
        else:
            print("\n[WARN] Neither error nor addresses")

if __name__ == '__main__':
    test_mixed()
