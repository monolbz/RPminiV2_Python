#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test and demonstrate GDPR consent messages

Reflects the gdpr-relax flow: no blocking gate; consent is implied
when the user sends their first address list.
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.templates.consent_messages import (
    CONSENT_REVOKED,
    DATA_CONTROLLER_INFO,
)


def print_message(title, message):
    """Print a message with a nice header"""
    print("\n" + "="*80)
    print(f"📱 {title}")
    print("="*80)
    print(message)
    print()


def show_conversation_flow():
    """Show a typical conversation flow under the implied-consent model"""
    print("\n" + "="*80)
    print("💬 TYPICAL CONVERSATION FLOW (implied-consent model)")
    print("="*80)

    flow = [
        ("User",  "hola"),
        ("Bot",   "¡Hola! 🦜 Soy tu asistente de rutas... [welcome, no gate]"),
        ("User",  "/ayuda"),
        ("Bot",   "[Shows help — no gate]"),
        ("User",  "Calle Mayor 1, Madrid\nPlaza España, Madrid"),
        ("Bot",   "[Route result + 🔒 privacy footnote — consent recorded at this point]"),
        ("User",  "Calle Mayor 1, Madrid\nPlaza España, Madrid  (second route)"),
        ("Bot",   "[Route result — no footnote this time]"),
        ("User",  "/revocar"),
        ("Bot",   "[CONSENT_REVOKED message]"),
    ]

    for i, (sender, message) in enumerate(flow, 1):
        print(f"\n{i}. {sender}: {message}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🔒 GDPR CONSENT MESSAGES - DEMONSTRATION (gdpr-relax flow)")
    print("="*80)

    print_message("CONSENT REVOKED (still used by /revocar)", CONSENT_REVOKED)
    print_message("DATA CONTROLLER INFO", DATA_CONTROLLER_INFO)

    show_conversation_flow()

    print("\n" + "="*80)
    print("✅ DEMONSTRATION COMPLETE")
    print("="*80)
    print("""
NOTE: The blocking-gate consent flow has been replaced with implied consent.
Sending the first address list = consent (consent_version='2.0',
user_agent='implied:first_address_list'). A privacy footnote is appended
to the first route result. CONSENT_REVOKED is the only consent message
still in active use.
    """)
