"""
Seadot Database State & Session Management (SQLAlchemy ORM Pattern)
Scoped session pattern untuk lifecycle management SQLite database.
"""

import os
import sys
import types
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

backend_root = Path(__file__).resolve().parent.parent
if "seadot_backend" not in sys.modules:
    pkg = types.ModuleType("seadot_backend")
    pkg.__path__ = [str(backend_root)]
    sys.modules["seadot_backend"] = pkg

# Base class untuk declarative model registry
Base = declarative_base()
_ENGINE_CACHE = {}


def _resolve_db_path(db_path: str = "seadot.db") -> str:
    """Resolve a database path relative to the db folder or accept absolute paths."""
    if not db_path or db_path == ":memory:":
        return db_path
    path = Path(db_path)
    if path.is_absolute():
        return str(path)
    return str((Path(__file__).resolve().parent / path).resolve())


def _get_or_create_engine(db_path: str = "seadot.db"):
    """Return a process-local engine, reusing one per database path."""
    resolved = _resolve_db_path(db_path)
    if resolved not in _ENGINE_CACHE:
        _ENGINE_CACHE[resolved] = create_engine(
            f"sqlite:///{resolved}",
            connect_args={"check_same_thread": False},
            echo=False,
            pool_pre_ping=True,
        )
    return _ENGINE_CACHE[resolved]


def get_db_state(db_path: str = "seadot.db"):
    """Get database engine and session factory."""
    engine = _get_or_create_engine(db_path)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db_session: scoped_session = scoped_session(session_factory)
    return {
        "engine": engine,
        "session_factory": session_factory,
        "get_db_session": lambda: db_session(),
    }


def create_session(db_path: str = "seadot.db"):
    """Compatibility factory used by tests and callers expecting a Session object."""
    state = get_db_state(db_path)
    init_database(db_path)
    return state["session_factory"]()


def init_database(db_path: str = "seadot.db"):
    """Initialize database tables."""
    from seadot_backend.db.models import Base, DownloadStatus

    full_path = _resolve_db_path(db_path)
    engine = _get_or_create_engine(full_path)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        for table in ("downloads", "download_history"):
            for status in DownloadStatus:
                connection.execute(
                    text(f"UPDATE {table} SET status = :value WHERE status = :name"),
                    {"value": status.value, "name": status.name},
                )


def get_db():
    """Get database session instance for the default database path."""
    return get_db_session()


def get_db_session(db_path: str = "seadot.db"):
    """Get a SQLAlchemy session bound to the requested database path."""
    engine = _get_or_create_engine(db_path)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


def close_all_sessions():
    """Dispose all pooled database engines so temp SQLite files can be deleted on Windows."""
    for path, engine in list(_ENGINE_CACHE.items()):
        try:
            engine.dispose()
        except Exception:
            pass
    _ENGINE_CACHE.clear()
    for attr in ["_engine", "_db_path"]:
        if hasattr(get_db_session, attr):
            delattr(get_db_session, attr)