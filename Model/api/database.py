"""
Compatibility module that exposes DB objects at api.database.
Internals remain in api.infrastructure.database.
"""

from api.infrastructure.database import SessionLocal, engine, get_db

__all__ = ["engine", "SessionLocal", "get_db"]
