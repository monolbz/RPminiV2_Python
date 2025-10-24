#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test and demonstrate GDPR consent messages

This script shows how the consent messages look and tests keyword detection.
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.templates.consent_messages import (
    CONSENT_REQUEST,
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_REVOKED,
    CONSENT_ALREADY_GIVEN,
    CONSENT_REQUIRED_FOR_ROUTE,
    PENDING_CONSENT_RESPONSE,
    DATA_CONTROLLER_INFO,
    get_consent_keywords
)

def print_message(title, message):
    """Print a message with a nice header"""
    print("\n" + "="*80)
    print(f"📱 {title}")
    print("="*80)
    print(message)
    print()

def test_keyword_detection():
    """Test consent keyword detection"""
    print("\n" + "="*80)
    print("🔍 TESTING CONSENT KEYWORD DETECTION")
    print("="*80)

    keywords = get_consent_keywords()

    test_inputs = [
        # Accept variations
        ("acepto", "accept"),
        ("Acepto", "accept"),
        ("ACEPTO", "accept"),
        ("Si", "accept"),
        ("sí", "accept"),
        ("ok", "accept"),
        ("vale", "accept"),
        ("de acuerdo", "accept"),
        ("consiento", "accept"),
        ("autorizo", "accept"),
        ("yes", "accept"),

        # Reject variations
        ("no acepto", "reject"),
        ("No acepto", "reject"),
        ("rechazo", "reject"),
        ("no", "reject"),
        ("no quiero", "reject"),
        ("cancelar", "reject"),

        # Ambiguous/unclear
        ("hola", None),
        ("ayuda", None),
        ("que es esto", None),
    ]

    print("\n✅ ACCEPT keywords:")
    for word in keywords['accept']:
        print(f"   • {word}")

    print("\n❌ REJECT keywords:")
    for word in keywords['reject']:
        print(f"   • {word}")

    print("\n📝 Testing user inputs:")
    for user_input, expected_type in test_inputs:
        user_lower = user_input.lower()

        # Check if it matches accept
        is_accept = any(kw in user_lower for kw in keywords['accept'])

        # Check if it matches reject
        is_reject = any(kw in user_lower for kw in keywords['reject'])

        if is_accept:
            result = "✅ ACCEPT"
        elif is_reject:
            result = "❌ REJECT"
        else:
            result = "❓ UNCLEAR"

        status = "✓" if ((is_accept and expected_type == "accept") or
                        (is_reject and expected_type == "reject") or
                        (not is_accept and not is_reject and expected_type is None)) else "✗"

        print(f"{status} '{user_input}' → {result}")

def show_conversation_flow():
    """Show a typical conversation flow"""
    print("\n" + "="*80)
    print("💬 TYPICAL CONVERSATION FLOW")
    print("="*80)

    flow = [
        ("User", "/ayuda"),
        ("Bot", "[Shows help message]"),
        ("Bot", "⚠️ Se requiere consentimiento..."),
        ("User", "Reads message, types: acepto"),
        ("Bot", "✅ ¡Gracias por tu consentimiento!"),
        ("User", "Calle Mayor 1, Madrid\nPlaza España, Madrid"),
        ("Bot", "[Processes route and returns optimization]"),
    ]

    for i, (sender, message) in enumerate(flow, 1):
        print(f"\n{i}. {sender}: {message}")

def check_gdpr_compliance():
    """Check that messages contain required GDPR elements"""
    print("\n" + "="*80)
    print("✅ GDPR COMPLIANCE CHECK")
    print("="*80)

    required_elements = {
        "Purpose of processing": ["optimizar", "calcular", "rutas"],
        "Data collected": ["direcciones", "número de teléfono"],
        "Retention period": ["24 horas", "3 años"],
        "Right to access": ["/mydata", "acceso"],
        "Right to erasure": ["/deletedata", "supresión"],
        "Right to revoke": ["/revokeconsent", "retirar", "revoca"],
        "Data protection": ["seguras", "HTTPS", "RGPD"],
        "Third parties": ["terceros"],
    }

    print("\n📋 Checking CONSENT_REQUEST message:\n")

    for element, keywords in required_elements.items():
        found = any(kw.lower() in CONSENT_REQUEST.lower() for kw in keywords)
        status = "✓" if found else "✗"
        keyword_str = ", ".join(keywords)
        print(f"{status} {element}: {keyword_str}")

        if not found:
            print(f"   ⚠️  WARNING: '{element}' not clearly mentioned!")

def estimate_message_length():
    """Estimate WhatsApp message character counts"""
    print("\n" + "="*80)
    print("📏 MESSAGE LENGTH ANALYSIS")
    print("="*80)

    messages = {
        "CONSENT_REQUEST": CONSENT_REQUEST,
        "CONSENT_ACCEPTED": CONSENT_ACCEPTED,
        "CONSENT_DECLINED": CONSENT_DECLINED,
        "CONSENT_REVOKED": CONSENT_REVOKED,
    }

    print("\nWhatsApp message limits:")
    print("  • Recommended: < 1000 characters (fits on one screen)")
    print("  • Maximum: 4096 characters (WhatsApp limit)")
    print()

    for name, message in messages.items():
        length = len(message)
        status = "✓" if length < 1000 else "⚠️" if length < 4096 else "✗"
        print(f"{status} {name}: {length} characters")

        if length > 1000:
            print(f"   ⚠️  Long message - user needs to scroll")
        if length > 4096:
            print(f"   ✗ TOO LONG - exceeds WhatsApp limit!")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🔒 GDPR CONSENT MESSAGES - DEMONSTRATION")
    print("="*80)

    # Show all messages
    print_message("1. CONSENT REQUEST (Initial)", CONSENT_REQUEST)
    print_message("2. CONSENT ACCEPTED", CONSENT_ACCEPTED)
    print_message("3. CONSENT DECLINED", CONSENT_DECLINED)
    print_message("4. CONSENT REVOKED", CONSENT_REVOKED)
    print_message("5. CONSENT ALREADY GIVEN",
                  CONSENT_ALREADY_GIVEN.format(consent_date="24 de octubre de 2025"))
    print_message("6. CONSENT REQUIRED FOR ROUTE", CONSENT_REQUIRED_FOR_ROUTE)
    print_message("7. PENDING CONSENT RESPONSE", PENDING_CONSENT_RESPONSE)
    print_message("8. DATA CONTROLLER INFO", DATA_CONTROLLER_INFO)

    # Test keyword detection
    test_keyword_detection()

    # Show typical flow
    show_conversation_flow()

    # Check GDPR compliance
    check_gdpr_compliance()

    # Estimate message lengths
    estimate_message_length()

    print("\n" + "="*80)
    print("✅ DEMONSTRATION COMPLETE")
    print("="*80)
    print("""
📝 NEXT STEPS:

1. Review the consent messages above
2. Ensure they fit your business needs
3. Fill in the placeholders:
   - [TU_NOMBRE_O_EMPRESA]
   - [TU_EMAIL_DE_CONTACTO]
   - [TU_NIF_O_CIF]
   - etc.

4. Consider having a Spanish lawyer review the texts
5. Test in real WhatsApp environment
6. Implement ConsentManager to store consent records

⚠️  IMPORTANT:
These messages are a starting point. For full legal compliance,
consult with a lawyer specialized in Spanish/EU data protection law.
    """)
