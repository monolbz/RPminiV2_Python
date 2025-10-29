# Data Retention Automation Setup

## Overview

This document explains how to set up automated data retention cleanup to comply with GDPR requirements.

## Retention Periods

| Data Type | Retention Period | Method |
|-----------|-----------------|---------|
| User addresses | 24 hours | Automatic deletion after route optimization |
| Session data | 24 hours | Automatic cleanup |
| Consent records | 3 years | `ConsentManager.cleanup_expired_records()` |

## Automated Cleanup

### 1. Consent Records Cleanup (Required)

The `ConsentManager` class has a `cleanup_expired_records()` method that deletes consent records older than 3 years.

**Location:** `wab/app/consent_manager.py`

**Method:**
```python
def cleanup_expired_records(self) -> int:
    """
    Delete consent records older than CONSENT_RETENTION_YEARS (3 years).
    Called by scheduled job.

    Returns:
        int: Number of records deleted
    """
```

### 2. Setup Options

#### Option A: Windows Task Scheduler (Recommended for Windows)

1. Create a Python script `cleanup_task.py`:

```python
#!/usr/bin/env python3
"""
Daily cleanup task for GDPR compliance
Run this via Windows Task Scheduler or cron
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wab.app.consent_manager import ConsentManager
from wab.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Run daily cleanup tasks"""
    consent_manager = ConsentManager()

    # Clean up expired consent records (older than 3 years)
    deleted_count = consent_manager.cleanup_expired_records()
    logger.info(f"Cleaned up {deleted_count} expired consent records")

    print(f"✅ Cleanup complete. Deleted {deleted_count} expired records.")

if __name__ == "__main__":
    main()
```

2. Create a Windows Task Scheduler task:
   - Open Task Scheduler
   - Create Basic Task
   - Name: "GDPR Data Cleanup"
   - Trigger: Daily at 2:00 AM
   - Action: Start a program
   - Program: `python` or `C:\path\to\python.exe`
   - Arguments: `C:\path\to\cleanup_task.py`
   - Finish

#### Option B: Linux/Mac Cron Job

1. Create the same `cleanup_task.py` script above

2. Add to crontab:
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * /usr/bin/python3 /path/to/cleanup_task.py >> /var/log/gdpr_cleanup.log 2>&1
```

#### Option C: Manual Execution

If you have low user volume, you can run the cleanup manually:

```python
from wab.app.consent_manager import ConsentManager

consent_manager = ConsentManager()
deleted = consent_manager.cleanup_expired_records()
print(f"Deleted {deleted} expired records")
```

### 3. Address and Session Data Cleanup

**Addresses:**
- Currently handled manually after route optimization
- **TODO:** Implement automatic deletion 24 hours after creation
- **Future implementation:** Add timestamp tracking and background cleanup

**Session Data:**
- Location: `wab/utils/conversation_tracker.py`
- **TODO:** Add cleanup method for sessions older than 24 hours
- **Future implementation:** Integrate into daily cleanup task

## Verification

### Check Cleanup Logs

After setting up the scheduled task, verify it's working:

1. Check the log file (if configured)
2. Check the consent records file: `wab/data/consents.json`
3. Verify old records are being deleted

### Manual Test

```python
# Run cleanup manually to test
from wab.app.consent_manager import ConsentManager

consent_manager = ConsentManager()
stats = consent_manager.get_consent_statistics()
print(f"Total records before cleanup: {stats['total_records']}")

deleted = consent_manager.cleanup_expired_records()
print(f"Deleted: {deleted} records")

stats = consent_manager.get_consent_statistics()
print(f"Total records after cleanup: {stats['total_records']}")
```

## Legal Compliance

✅ **GDPR Article 5(1)(e):** Storage limitation
- Consent records: 3 years (legal requirement for proof)
- Addresses: 24 hours (operational necessity)
- Session data: 24 hours (operational necessity)

✅ **GDPR Article 17:** Right to erasure
- User can delete data via `/deletedata` command
- Consent marked as withdrawn, data deletion scheduled

✅ **Recital 39:** Proof of consent
- Consent records preserved for 3 years to demonstrate compliance
- Records contain: consent date, version, user decision

## TODO Before Production

- [ ] Create `cleanup_task.py` script
- [ ] Set up Windows Task Scheduler / Cron job
- [ ] Test cleanup runs successfully
- [ ] Monitor cleanup logs
- [ ] Implement address deletion 24h after creation
- [ ] Implement session data cleanup
- [ ] Document cleanup in privacy policy (already done)

## Support

For questions about data retention setup, contact: [YOUR_EMAIL]
