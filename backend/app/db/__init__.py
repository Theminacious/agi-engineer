"""Database base, connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from .base import Base

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.api_env == "development",
    pool_pre_ping=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
