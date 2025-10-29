#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test for Spanish road types and ZIP code pattern.
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.app.address_parser import AddressParser, SPANISH_ROAD_TYPES
from wab.app.message_processor import MessageProcessor

parser = AddressParser()
processor = MessageProcessor()

def test_input(description, input_text, expected):
    """Test an input and show result"""
    addresses, error = parser.parse_addresses(input_text)
    is_fallback = (addresses is None and error is None)

    result = "FALLBACK" if is_fallback else "ADDRESS"
    status = "✓" if (expected == "FALLBACK" and is_fallback) or (expected == "ADDRESS" and not is_fallback) else "✗"

    print(f"{status} {result:10} | {description:40} | '{input_text}'")

    return status == "✓"

print("="*100)
print("COMPREHENSIVE TEST: Spanish Road Types + ZIP Codes")
print("="*100)

# Section 1: Gibberish with numbers (should trigger fallback)
print("\n" + "="*100)
print("SECTION 1: Gibberish with numbers → Should trigger FALLBACK")
print("="*100)

tests = [
    ("Random gibberish + number", "asdf123", "FALLBACK"),
    ("Number + gibberish", "123test", "FALLBACK"),
    ("Words with number", "hello123world", "FALLBACK"),
    ("Mixed alphanumeric", "abc456def", "FALLBACK"),
    ("Test with space and number", "test 123", "FALLBACK"),
    ("Random sentence with number", "I have 5 apples", "FALLBACK"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 2: Spanish road types (should be treated as address)
print("\n" + "="*100)
print("SECTION 2: Spanish road types → Should be ADDRESS ATTEMPT")
print("="*100)

tests = [
    ("CALLE", "Calle Mayor", "ADDRESS"),
    ("AVENIDA", "Avenida Principal", "ADDRESS"),
    ("PLAZA", "Plaza España", "ADDRESS"),
    ("PASEO", "Paseo de la Castellana", "ADDRESS"),
    ("CARRETERA", "Carretera Nacional", "ADDRESS"),
    ("GLORIETA", "Glorieta de Bilbao", "ADDRESS"),
    ("VIA", "Via Augusta", "ADDRESS"),
    ("CAMINO", "Camino Real", "ADDRESS"),
    ("Mixed case", "calle mayor", "ADDRESS"),
    ("Uppercase", "CALLE MAYOR", "ADDRESS"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 3: Spanish ZIP codes (should be treated as address)
print("\n" + "="*100)
print("SECTION 3: Spanish ZIP codes → Should be ADDRESS ATTEMPT")
print("="*100)

tests = [
    ("Madrid ZIP", "28001", "ADDRESS"),
    ("Barcelona ZIP", "08001", "ADDRESS"),
    ("Valencia ZIP", "46001", "ADDRESS"),
    ("Sevilla ZIP", "41001", "ADDRESS"),
    ("Madrid + city", "28013 Madrid", "ADDRESS"),
    ("High ZIP (valid)", "52999", "ADDRESS"),
    ("Low ZIP (valid)", "01000", "ADDRESS"),
    ("Invalid ZIP (too high)", "53000", "FALLBACK"),  # Province 53 doesn't exist
    ("Invalid ZIP (starts with 00)", "00123", "FALLBACK"),
    ("Random 5 digits", "99999", "FALLBACK"),  # Not a valid Spanish ZIP
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 4: City names (should be treated as address)
print("\n" + "="*100)
print("SECTION 4: City names → Should be ADDRESS ATTEMPT")
print("="*100)

tests = [
    ("Madrid", "madrid", "ADDRESS"),
    ("Barcelona", "barcelona", "ADDRESS"),
    ("Valencia", "valencia", "ADDRESS"),
    ("Sevilla", "sevilla", "ADDRESS"),
    ("Bilbao", "bilbao", "ADDRESS"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 5: English addresses (should still work)
print("\n" + "="*100)
print("SECTION 5: English addresses → Should be ADDRESS ATTEMPT")
print("="*100)

tests = [
    ("Street", "123 Main Street", "ADDRESS"),
    ("Avenue", "Park Avenue", "ADDRESS"),
    ("Road", "Oxford Road", "ADDRESS"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 6: Commas and newlines (should be treated as address)
print("\n" + "="*100)
print("SECTION 6: Commas and newlines → Should be ADDRESS ATTEMPT")
print("="*100)

tests = [
    ("With comma", "test, test", "ADDRESS"),
    ("Multiple lines", "line1\nline2", "ADDRESS"),
    ("Comma + text", "Madrid, España", "ADDRESS"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Section 7: Real-world scenarios
print("\n" + "="*100)
print("SECTION 7: Real-world scenarios")
print("="*100)

tests = [
    ("Full Spanish address", "Calle Mayor 1, 28013 Madrid", "ADDRESS"),
    ("Simple Spanish address", "Plaza España, Madrid", "ADDRESS"),
    ("Address with ZIP only", "28001 Madrid", "ADDRESS"),
    ("Random question", "what time is it", "FALLBACK"),
    ("Random statement", "hello how are you", "FALLBACK"),
    ("Number in sentence", "I need 3 pizzas", "FALLBACK"),
    ("Mixed gibberish", "asdf qwerty 123", "FALLBACK"),
]

passed = sum(test_input(desc, inp, exp) for desc, inp, exp in tests)
print(f"\nPassed: {passed}/{len(tests)}")

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"""
Total Spanish road types: {len(SPANISH_ROAD_TYPES)}
Road types list: {', '.join(SPANISH_ROAD_TYPES[:10])}...

Address indicators now include:
  ✓ Spanish road types (29 types: CALLE, AVENIDA, PLAZA, etc.)
  ✓ Spanish ZIP codes (01000-52999)
  ✓ City names (madrid, barcelona, valencia, sevilla, bilbao)
  ✓ English road types (street, avenue, road)
  ✓ Commas (,)
  ✓ Multiple lines (\\n)

Removed:
  ✗ Generic number check (was causing false positives)

Benefits:
  • "asdf123" → Now shows fallback instead of address error
  • "Calle Mayor" → Still detected as address attempt
  • "28013 Madrid" → Detected via ZIP code pattern
  • More accurate for Spanish users
  • Fewer false positives
""")
