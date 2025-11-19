"""
Database Manager for WhatsApp Route Optimizer

This module provides database connection management, session handling,
and transaction support using SQLAlchemy.

Features:
- Connection pooling for performance
- Context managers for automatic session cleanup
- Transaction management with rollback support
- Environment-based configuration
- Thread-safe session management

Usage:
    from database.db_manager import DatabaseManager

    # Initialize (usually once at application startup)
    db_manager = DatabaseManager()

    # Use context manager for automatic session cleanup
    with db_manager.get_session() as session:
        user = session.query(User).filter_by(phone_number='+1234567890').first()
        # Session automatically committed and closed

    # Manual session management
    session = db_manager.create_session()
    try:
        user = User(phone_number='+1234567890')
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import Pool
from dotenv import load_dotenv

from database.models import Base

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.

    This class implements the singleton-like pattern for engine creation
    and provides thread-safe session management.

    Attributes:
        engine: SQLAlchemy engine instance
        SessionLocal: Session factory for creating new sessions
        scoped_session: Thread-local session registry
    """

    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL. If None, reads from DATABASE_URL env var.
            echo: If True, log all SQL statements (useful for debugging)

        Environment Variables:
            DATABASE_URL: PostgreSQL connection string
                Format: postgresql://user:password@host:port/database
                Example: postgresql://wab_user:password@localhost:5432/wab_db
        """
        # Get database URL from parameter or environment
        self.database_url = database_url or os.getenv('DATABASE_URL')

        if not self.database_url:
            raise ValueError(
                "Database URL not provided. Set DATABASE_URL environment variable "
                "or pass database_url parameter."
            )

        # Ensure UTF-8 encoding for Windows PostgreSQL compatibility
        if '?' in self.database_url:
            if 'client_encoding' not in self.database_url:
                self.database_url += '&client_encoding=utf8'
        else:
            self.database_url += '?client_encoding=utf8'

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            echo=echo,
            pool_size=10,           # Number of connections to maintain
            max_overflow=20,        # Additional connections if pool is full
            pool_pre_ping=True,     # Verify connections before using them
            pool_recycle=3600,      # Recycle connections after 1 hour
        )

        # Configure connection pool events
        self._setup_pool_events()

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Create scoped session for thread-safety
        self.ScopedSession = scoped_session(self.SessionLocal)

        logger.info("Database manager initialized successfully")

    def _setup_pool_events(self):
        """Set up connection pool event listeners for monitoring and optimization."""

        @event.listens_for(Pool, "connect")
        def set_search_path(dbapi_conn, connection_record):
            """Set default schema search path on new connections."""
            cursor = dbapi_conn.cursor()
            cursor.execute("SET search_path TO public")
            cursor.close()

        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log when connection is checked out from pool (for debugging)."""
            logger.debug("Connection checked out from pool")

        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Log when connection is returned to pool (for debugging)."""
            logger.debug("Connection returned to pool")

    def create_session(self) -> Session:
        """
        Create a new database session.

        Returns:
            Session: New SQLAlchemy session

        Note:
            Caller is responsible for closing the session.
            Consider using get_session() context manager instead.
        """
        return self.SessionLocal()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Automatically handles:
        - Session creation
        - Commit on success
        - Rollback on exception
        - Session cleanup

        Yields:
            Session: Database session

        Example:
            with db_manager.get_session() as session:
                user = User(phone_number='+1234567890')
                session.add(user)
                # Automatically committed here
        """
        session = self.create_session()
        try:
            yield session
            session.commit()
            logger.debug("Session committed successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Session rolled back due to error: {e}")
            raise
        finally:
            session.close()
            logger.debug("Session closed")

    def get_scoped_session(self) -> Session:
        """
        Get thread-local scoped session.

        Returns:
            Session: Thread-local session instance

        Note:
            Use this for multi-threaded applications.
            Call remove_scoped_session() when done with thread.
        """
        return self.ScopedSession()

    def remove_scoped_session(self):
        """Remove current thread's scoped session."""
        self.ScopedSession.remove()
        logger.debug("Scoped session removed")

    def create_all_tables(self):
        """
        Create all tables defined in models.

        Warning:
            Only use this in development. In production, use migrations.
        """
        Base.metadata.create_all(bind=self.engine)
        logger.info("All tables created successfully")

    def drop_all_tables(self):
        """
        Drop all tables.

        Warning:
            THIS DELETES ALL DATA! Only use in development/testing.
        """
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All tables dropped")

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def execute_cleanup(self) -> dict:
        """
        Execute GDPR data cleanup function.

        Calls the cleanup_expired_data() PostgreSQL function that:
        - Deletes expired sessions (>48 hours)
        - Deletes expired consents (>3 years)
        - Deletes old audit logs (>90 days)
        - Soft-deletes users with withdrawn consent (>24 hours)

        Returns:
            dict: Dictionary with cleanup results
                Format: {'sessions': 5, 'consents': 2, 'audit_logs': 10, 'users': 1}

        Example:
            results = db_manager.execute_cleanup()
            print(f"Cleaned up {results['sessions']} expired sessions")
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM cleanup_expired_data()"))
                cleanup_results = {row[0]: row[1] for row in result}

                total = sum(cleanup_results.values())
                logger.info(f"Cleanup completed: {total} total records processed")
                logger.info(f"Details: {cleanup_results}")

                conn.commit()
                return cleanup_results
        except Exception as e:
            logger.error(f"Cleanup execution failed: {e}")
            raise

    def get_pool_status(self) -> dict:
        """
        Get current connection pool status.

        Returns:
            dict: Pool statistics

        Example:
            status = db_manager.get_pool_status()
            print(f"Active connections: {status['size']}")
        """
        pool = self.engine.pool
        return {
            'size': pool.size(),           # Current pool size
            'checked_in': pool.checkedin(), # Available connections
            'checked_out': pool.checkedout(), # In-use connections
            'overflow': pool.overflow(),    # Overflow connections
            'total': pool.size() + pool.overflow()
        }

    def close(self):
        """
        Close all connections and cleanup resources.

        Call this when shutting down the application.
        """
        self.ScopedSession.remove()
        self.engine.dispose()
        logger.info("Database manager closed, all connections disposed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None, echo: bool = False) -> DatabaseManager:
    """
    Get or create global database manager instance.

    Args:
        database_url: PostgreSQL connection URL (optional)
        echo: Enable SQL statement logging (optional)

    Returns:
        DatabaseManager: Global database manager instance

    Example:
        from database.db_manager import get_db_manager

        db = get_db_manager()
        with db.get_session() as session:
            users = session.query(User).all()
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(database_url=database_url, echo=echo)

    return _db_manager


def close_db_manager():
    """Close global database manager and cleanup resources."""
    global _db_manager

    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None


# Export main classes and functions
__all__ = ['DatabaseManager', 'get_db_manager', 'close_db_manager']
