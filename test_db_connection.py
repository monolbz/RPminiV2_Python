#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Connection Test
Tests database connection using psycopg2 and SQLAlchemy
"""

import psycopg2
from sqlalchemy import create_engine, text
import sys

# Database connection parameters
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'wab_db',
    'user': 'wab_user',
    'password': 'Sanderk0=',
    'client_encoding': 'UTF8'  # Force UTF-8 encoding
}

# SQLAlchemy connection URL
DATABASE_URL = (
    f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
    f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
    f"?client_encoding=utf8"  # Force UTF-8 encoding
)

print("=" * 60)
print("PostgreSQL Connection Test")
print("=" * 60)

# TEST 1: psycopg2 direct connection
print("\n[Test 1] Testing psycopg2 connection...")
try:
    # Connect to database
    conn = psycopg2.connect(**DATABASE_CONFIG)
    print("✅ psycopg2 connection successful!")

    # Create cursor to run queries
    cursor = conn.cursor()

    # Get PostgreSQL version
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    try:
        version_str = version[0][:50] if version[0] else "Unknown"
        print(f"✅ PostgreSQL version: {version_str}...")
    except UnicodeDecodeError:
        print(f"✅ PostgreSQL version: PostgreSQL 18.x (encoding issue with special chars)")

    # Test database access
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()
    print(f"✅ Connected to database: {db_name[0]}")

    # Close cursor and connection
    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ psycopg2 connection failed: {e}")
    sys.exit(1)

# TEST 2: SQLAlchemy connection
print("\n[Test 2] Testing SQLAlchemy connection...")
try:
    # Create engine
    engine = create_engine(DATABASE_URL)

    # Test connection
    with engine.connect() as connection:
        # Run test query
        result = connection.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()
        print(f"✅ SQLAlchemy connection successful!")
        print(f"✅ Test query result: {test_value[0]}")

        # Verify we can access wab_db
        result = connection.execute(text("SELECT current_user, current_database()"))
        user_db = result.fetchone()
        print(f"✅ Connected as user: {user_db[0]}")
        print(f"✅ To database: {user_db[1]}")

except Exception as e:
    print(f"❌ SQLAlchemy connection failed: {e}")
    sys.exit(1)

# TEST 3: Verify schema permissions
print("\n[Test 3] Testing schema permissions...")
try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        # Try to create a test table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS test_permissions (
                id SERIAL PRIMARY KEY,
                test_field VARCHAR(50)
            )
        """))
        connection.commit()
        print("✅ Can create tables")

        # Try to insert data
        connection.execute(text("""
            INSERT INTO test_permissions (test_field)
            VALUES ('Permission test successful')
        """))
        connection.commit()
        print("✅ Can insert data")

        # Try to query data
        result = connection.execute(text("SELECT * FROM test_permissions"))
        rows = result.fetchall()
        print(f"✅ Can query data (found {len(rows)} row(s))")

        # Clean up test table
        connection.execute(text("DROP TABLE test_permissions"))
        connection.commit()
        print("✅ Can delete tables")

except Exception as e:
    print(f"❌ Permission test failed: {e}")
    sys.exit(1)

# SUCCESS SUMMARY
print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nDatabase connection is working correctly!")
print(f"Connection URL: postgresql://{DATABASE_CONFIG['user']}:***@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
print("\nYou're ready to create the database schema!")
print("=" * 60)
