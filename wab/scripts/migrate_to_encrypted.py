#!/usr/bin/env python3
"""
Data Migration Script: Plain to Encrypted
Migrates existing JSON files to use hashed phone numbers.

This script:
1. Backs up existing files
2. Converts phone number keys to hashed keys
3. Preserves all other data (timestamps, metadata)
4. Creates backup before modifying original

Usage:
    python wab/scripts/migrate_to_encrypted.py

Safety:
    - Creates .backup files before modifying
    - Can be run multiple times (idempotent)
    - Skips already-encrypted data
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


def backup_file(file_path):
    """Create a backup of the file before migration."""
    if not file_path.exists():
        return None

    backup_path = file_path.with_suffix(f'.json.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')

    with open(file_path, 'r') as f:
        data = f.read()

    with open(backup_path, 'w') as f:
        f.write(data)

    print(f"  [BACKUP] Created: {backup_path}")
    return backup_path


def migrate_sessions_file(file_path, encryptor):
    """
    Migrate sessions.json to use hashed phone numbers.

    Before: {"+34644252886": "2025-11-17T08:50:19.226032"}
    After:  {"phone_d2d767c177a41064": "2025-11-17T08:50:19.226032"}
    """
    print(f"\n[MIGRATE] Processing: {file_path}")

    if not file_path.exists():
        print(f"  [SKIP] File does not exist")
        return False

    # Load current data
    with open(file_path, 'r') as f:
        data = json.load(f)

    if not data:
        print(f"  [SKIP] File is empty")
        return False

    # Check if already encrypted
    first_key = list(data.keys())[0]
    if encryptor.is_hashed_key(first_key):
        print(f"  [SKIP] Already encrypted (key format: {first_key})")
        return False

    # Create backup
    backup_file(file_path)

    # Migrate data
    print(f"  [PROCESS] Migrating {len(data)} entries...")
    migrated_data = {}
    migration_count = 0

    for phone_number, timestamp in data.items():
        try:
            # Hash the phone number
            hashed_key = encryptor.hash_phone(phone_number)
            migrated_data[hashed_key] = timestamp
            migration_count += 1
            print(f"    {phone_number} -> {hashed_key}")
        except Exception as e:
            print(f"    [ERROR] Failed to migrate {phone_number}: {e}")

    # Save migrated data
    with open(file_path, 'w') as f:
        json.dump(migrated_data, f, indent=2)

    print(f"  [SUCCESS] Migrated {migration_count}/{len(data)} entries")
    return True


def migrate_consents_file(file_path, encryptor):
    """
    Migrate user_consents.json to use hashed phone numbers.

    Before: {
        "+34644252886": {
            "consent_given": true,
            "consent_date": "2025-11-14T10:30:00"
        }
    }

    After: {
        "phone_d2d767c177a41064": {
            "consent_given": true,
            "consent_date": "2025-11-14T10:30:00"
        }
    }
    """
    print(f"\n[MIGRATE] Processing: {file_path}")

    if not file_path.exists():
        print(f"  [SKIP] File does not exist")
        return False

    # Load current data
    with open(file_path, 'r') as f:
        data = json.load(f)

    if not data:
        print(f"  [SKIP] File is empty")
        return False

    # Check if already encrypted
    first_key = list(data.keys())[0]
    if encryptor.is_hashed_key(first_key):
        print(f"  [SKIP] Already encrypted (key format: {first_key})")
        return False

    # Create backup
    backup_file(file_path)

    # Migrate data
    print(f"  [PROCESS] Migrating {len(data)} entries...")
    migrated_data = {}
    migration_count = 0

    for phone_number, consent_data in data.items():
        try:
            # Hash the phone number
            hashed_key = encryptor.hash_phone(phone_number)
            # Preserve all consent metadata
            migrated_data[hashed_key] = consent_data
            migration_count += 1
            print(f"    {phone_number} -> {hashed_key}")
        except Exception as e:
            print(f"    [ERROR] Failed to migrate {phone_number}: {e}")

    # Save migrated data
    with open(file_path, 'w') as f:
        json.dump(migrated_data, f, indent=2)

    print(f"  [SUCCESS] Migrated {migration_count}/{len(data)} entries")
    return True


def main():
    """Main migration function."""
    print("=" * 70)
    print("Data Migration: Plain Phone Numbers -> Hashed Keys")
    print("=" * 70)

    try:
        # Initialize encryptor
        print("\n[INIT] Initializing encryptor...")
        encryptor = DataEncryptor()
        print("[OK] Encryptor ready")

        # Find files to migrate
        base_dir = Path(__file__).parent.parent
        sessions_file = base_dir / 'data' / 'sessions.json'
        consents_file = base_dir / 'storage' / 'user_consents.json'

        # Migrate sessions
        migrated_sessions = migrate_sessions_file(sessions_file, encryptor)

        # Migrate consents
        migrated_consents = migrate_consents_file(consents_file, encryptor)

        # Summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Sessions file: {'MIGRATED' if migrated_sessions else 'SKIPPED'}")
        print(f"Consents file: {'MIGRATED' if migrated_consents else 'SKIPPED'}")

        if migrated_sessions or migrated_consents:
            print("\n[OK] Migration completed successfully!")
            print("\nIMPORTANT:")
            print("1. Backup files created with timestamp suffix")
            print("2. Original files now use hashed keys")
            print("3. Keep ENCRYPTION_KEY in .env safe - needed to decrypt")
            print("4. Backups can be deleted after verifying migration worked")
        else:
            print("\n[INFO] No migration needed - files already encrypted or don't exist")

        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
