#!/usr/bin/env python3
"""
Encrypted Data Inspector
Utility to inspect and verify encrypted data files.

This script helps you:
1. View hashed phone number keys
2. Verify which phone number corresponds to which hash
3. Check encryption status of files
4. Validate data integrity

Usage:
    # View sessions file
    python wab/scripts/inspect_encrypted_data.py --sessions

    # View consents file
    python wab/scripts/inspect_encrypted_data.py --consents

    # Check if specific phone is in system
    python wab/scripts/inspect_encrypted_data.py --find +34644252886

    # Show all
    python wab/scripts/inspect_encrypted_data.py --all
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wab.utils.encryption import DataEncryptor
from dotenv import load_dotenv

# Load .env for encryption key
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


def inspect_sessions(encryptor):
    """Inspect sessions.json file."""
    file_path = Path(__file__).parent.parent / 'data' / 'sessions.json'

    print("\n" + "=" * 70)
    print("SESSIONS FILE")
    print("=" * 70)
    print(f"File: {file_path}")

    if not file_path.exists():
        print("[INFO] File does not exist")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    print(f"Total sessions: {len(data)}")

    if not data:
        print("[INFO] No sessions found")
        return

    # Check if encrypted
    first_key = list(data.keys())[0]
    is_encrypted = encryptor.is_hashed_key(first_key)

    print(f"Encryption status: {'ENCRYPTED' if is_encrypted else 'PLAIN TEXT'}")
    print("\nSessions:")
    print("-" * 70)

    for key, timestamp in data.items():
        if is_encrypted:
            print(f"  Hashed key: {key}")
            print(f"  Timestamp:  {timestamp}")
            # Show when it expires
            try:
                ts_time = datetime.fromisoformat(timestamp)
                now = datetime.now()
                diff = now - ts_time
                hours_ago = diff.total_seconds() / 3600
                print(f"  Age:        {hours_ago:.1f} hours ago")
            except:
                pass
            print()
        else:
            print(f"  Phone:     {key}")
            print(f"  Timestamp: {timestamp}")
            print()


def inspect_consents(encryptor):
    """Inspect user_consents.json file."""
    file_path = Path(__file__).parent.parent / 'storage' / 'user_consents.json'

    print("\n" + "=" * 70)
    print("CONSENTS FILE")
    print("=" * 70)
    print(f"File: {file_path}")

    if not file_path.exists():
        print("[INFO] File does not exist")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    print(f"Total consents: {len(data)}")

    if not data:
        print("[INFO] No consents found")
        return

    # Check if encrypted
    first_key = list(data.keys())[0]
    is_encrypted = encryptor.is_hashed_key(first_key)

    print(f"Encryption status: {'ENCRYPTED' if is_encrypted else 'PLAIN TEXT'}")
    print("\nConsent records:")
    print("-" * 70)

    for key, consent_data in data.items():
        if is_encrypted:
            print(f"  Hashed key: {key}")
        else:
            print(f"  Phone: {key}")

        print(f"  Consent given: {consent_data.get('consent_given', 'N/A')}")
        print(f"  Date: {consent_data.get('consent_date', 'N/A')}")
        print(f"  Withdrawn: {consent_data.get('consent_withdrawn', False)}")
        print()


def find_phone(encryptor, phone_number):
    """Find if a phone number exists in the system."""
    print("\n" + "=" * 70)
    print(f"SEARCHING FOR: {phone_number}")
    print("=" * 70)

    # Hash the phone number
    hashed_key = encryptor.hash_phone(phone_number)
    print(f"Hashed key: {hashed_key}")

    # Check sessions
    sessions_file = Path(__file__).parent.parent / 'data' / 'sessions.json'
    if sessions_file.exists():
        with open(sessions_file, 'r') as f:
            sessions = json.load(f)

        if hashed_key in sessions:
            print(f"\n[FOUND] In sessions.json")
            print(f"  Last message: {sessions[hashed_key]}")
        else:
            print(f"\n[NOT FOUND] Not in sessions.json")

    # Check consents
    consents_file = Path(__file__).parent.parent / 'storage' / 'user_consents.json'
    if consents_file.exists():
        with open(consents_file, 'r') as f:
            consents = json.load(f)

        if hashed_key in consents:
            print(f"\n[FOUND] In user_consents.json")
            consent_data = consents[hashed_key]
            print(f"  Consent: {consent_data.get('consent_given', 'N/A')}")
            print(f"  Date: {consent_data.get('consent_date', 'N/A')}")
        else:
            print(f"\n[NOT FOUND] Not in user_consents.json")


def main():
    """Main inspection function."""
    print("\n" + "=" * 70)
    print("ENCRYPTED DATA INSPECTOR")
    print("=" * 70)

    try:
        # Initialize encryptor
        encryptor = DataEncryptor()

        # Parse command line arguments
        if len(sys.argv) == 1 or '--help' in sys.argv:
            print("\nUsage:")
            print("  python wab/scripts/inspect_encrypted_data.py --sessions")
            print("      View sessions file")
            print("\n  python wab/scripts/inspect_encrypted_data.py --consents")
            print("      View consents file")
            print("\n  python wab/scripts/inspect_encrypted_data.py --find +34644252886")
            print("      Find specific phone number")
            print("\n  python wab/scripts/inspect_encrypted_data.py --all")
            print("      Show everything")
            return

        if '--sessions' in sys.argv or '--all' in sys.argv:
            inspect_sessions(encryptor)

        if '--consents' in sys.argv or '--all' in sys.argv:
            inspect_consents(encryptor)

        if '--find' in sys.argv:
            idx = sys.argv.index('--find')
            if idx + 1 < len(sys.argv):
                phone = sys.argv[idx + 1]
                find_phone(encryptor, phone)
            else:
                print("\n[ERROR] --find requires a phone number argument")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Inspection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
