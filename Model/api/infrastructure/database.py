"""
Database — connection pool and session management.
Infrastructure layer: only this module knows about SQLAlchemy/psycopg2.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from api.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency: yields a DB session, auto-closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
