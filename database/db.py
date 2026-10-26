"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  RESILIENT DATABASE MANAGER (Dual PostgreSQL / Fallback Engine)
================================================================================
  - Primary Engine: PostgreSQL via psycopg2 (Full ACID, Stored Procedures, Triggers)
  - Resilient Fallback Engine: SQLite3 (Automatically active if PostgreSQL service
    is offline or not yet started on localhost:5432).
================================================================================
"""

import os
import re
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from config import Config
from database.sqlite_fallback import SQLITE_PATH, init_sqlite_database

logger = logging.getLogger(__name__)

# Ensure fallback database is seeded and ready
init_sqlite_database()

def get_db_params():
    return {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "dbname": Config.DB_NAME,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "connect_timeout": 1
    }

def is_postgres_available():
    """Checks if PostgreSQL server is accepting connections."""
    try:
        conn = psycopg2.connect(**get_db_params())
        conn.close()
        return True
    except Exception:
        return False

def test_connection():
    """
    Tests database connection status.
    Returns (True, details) if PostgreSQL is live, or (False, details) with fallback note.
    """
    try:
        conn = psycopg2.connect(**get_db_params())
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
        conn.close()
        return True, ver
    except Exception as e:
        return False, f"PostgreSQL Offline (Connection Refused on port {Config.DB_PORT}). Using SQLite Local Engine."

def adapt_sql_for_sqlite(sql):
    """Adapts PostgreSQL SQL dialect to SQLite dialect where necessary."""
    # 1. Parameter placeholder %s -> ?
    clean_sql = sql.replace("%s", "?")
    
    # 2. Case-insensitive ILIKE -> LIKE
    clean_sql = re.sub(r'\bILIKE\b', 'LIKE', clean_sql, flags=re.IGNORECASE)
    
    # 3. Strip pessimistic lock FOR UPDATE (SQLite uses database file locks)
    clean_sql = re.sub(r'\bFOR\s+UPDATE\b', '', clean_sql, flags=re.IGNORECASE)
    
    # 4. Interval date arithmetic: CURRENT_DATE + (? || ' days')::INTERVAL -> date('now', '+' || ? || ' days')
    clean_sql = re.sub(
        r"CURRENT_DATE\s*\+\s*\(\s*\?\s*\|\|\s*' days'\s*\)::INTERVAL",
        "date('now', '+' || ? || ' days')",
        clean_sql,
        flags=re.IGNORECASE
    )

    # 5. DATE(payment_date) = CURRENT_DATE -> date(payment_date) = date('now')
    clean_sql = re.sub(
        r"DATE\((.*?)\)\s*=\s*CURRENT_DATE",
        r"date(\1) = date('now')",
        clean_sql,
        flags=re.IGNORECASE
    )

    return clean_sql.strip()

class ResilientCursor:
    def __init__(self, raw_cur, is_sqlite=False):
        self.raw_cur = raw_cur
        self.is_sqlite = is_sqlite

    def execute(self, sql, params=None):
        if self.is_sqlite:
            adapted = adapt_sql_for_sqlite(sql)
            return self.raw_cur.execute(adapted, params or ())
        return self.raw_cur.execute(sql, params or ())

    def executemany(self, sql, seq_of_params):
        if self.is_sqlite:
            adapted = adapt_sql_for_sqlite(sql)
            return self.raw_cur.executemany(adapted, seq_of_params)
        return self.raw_cur.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self.raw_cur.fetchone()
        if row is not None and self.is_sqlite:
            # If row has keys/mapping, return dict or subscriptable
            if isinstance(row, sqlite3.Row):
                return row
            elif hasattr(row, 'keys'):
                return row
        return row

    def fetchall(self):
        rows = self.raw_cur.fetchall()
        return rows

    @property
    def rowcount(self):
        return self.raw_cur.rowcount

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.raw_cur, '__exit__'):
            return self.raw_cur.__exit__(exc_type, exc_val, exc_tb)
        self.raw_cur.close()

class ResilientConnection:
    def __init__(self, raw_conn, is_sqlite=False):
        self.raw_conn = raw_conn
        self.is_sqlite = is_sqlite

    def cursor(self, *args, **kwargs):
        if self.is_sqlite:
            return ResilientCursor(self.raw_conn.cursor(), is_sqlite=True)
        return ResilientCursor(self.raw_conn.cursor(*args, **kwargs), is_sqlite=False)

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        self.raw_conn.close()

@contextmanager
def get_db_connection():
    """
    Context manager yielding an active database connection with auto-commit/rollback.
    Prioritizes PostgreSQL; seamlessly falls back to SQLite if PostgreSQL is offline.
    """
    if is_postgres_available():
        conn = None
        try:
            conn = psycopg2.connect(**get_db_params())
            yield ResilientConnection(conn, is_sqlite=False)
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"PostgreSQL connection error: {e}")
            raise e
        finally:
            if conn:
                conn.close()
    else:
        # SQLite Fallback Connection
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield ResilientConnection(conn, is_sqlite=True)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"SQLite fallback error: {e}")
            raise e
        finally:
            conn.close()

def execute_query(sql, params=None):
    """Executes a SELECT query and returns a list of dictionary rows."""
    if is_postgres_available():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
    else:
        sqlite_sql = adapt_sql_for_sqlite(sql)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(sqlite_sql, params or ())
            rows = cur.fetchall()
            return [dict(row) for row in rows]

def execute_query_one(sql, params=None):
    """Executes a SELECT query returning a single row as a dictionary, or None."""
    if is_postgres_available():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()
    else:
        sqlite_sql = adapt_sql_for_sqlite(sql)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(sqlite_sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None

def execute_dml(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and returns affected rows."""
    if is_postgres_available():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.rowcount
    else:
        sqlite_sql = adapt_sql_for_sqlite(sql)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(sqlite_sql, params or ())
            return cur.rowcount

def execute_returning(sql, params=None):
    """Executes an INSERT or UPDATE statement with RETURNING clause."""
    if is_postgres_available():
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()
    else:
        sqlite_sql = adapt_sql_for_sqlite(sql)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(sqlite_sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None
