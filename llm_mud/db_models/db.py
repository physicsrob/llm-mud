"""Database connection utilities."""

from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


# Database connection functions
def get_engine(db_url: Optional[str] = None):
    """Create a database engine."""
    # Default to SQLite for development
    if db_url is None:
        db_url = "sqlite:///llm_mud.db"
    return create_engine(db_url)


def init_db(engine=None):
    """Initialize the database."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(engine=None):
    """Get a session factory."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


def get_session(engine=None):
    """Get a database session."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
