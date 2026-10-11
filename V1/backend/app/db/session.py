from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _make_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        db_path = url.replace("sqlite:///", "", 1)
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _make_engine(get_settings().resolved_database_url)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def configure_engine(url: str) -> Engine:
    """Replace the global engine (used by tests to point at a temp database)."""
    global _engine, _SessionLocal
    _engine = _make_engine(url)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
