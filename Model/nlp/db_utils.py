"""
Database utilities — connection helpers for the warehouse DB.
Reused by populate_skills.py, generate_embeddings.py, and recommender.py.
"""

import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "jobs_dw",
    "user": "warehouse",
    "password": "warehouse",
}


@contextmanager
def get_connection():
    """Yield a psycopg2 connection, auto-close on exit."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(conn, commit=True):
    """Yield a cursor. Commits on success, rolls back on error."""
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
