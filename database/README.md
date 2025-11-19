# Database Module

PostgreSQL database implementation for WhatsApp Route Optimizer with GDPR compliance.

## Overview

This module provides a complete database layer with:
- **PostgreSQL 18** backend with ACID compliance
- **SQLAlchemy ORM** for Python integration
- **GDPR-compliant** data lifecycle management
- **Automatic data retention** policies
- **Soft delete** pattern for user accounts
- **Audit logging** for compliance tracking

---

## Architecture

```
database/
├── schema.sql          # PostgreSQL schema definition
├── models.py           # SQLAlchemy ORM models
├── db_manager.py       # Connection and session management
├── test_models.py      # Test suite
├── .env                # Database credentials (gitignored)
├── .env.example        # Template for .env file
└── README.md           # This file
```

---

## Database Schema

### Tables

#### 1. **users** - User Accounts
Stores user profiles and account information.

**Columns:**
- `user_id` (UUID, PK) - Unique user identifier
- `phone_number` (VARCHAR, UNIQUE) - WhatsApp phone number
- `display_name` (VARCHAR) - User's display name
- `language` (VARCHAR) - Preferred language (default: 'es')
- `created_at` (TIMESTAMP) - Account creation time
- `updated_at` (TIMESTAMP) - Last update time
- `deleted_at` (TIMESTAMP) - Soft delete timestamp

**GDPR Retention:** Soft deleted 24 hours after consent withdrawal

**Relationships:**
- → consents (ON DELETE RESTRICT - must keep legal proof)
- → sessions (ON DELETE CASCADE - operational data)
- → audit_logs (ON DELETE SET NULL - preserve logs)

---

#### 2. **consents** - GDPR Consent Records
Tracks user consent for data processing (legal requirement under GDPR Article 7).

**Columns:**
- `consent_id` (UUID, PK) - Unique consent identifier
- `user_id` (UUID, FK) - Reference to user
- `consent_given` (BOOLEAN) - Whether consent was given
- `consent_date` (TIMESTAMP) - When consent was given
- `consent_version` (VARCHAR) - Version of terms accepted
- `consent_withdrawn` (BOOLEAN) - Whether consent was withdrawn
- `withdrawal_date` (TIMESTAMP) - When consent was withdrawn
- `ip_address` (VARCHAR) - IP address (if available)
- `user_agent` (VARCHAR) - User agent string
- `language` (VARCHAR) - Language of consent

**GDPR Retention:** 3 years (legal requirement)

**Foreign Key:** `ON DELETE RESTRICT` - Cannot delete user while consent exists

---

#### 3. **sessions** - Conversation Sessions
Tracks active conversation sessions with 24-hour expiry.

**Columns:**
- `session_id` (UUID, PK) - Unique session identifier
- `user_id` (UUID, FK) - Reference to user
- `last_message_at` (TIMESTAMP) - Last message timestamp
- `expires_at` (TIMESTAMP) - Session expiration time
- `created_at` (TIMESTAMP) - Session creation time

**GDPR Retention:** Deleted after 48 hours

**Foreign Key:** `ON DELETE CASCADE` - Auto-delete with user

---

#### 4. **audit_logs** - Audit Trail
Records all significant actions for GDPR accountability (Article 32).

**Columns:**
- `log_id` (UUID, PK) - Unique log identifier
- `user_id` (UUID, FK) - Reference to user (nullable)
- `action` (VARCHAR) - Action type (see Actions below)
- `actor` (VARCHAR) - Who performed the action
- `details` (JSONB) - Flexible JSON details
- `created_at` (TIMESTAMP) - When action occurred
- `ip_address` (VARCHAR) - IP address

**Actions:**
- `user_created` - User account created
- `consent_given` - User gave consent
- `consent_revoked` - User withdrew consent
- `data_accessed` - User data accessed
- `data_exported` - User data exported (Article 20)
- `data_deleted` - User data deleted (Article 17)
- `session_started` - Conversation started
- `route_requested` - Route optimization requested

**GDPR Retention:** 90 days

**Foreign Key:** `ON DELETE SET NULL` - Preserve logs after user deletion

---

#### 5. **schema_migrations** - Migration Tracking
Tracks applied database migrations for production deployment.

**Columns:**
- `version` (VARCHAR, PK) - Migration version
- `applied_at` (TIMESTAMP) - When migration was applied
- `description` (TEXT) - Migration description

---

## GDPR Compliance

### Data Retention Policies

| Data Type | Retention Period | Rationale |
|-----------|-----------------|-----------|
| **Consents** | 3 years | Legal requirement (GDPR Article 7) |
| **Sessions** | 48 hours | Operational data, storage limitation |
| **Audit Logs** | 90 days | Accountability requirement (Article 32) |
| **Users** | 24h after consent withdrawal | Right to erasure (Article 17) |

### Automatic Cleanup

The `cleanup_expired_data()` PostgreSQL function automatically deletes expired data:

```sql
SELECT * FROM cleanup_expired_data();
```

**Returns:**
```
 table_name | records_deleted
------------+-----------------
 sessions   |               5
 consents   |               2
 audit_logs |              10
 users      |               1
```

**Schedule:** Should be run daily via cron job or task scheduler.

### Foreign Key Cascade Strategies

- **RESTRICT** (consents): Must keep legal proof, prevents user deletion if consent exists
- **CASCADE** (sessions): Operational data, auto-delete with user
- **SET NULL** (audit_logs): Preserve audit trail after user deletion

---

## Setup

### 1. Install PostgreSQL

Download and install PostgreSQL 18 from: https://www.postgresql.org/download/

### 2. Create Database and User

```bash
psql -U postgres
```

```sql
CREATE DATABASE wab_db;
CREATE USER wab_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE wab_db TO wab_user;
\c wab_db
GRANT ALL ON SCHEMA public TO wab_user;
\q
```

### 3. Apply Schema

```bash
psql -U wab_user -d wab_db -f database/schema.sql
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update credentials:

```bash
cp database/.env.example database/.env
```

Edit `database/.env`:
```
DATABASE_URL=postgresql://wab_user:your_password@localhost:5432/wab_db?client_encoding=utf8
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6. Test Connection

```bash
python database/test_models.py
```

---

## Usage

### Basic Connection

```python
from database.db_manager import DatabaseManager
from database.models import User, Consent, Session, AuditLog

# Initialize database manager
db = DatabaseManager()

# Test connection
if db.test_connection():
    print("Connected successfully!")
```

### Using Context Manager (Recommended)

```python
# Automatic session management with commit/rollback
with db.get_session() as session:
    user = User(
        phone_number='+34644252886',
        display_name='John Doe',
        language='es'
    )
    session.add(user)
    # Automatically committed here

# Query data
with db.get_session() as session:
    user = session.query(User).filter_by(
        phone_number='+34644252886'
    ).first()
    print(f"Found user: {user.display_name}")
```

### Manual Session Management

```python
session = db.create_session()
try:
    user = User(phone_number='+34644252886')
    session.add(user)
    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()
```

### Creating Records

```python
with db.get_session() as session:
    # Create user
    user = User(
        phone_number='+34644252886',
        display_name='John Doe'
    )
    session.add(user)
    session.flush()  # Get user_id without committing

    # Create consent
    consent = Consent(
        user_id=user.user_id,
        consent_given=True,
        consent_version='1.0'
    )
    session.add(consent)

    # Create session
    conv_session = Session.create_new(
        user_id=user.user_id,
        expiry_hours=24
    )
    session.add(conv_session)

    # Create audit log
    audit = AuditLog.log_action(
        user_id=user.user_id,
        action='user_created',
        details={'source': 'whatsapp'}
    )
    session.add(audit)
```

### Reading Records

```python
with db.get_session() as session:
    # Get user by phone number
    user = session.query(User).filter_by(
        phone_number='+34644252886'
    ).first()

    # Get all consents for user
    consents = session.query(Consent).filter_by(
        user_id=user.user_id
    ).all()

    # Get active sessions
    from datetime import datetime
    active_sessions = session.query(Session).filter(
        Session.expires_at > datetime.now()
    ).all()

    # Query audit logs with JSONB
    logs = session.query(AuditLog).filter(
        AuditLog.details['source'].astext == 'whatsapp'
    ).all()
```

### Updating Records

```python
with db.get_session() as session:
    user = session.query(User).filter_by(
        phone_number='+34644252886'
    ).first()

    user.display_name = 'New Name'
    # Automatically committed at end of context
```

### Soft Delete

```python
with db.get_session() as session:
    user = session.query(User).filter_by(
        phone_number='+34644252886'
    ).first()

    user.soft_delete()  # Sets deleted_at timestamp

    # Check if user is active
    if user.is_active:
        print("User is active")
    else:
        print("User is deleted")
```

### Consent Withdrawal

```python
with db.get_session() as session:
    consent = session.query(Consent).filter_by(
        user_id=user_id
    ).first()

    consent.withdraw()  # Sets consent_withdrawn and withdrawal_date

    if consent.is_active:
        print("Consent is active")
    else:
        print("Consent withdrawn")
```

### Session Management

```python
with db.get_session() as session:
    # Create new conversation session
    conv_session = Session.create_new(
        user_id=user_id,
        expiry_hours=24
    )
    session.add(conv_session)
    session.flush()

    # Later: Update activity
    conv_session.update_activity(expiry_hours=24)

    # Check if active
    if conv_session.is_active:
        print("Session is active")
```

### Relationships

```python
with db.get_session() as session:
    user = session.query(User).filter_by(
        phone_number='+34644252886'
    ).first()

    # Access related records
    print(f"Consents: {len(user.consents)}")
    for consent in user.consents:
        print(f"  - Given: {consent.consent_given}")

    print(f"Sessions: {len(user.sessions)}")
    for sess in user.sessions:
        print(f"  - Expires: {sess.expires_at}")

    print(f"Audit Logs: {len(user.audit_logs)}")
    for log in user.audit_logs:
        print(f"  - Action: {log.action}")
```

### GDPR Cleanup

```python
# Execute automatic cleanup
results = db.execute_cleanup()
print(f"Cleaned up {results['sessions']} expired sessions")
print(f"Cleaned up {results['consents']} expired consents")
print(f"Cleaned up {results['audit_logs']} old audit logs")
print(f"Soft-deleted {results['users']} users")
```

### Connection Pool Status

```python
status = db.get_pool_status()
print(f"Pool size: {status['size']}")
print(f"Available: {status['checked_in']}")
print(f"In use: {status['checked_out']}")
print(f"Overflow: {status['overflow']}")
```

---

## Models API

### User Model

**Properties:**
- `is_active` - Returns True if user is not soft deleted
- `soft_delete()` - Soft delete the user

**Relationships:**
- `consents` - List of Consent records
- `sessions` - List of Session records
- `audit_logs` - List of AuditLog records

### Consent Model

**Properties:**
- `is_active` - Returns True if consent is active (given and not withdrawn)
- `expires_at` - Returns datetime when consent record expires (3 years)
- `withdraw()` - Withdraw consent

### Session Model

**Properties:**
- `is_active` - Returns True if session has not expired
- `update_activity(expiry_hours=24)` - Update last activity and extend expiration

**Static Methods:**
- `create_new(user_id, expiry_hours=24)` - Create new session with default expiry

### AuditLog Model

**Properties:**
- `expires_at` - Returns datetime when log expires (90 days)

**Static Methods:**
- `log_action(user_id, action, actor='system', details=None, ip_address=None)` - Create audit log entry

---

## Migrations

### Development Phase (Current)

Use `schema.sql` with `DROP TABLE` for fast iteration:

```bash
psql -U wab_user -d wab_db -f database/schema.sql
```

**Warning:** This deletes all data! Only safe for development.

### Production Phase

Use Alembic for safe migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

Example manual migration:

```sql
-- migrations/002_add_display_name.sql
ALTER TABLE users ADD COLUMN display_name VARCHAR(100);

INSERT INTO schema_migrations (version, description)
VALUES ('002', 'Add display_name column to users');
```

---

## Testing

Run the complete test suite:

```bash
python database/test_models.py
```

Tests cover:
1. Database connection
2. CRUD operations on all models
3. Relationships between models
4. GDPR cleanup function
5. Soft delete functionality
6. Constraint validation

---

## Cloud Deployment

### Railway

1. Create PostgreSQL database on Railway
2. Get connection string from Railway dashboard
3. Update `DATABASE_URL` in production `.env`
4. Deploy schema:

```bash
psql $DATABASE_URL -f database/schema.sql
```

### Google Cloud SQL

1. Create Cloud SQL PostgreSQL instance
2. Create database and user
3. Get connection string
4. For Cloud Run/Functions, use Cloud SQL Proxy
5. Deploy schema using psql

---

## Monitoring

### Pool Status

```python
status = db.get_pool_status()
# Monitor checked_out connections
# Alert if overflow is frequently used
```

### Cleanup Results

```python
results = db.execute_cleanup()
# Log results for monitoring
# Alert if unusual numbers
```

### Performance

- Monitor query execution times
- Use `echo=True` for SQL debugging
- Add indexes for frequently queried columns

---

## Security

### Credentials

- **Never commit** `.env` file (already in `.gitignore`)
- Use **strong passwords** for production
- Rotate passwords regularly
- Use **SSL/TLS** for cloud connections

### SQL Injection

- SQLAlchemy ORM prevents SQL injection
- Always use parameterized queries
- Never concatenate user input into SQL strings

### Access Control

- Use **least privilege** principle
- Separate read-only and read-write users for production
- Restrict network access to database

---

## Troubleshooting

### Connection Issues

**Error:** `connection refused`
- Check PostgreSQL is running: `pg_ctl status`
- Check connection parameters in `.env`
- Check firewall rules

**Error:** `authentication failed`
- Verify username and password
- Check `pg_hba.conf` for authentication method

### Encoding Issues

**Error:** `'utf-8' codec can't decode byte`
- Ensure `client_encoding=utf8` in DATABASE_URL
- On Windows, verify PostgreSQL encoding is UTF-8

### Migration Issues

**Error:** `table already exists`
- Drop tables manually or use `DROP TABLE IF EXISTS`
- Check `schema_migrations` table for version

---

## Best Practices

1. **Always use context managers** for session management
2. **Close database** when shutting down: `db.close()`
3. **Test on staging** before production migrations
4. **Backup before migrations**: `pg_dump wab_db > backup.sql`
5. **Schedule daily cleanup** for GDPR compliance
6. **Monitor connection pool** to prevent leaks
7. **Use audit logging** for all sensitive operations
8. **Soft delete users** to preserve audit trail

---

## Support

For issues or questions:
1. Check this README
2. Review test suite in `test_models.py`
3. Check SQLAlchemy docs: https://docs.sqlalchemy.org/
4. Check PostgreSQL docs: https://www.postgresql.org/docs/

---

## License

Part of WhatsApp Route Optimizer project.
