# Database Migration Guide

This guide explains how to migrate from JSON-based storage to the PostgreSQL database.

---

## Overview

The WhatsApp Route Optimizer has been upgraded with a PostgreSQL database backend, replacing JSON file storage with:

- **PostgreSQL 18** for ACID-compliant storage
- **SQLAlchemy ORM** for Python integration
- **GDPR-compliant** automatic data lifecycle
- **Scalable** architecture supporting unlimited users
- **Thread-safe** operations for production deployment

---

## What Changed

### Before (JSON-based)

```
wab/storage/user_consents.json  → Consent records
wab/data/sessions.json           → Session tracking
```

### After (Database)

```
database/
├── schema.sql           # PostgreSQL schema
├── models.py            # ORM models
├── db_manager.py        # Connection management
└── README.md            # Documentation

PostgreSQL Tables:
├── users                # User accounts
├── consents             # GDPR consent records
├── sessions             # Conversation sessions
├── audit_logs           # Audit trail
└── schema_migrations    # Migration tracking
```

---

## Migration Steps

### Step 1: Current Status

The database is already set up and tested! ✅

- PostgreSQL database `wab_db` created
- Schema applied successfully
- All tables created with proper constraints and indexes
- Database-backed versions of ConsentManager and ConversationTracker created and tested

### Step 2: Choose Migration Approach

You have two options:

#### Option A: Start Fresh (Recommended for Development)

Simply start using the new database-backed classes. Old JSON data will remain as backup.

**Advantages:**
- Clean start
- No migration complexity
- Old data preserved as backup

**Code changes:**
```python
# OLD
from wab.app.consent_manager import ConsentManager
from wab.utils.conversation_tracker import ConversationTracker

# NEW
from wab.app.consent_manager_db import ConsentManager
from wab.utils.conversation_tracker_db import ConversationTracker

# Everything else stays the same!
```

#### Option B: Migrate Existing Data

If you have existing production data to preserve, use the migration functions.

**Migrate consents:**
```python
from wab.app.consent_manager_db import migrate_from_json

stats = migrate_from_json('wab/storage/user_consents.json')
print(f"Migrated {stats['migrated']} consents with {stats['errors']} errors")
```

**Migrate sessions:**
```python
from wab.utils.conversation_tracker_db import migrate_from_json

stats = migrate_from_json('wab/data/sessions.json')
print(f"Migrated {stats['migrated']} sessions, skipped {stats['skipped']} expired")
```

### Step 3: Update Application Code

The new classes maintain API compatibility, so minimal code changes are needed.

#### ConsentManager Migration

```python
# OLD CODE (still works, no changes needed to calling code)
from wab.app.consent_manager import ConsentManager

consent_mgr = ConsentManager()
consent_mgr.save_consent('+34644252886', True)
has_consent = consent_mgr.has_consent('+34644252886')

# NEW CODE (just change the import!)
from wab.app.consent_manager_db import ConsentManager

consent_mgr = ConsentManager()  # Same API!
consent_mgr.save_consent('+34644252886', True)
has_consent = consent_mgr.has_consent('+34644252886')
```

#### ConversationTracker Migration

```python
# OLD CODE
from wab.utils.conversation_tracker import ConversationTracker

tracker = ConversationTracker()
tracker.update_conversation('+34644252886')
is_active = tracker.is_within_window('+34644252886')

# NEW CODE (just change the import!)
from wab.utils.conversation_tracker_db import ConversationTracker

tracker = ConversationTracker()  # Same API!
tracker.update_conversation('+34644252886')
is_active = tracker.is_within_window('+34644252886')
```

### Step 4: Environment Configuration

Ensure the database connection is configured:

**File: `database/.env`**
```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database?client_encoding=utf8
```

The database-backed classes will automatically read this configuration.

### Step 5: Test the Migration

Run the test suites to verify everything works:

```bash
# Test database models
python database/test_models.py

# Test ConsentManager
python wab/app/test_consent_manager_db.py

# Test ConversationTracker
python wab/utils/test_conversation_tracker_db.py
```

All tests should pass! ✅

### Step 6: Gradual Rollout (Production)

For production, consider a gradual rollout:

1. **Week 1: Parallel Run**
   - Deploy database-backed code
   - Keep JSON versions as backup
   - Monitor for issues

2. **Week 2: Verify**
   - Compare data between JSON and database
   - Verify GDPR cleanup is working
   - Check audit logs

3. **Week 3: Switch Over**
   - Make database the primary source
   - Keep JSON as read-only backup

4. **Week 4: Cleanup**
   - Archive old JSON files
   - Remove old code (keep in git history)

---

## File-by-File Changes

### Files to Update

| File | Change Required | Complexity |
|------|----------------|------------|
| Any file using `ConsentManager` | Change import statement | Easy |
| Any file using `ConversationTracker` | Change import statement | Easy |
| `requirements.txt` | Already updated ✅ | Done |
| `.env` | Add `DATABASE_URL` | Easy |

### Example: Updating webhook.py

**Before:**
```python
from wab.app.consent_manager import ConsentManager
from wab.utils.conversation_tracker import ConversationTracker

consent_mgr = ConsentManager()
tracker = ConversationTracker()
```

**After:**
```python
from wab.app.consent_manager_db import ConsentManager
from wab.utils.conversation_tracker_db import ConversationTracker

consent_mgr = ConsentManager()  # Same API!
tracker = ConversationTracker()  # Same API!
```

---

## Benefits After Migration

### 1. **Scalability**
- JSON: Limited to ~10,000 users
- Database: Handles millions of users

### 2. **Performance**
- JSON: Loads entire file for each operation
- Database: Indexed queries, instant lookups

### 3. **Concurrency**
- JSON: File locking issues in multi-server setup
- Database: Full ACID transactions, safe for concurrent access

### 4. **GDPR Compliance**
- JSON: Manual cleanup required
- Database: Automatic cleanup via `cleanup_expired_data()` function

### 5. **Audit Trail**
- JSON: No audit logging
- Database: Full audit trail in `audit_logs` table

### 6. **Data Integrity**
- JSON: No constraints
- Database: Foreign keys, CHECK constraints, data validation

---

## GDPR Automation

The database automatically handles GDPR requirements:

### Automatic Cleanup Schedule

Set up a daily cron job (or Windows Task Scheduler):

**Linux/Mac cron:**
```bash
# Run cleanup daily at 2 AM
0 2 * * * python /path/to/run_cleanup.py
```

**Windows Task Scheduler:**
- Create task: "GDPR Cleanup"
- Trigger: Daily at 2:00 AM
- Action: `python C:\path\to\run_cleanup.py`

**File: `database/run_cleanup.py`**
```python
#!/usr/bin/env python3
"""Daily GDPR cleanup script."""

from database.db_manager import get_db_manager

def main():
    db = get_db_manager()
    results = db.execute_cleanup()

    print(f"GDPR Cleanup Results:")
    print(f"  Sessions: {results['sessions']} expired")
    print(f"  Consents: {results['consents']} expired (>3 years)")
    print(f"  Audit logs: {results['audit_logs']} expired (>90 days)")
    print(f"  Users: {results['users']} soft-deleted (consent withdrawn >24h)")

    db.close()

if __name__ == '__main__':
    main()
```

### Data Retention Summary

| Data Type | Retention | Action |
|-----------|-----------|--------|
| Sessions | 48 hours | Auto-delete |
| Consents | 3 years | Auto-delete (legal requirement) |
| Audit Logs | 90 days | Auto-delete |
| Users | 24h after consent withdrawal | Soft delete |

---

## Rollback Plan

If you need to roll back to JSON storage:

1. **Stop the application**
2. **Export database to JSON** (optional backup)
3. **Revert code changes:**
   ```bash
   git checkout HEAD~1  # Or specific commit
   ```
4. **Restore JSON files** from backup
5. **Restart application**

**Export script** (for backup):
```python
from database.db_manager import get_db_manager
from database.models import User, Consent, Session
import json

db = get_db_manager()

# Export consents
with db.get_session() as session:
    users = session.query(User).all()
    consents = {}

    for user in users:
        if user.consents:
            consent = user.consents[0]
            consents[user.phone_number] = {
                'consent_given': consent.consent_given,
                'consent_date': consent.consent_date.isoformat(),
                'consent_withdrawn': consent.consent_withdrawn,
                'withdrawal_date': consent.withdrawal_date.isoformat() if consent.withdrawal_date else None,
                'consent_version': consent.consent_version,
                'language': consent.language
            }

    with open('backup_consents.json', 'w') as f:
        json.dump(consents, f, indent=2)

print("Backup complete!")
```

---

## Monitoring & Maintenance

### Daily Checks

```python
from database.db_manager import get_db_manager

db = get_db_manager()

# Check connection
if db.test_connection():
    print("✓ Database connection OK")

# Check pool status
status = db.get_pool_status()
print(f"✓ Pool: {status['checked_out']} active, {status['checked_in']} available")

# Get consent statistics
from wab.app.consent_manager_db import ConsentManager
cm = ConsentManager()
stats = cm.get_statistics()
print(f"✓ Consents: {stats['active_consents']} active, {stats['withdrawn_consents']} withdrawn")

# Get session count
from wab.utils.conversation_tracker_db import ConversationTracker
tracker = ConversationTracker()
count = tracker.get_active_sessions_count()
print(f"✓ Sessions: {count} active")
```

### Weekly Tasks

1. **Backup database:**
   ```bash
   pg_dump -U wab_user wab_db > backup_$(date +%Y%m%d).sql
   ```

2. **Review audit logs:**
   ```sql
   SELECT action, COUNT(*)
   FROM audit_logs
   WHERE created_at > NOW() - INTERVAL '7 days'
   GROUP BY action;
   ```

3. **Check for errors:**
   ```bash
   tail -100 /var/log/application.log | grep ERROR
   ```

### Monthly Tasks

1. **Vacuum database** (PostgreSQL maintenance):
   ```sql
   VACUUM ANALYZE;
   ```

2. **Review retention policies:**
   - Are cleanup rates normal?
   - Any unusual patterns?

3. **Test backup restore:**
   ```bash
   # Create test database
   createdb -U postgres wab_db_test

   # Restore from backup
   psql -U wab_user wab_db_test < backup_20251106.sql

   # Verify
   psql -U wab_user wab_db_test -c "SELECT COUNT(*) FROM users;"
   ```

---

## Cloud Deployment

### Railway Deployment

1. **Create PostgreSQL database** on Railway
2. **Get connection string** from Railway dashboard
3. **Update `.env`:**
   ```
   DATABASE_URL=postgresql://user:pass@railway-host:port/db
   ```
4. **Deploy schema:**
   ```bash
   psql $DATABASE_URL -f database/schema.sql
   ```
5. **Deploy application** (Railway will use DATABASE_URL automatically)

### Google Cloud SQL

1. **Create Cloud SQL instance** (PostgreSQL 18)
2. **Create database and user**
3. **Get connection string**
4. **For Cloud Run/Functions**, use Cloud SQL Proxy
5. **Deploy schema** via Cloud SQL Proxy:
   ```bash
   psql "host=/cloudsql/PROJECT:REGION:INSTANCE user=wab_user dbname=wab_db" -f database/schema.sql
   ```

---

## Troubleshooting

### Connection Issues

**Error:** `connection refused`
- **Fix:** Check PostgreSQL is running: `pg_ctl status`
- **Fix:** Verify connection string in `.env`

**Error:** `authentication failed`
- **Fix:** Check username/password
- **Fix:** Check `pg_hba.conf` authentication method

### Migration Issues

**Error:** `table already exists`
- **Fix:** Drop tables or use `DROP TABLE IF EXISTS` in schema.sql

**Error:** `foreign key constraint failed`
- **Fix:** Delete child records first (consents before users)

### Performance Issues

**Slow queries:**
- **Fix:** Check indexes: `\d users` in psql
- **Fix:** Run VACUUM ANALYZE

**Connection pool exhausted:**
- **Fix:** Increase `pool_size` in `db_manager.py`
- **Fix:** Check for connection leaks

---

## Support

For issues:
1. Check [database/README.md](README.md)
2. Review test suites for examples
3. Check SQLAlchemy docs: https://docs.sqlalchemy.org/
4. Check PostgreSQL docs: https://www.postgresql.org/docs/

---

## Summary

✅ Database setup complete
✅ Schema applied
✅ ORM models created
✅ Database manager implemented
✅ ConsentManager migrated
✅ ConversationTracker migrated
✅ All tests passing
✅ GDPR compliance automated
✅ Ready for production!

**Next Steps:**
1. Update import statements in your application code
2. Optionally migrate existing JSON data
3. Set up daily GDPR cleanup job
4. Deploy to production
5. Monitor and maintain

---

*Database implementation completed on: November 6, 2025*
*Branch: `db_implementation`*
*PostgreSQL Version: 18*
*SQLAlchemy Version: 2.0.23*
