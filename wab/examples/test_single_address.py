#!/usr/bin/env python3
"""
Test single address parsing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser

def test_single():
    parser = AddressParser()

    test_cases = [
        "Calle Mayor 1, Madrid",
        "Plaza España, Madrid",
        "Paseo de la Castellana 50, Madrid",
    ]

    for input_text in test_cases:
        print(f"\n{'='*60}")
        print(f"Input: {input_text}")
        print(f"{'='*60}")

        addresses, error = parser.parse_addresses(input_text)

        if error:
            print(f"[ERROR] {error}")
        elif addresses:
            print(f"[PARSED] {len(addresses)} addresses:")
            for i, addr in enumerate(addresses, 1):
                print(f"  {i}. {addr}")
        else:
            print("[WARN] Neither error nor addresses")

if __name__ == '__main__':
    test_single()
