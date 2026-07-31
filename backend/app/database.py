"""SQLite/SQLAlchemy engine, session management and schema initialisation."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            f"sqlite:///{db_path}",
            # The engine is shared between FastAPI's threadpool and the
            # background queue worker thread.
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            # WAL allows the API (reader) and the worker (writer) to access
            # the database concurrently without "database is locked" errors.
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    """Create all tables if they do not exist yet."""

    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def session_scope() -> Session:
    """Create a standalone session for use outside of FastAPI's DI, e.g. the
    background queue worker thread."""

    return get_session_factory()()


def reset_engine() -> None:
    """Dispose of the current engine/session factory.

    Used by the test suite to point the app at a fresh, temporary database
    between tests.
    """

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
