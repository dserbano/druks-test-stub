from __future__ import annotations

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DEFAULT_DB_URL = "sqlite:///./inventory.db"


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def make_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("INVENTORY_DB_URL", DEFAULT_DB_URL)
    return create_engine(url, future=True, **_engine_kwargs(url))


engine: Engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(bind: Engine | None = None) -> None:
    """Create all tables. Imports models to populate metadata."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=bind or engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
