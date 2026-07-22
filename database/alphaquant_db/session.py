"""SQLAlchemy engine / session helpers."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alphaquant_db.models import Base
from alphaquant_shared.config import get_settings


@lru_cache(maxsize=1)
def get_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    return create_engine(url or settings.database_url, pool_pre_ping=True)


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), autoflush=False, autocommit=False)


def init_db(url: str | None = None) -> None:
    """Create tables (dev bootstrap). Prefer Alembic in production."""
    engine = get_engine(url)
    Base.metadata.create_all(bind=engine)
