from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None) -> Engine:
    database_url = url or os.environ.get("SHOP_DATABASE_URL", "sqlite:///./shop.db")
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _ensure_default_engine() -> sessionmaker[Session]:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = make_engine()
        Base.metadata.create_all(_engine)
        _SessionLocal = make_session_factory(_engine)
    return _SessionLocal


def get_session() -> Iterator[Session]:
    factory = _ensure_default_engine()
    session = factory()
    try:
        yield session
    finally:
        session.close()
