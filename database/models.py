"""
SQLAlchemy ORM Models for WhatsApp Route Optimizer Database

This module defines the database models that map to PostgreSQL tables.
These models provide a Pythonic interface to interact with the database.

Tables:
- User: User accounts and profiles
- Consent: GDPR consent records (3-year retention)
- Session: Active conversation sessions (48-hour retention)
- AuditLog: Audit trail for GDPR compliance (90-day retention)
- SchemaMigration: Migration version tracking

GDPR Compliance:
- Soft delete for users (deleted_at timestamp)
- Automatic cleanup via cleanup_expired_data() function
- Foreign key cascade strategies for data lifecycle management
"""

from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    CheckConstraint, Index, func, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import text
import uuid

Base = declarative_base()


class SchemaMigration(Base):
    """
    Tracks applied database migrations.

    Used for production migration management to ensure
    migrations are applied in order and only once.
    """
    __tablename__ = 'schema_migrations'

    version = Column(String(50), primary_key=True)
    applied_at = Column(DateTime(timezone=True), default=func.now())
    description = Column(Text)

    def __repr__(self):
        return f"<SchemaMigration(version='{self.version}', applied_at='{self.applied_at}')>"


class User(Base):
    """
    User account and profile information.

    GDPR Lifecycle:
    - Created when user first contacts the system
    - Soft deleted 24h after consent withdrawal (deleted_at set)
    - Phone number is unique identifier
    - Display name optional (from WhatsApp profile)

    Relationships:
    - consents: User's consent history (ON DELETE RESTRICT - must keep proof)
    - sessions: Active conversation sessions (ON DELETE CASCADE)
    - audit_logs: Audit trail entries (ON DELETE SET NULL - preserve logs)
    """
    __tablename__ = 'users'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    display_name = Column(String(100))
    language = Column(String(5), default='es')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # Soft delete

    # Relationships
    consents = relationship("Consent", back_populates="user", cascade="all")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "phone_number ~ '^\\+?[0-9]+$'",
            name='phone_format'
        ),
        Index('idx_users_phone', 'phone_number'),
        Index('idx_users_created', 'created_at'),
        Index('idx_users_deleted', 'deleted_at', postgresql_where=text('deleted_at IS NOT NULL'))
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', phone='{self.phone_number}', deleted={self.deleted_at is not None})>"

    @property
    def is_active(self):
        """Check if user is active (not soft deleted)"""
        return self.deleted_at is None

    def soft_delete(self):
        """Soft delete the user by setting deleted_at timestamp"""
        self.deleted_at = datetime.now()

    def anonymize(self):
        """
        Anonymize personal data for GDPR Article 17 (Right to erasure).

        Overwrites PII with a non-reversible numeric placeholder derived from
        user_id, then sets deleted_at. The row is kept for FK integrity with
        consent records (3-year retention) and audit logs (90-day retention).

        Placeholder format: 14 decimal digits (passes phone_format constraint
        and VARCHAR(20) limit). Derived from user_id so it is unique per user.
        """
        # 14-digit unique placeholder: user_id is the UUID PK, so
        # int % 10^14 is unique within this database and digits-only.
        placeholder = str(self.user_id.int % 10**14).zfill(14)
        self.phone_number = placeholder
        self.display_name = None
        self.deleted_at = datetime.now()


class Consent(Base):
    """
    GDPR consent records with 3-year retention.

    GDPR Lifecycle:
    - Created when user gives consent
    - Updated when user withdraws consent
    - Retained for 3 years (legal requirement - Article 7 GDPR)
    - Deleted automatically by cleanup_expired_data()

    Foreign Key Strategy:
    - ON DELETE RESTRICT: Cannot delete user if consent exists
    - Rationale: Must keep legal proof of consent

    Fields:
    - consent_given: Boolean indicating if consent was given
    - consent_withdrawn: Boolean indicating if consent was withdrawn
    - consent_version: Version of terms & conditions
    - ip_address: IP address where consent was given (if available)
    - user_agent: User agent string (WhatsApp client info)
    """
    __tablename__ = 'consents'

    consent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    consent_given = Column(Boolean, nullable=False)
    consent_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    consent_version = Column(String(10), nullable=False, default='1.0')
    consent_withdrawn = Column(Boolean, default=False)
    withdrawal_date = Column(DateTime(timezone=True))
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(String(255))
    language = Column(String(5), default='es')

    # Relationships
    user = relationship("User", back_populates="consents")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(consent_withdrawn = FALSE AND withdrawal_date IS NULL) OR "
            "(consent_withdrawn = TRUE AND withdrawal_date IS NOT NULL)",
            name='valid_withdrawal'
        ),
        Index('idx_consents_user', 'user_id'),
        Index('idx_consents_date', 'consent_date'),
        Index('idx_consents_status', 'consent_given', 'consent_withdrawn')
    )

    def __repr__(self):
        return f"<Consent(consent_id='{self.consent_id}', user_id='{self.user_id}', given={self.consent_given}, withdrawn={self.consent_withdrawn})>"

    def withdraw(self):
        """Withdraw consent and set withdrawal date"""
        self.consent_withdrawn = True
        self.withdrawal_date = datetime.now()

    @property
    def is_active(self):
        """Check if consent is currently active"""
        return self.consent_given and not self.consent_withdrawn

    @property
    def expires_at(self):
        """Calculate when this consent record expires (3 years from consent date)"""
        return self.consent_date + timedelta(days=3*365)


class Session(Base):
    """
    Active conversation sessions with 48-hour retention.

    GDPR Lifecycle:
    - Created when conversation starts
    - Updated on each message (last_message_at)
    - Expires after 24 hours of inactivity
    - Deleted after 48 hours by cleanup_expired_data()

    Foreign Key Strategy:
    - ON DELETE CASCADE: Auto-delete sessions when user is deleted
    - Rationale: Sessions are operational data, not legal records

    Usage:
    - Track conversation context and state
    - Determine if user is in active conversation
    - Clean up stale sessions automatically
    """
    __tablename__ = 'sessions'

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'expires_at > last_message_at',
            name='valid_expiry'
        ),
        Index('idx_sessions_user', 'user_id'),
        Index('idx_sessions_expiry', 'expires_at')
    )

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id='{self.user_id}', expires_at='{self.expires_at}')>"

    @property
    def is_active(self):
        """Check if session is still active (not expired)"""
        return datetime.now(self.expires_at.tzinfo) < self.expires_at

    def update_activity(self, expiry_hours=24):
        """Update last activity and extend expiration"""
        now = datetime.now(self.last_message_at.tzinfo)
        self.last_message_at = now
        self.expires_at = now + timedelta(hours=expiry_hours)

    @staticmethod
    def create_new(user_id, expiry_hours=24):
        """Create a new session with default expiry"""
        now = datetime.now()
        return Session(
            user_id=user_id,
            last_message_at=now,
            expires_at=now + timedelta(hours=expiry_hours)
        )


class AuditLog(Base):
    """
    Audit trail for GDPR compliance with 90-day retention.

    GDPR Lifecycle:
    - Created on every significant action
    - Retained for 90 days (accountability requirement)
    - Deleted automatically by cleanup_expired_data()

    Foreign Key Strategy:
    - ON DELETE SET NULL: Preserve logs even after user deletion
    - Rationale: Audit trail must survive user deletion for compliance

    Actions:
    - user_created: User account created
    - consent_given: User gave consent
    - consent_revoked: User withdrew consent
    - data_accessed: User data was accessed
    - data_exported: User data was exported (GDPR Article 20)
    - data_deleted: User data was deleted (GDPR Article 17)
    - session_started: Conversation session started
    - route_requested: Route optimization requested

    Details Field:
    - JSONB for flexible storage
    - Can contain request/response data, IP addresses, etc.
    - Indexed with GIN for fast queries
    """
    __tablename__ = 'audit_logs'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'))
    action = Column(String(50), nullable=False)
    actor = Column(String(50), nullable=False, default='system')
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    ip_address = Column(String(45))

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "action IN ('user_created', 'consent_given', 'consent_revoked', "
            "'data_accessed', 'data_exported', 'data_deleted', "
            "'session_started', 'route_requested')",
            name='valid_action'
        ),
        Index('idx_audit_logs_user', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_created', 'created_at'),
        Index('idx_audit_logs_details', 'details', postgresql_using='gin')
    )

    def __repr__(self):
        return f"<AuditLog(log_id='{self.log_id}', action='{self.action}', user_id='{self.user_id}', created_at='{self.created_at}')>"

    @staticmethod
    def log_action(user_id, action, actor='system', details=None, ip_address=None):
        """Helper method to create audit log entries"""
        return AuditLog(
            user_id=user_id,
            action=action,
            actor=actor,
            details=details,
            ip_address=ip_address
        )

    @property
    def expires_at(self):
        """Calculate when this audit log expires (90 days from creation)"""
        return self.created_at + timedelta(days=90)


# Export all models for easy import
__all__ = ['Base', 'User', 'Consent', 'Session', 'AuditLog', 'SchemaMigration']
