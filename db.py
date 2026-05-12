"""Database helpers for the quiz application."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent

# Streamlit Cloud can import modules with either bare names (db/models)
# or package names (e.g. chinese_hsk_app.db/models). Keep a single module
# instance in sys.modules to avoid duplicate SQLAlchemy metadata declarations.
_PKG_NAME = BASE_DIR.name
if __name__ == "db":
    sys.modules.setdefault(f"{_PKG_NAME}.db", sys.modules[__name__])
elif __name__.endswith(".db"):
    sys.modules.setdefault("db", sys.modules[__name__])

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_database_url(raw_url: str) -> str:
    """Normalize DB URL for SQLAlchemy driver compatibility."""
    url = raw_url.strip()
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _get_external_database_url() -> str:
    """Read DB URL from env or Streamlit secrets (for Cloud deployment)."""
    env_candidates = ["HSK_DATABASE_URL", "DATABASE_URL"]
    for key in env_candidates:
        value = os.environ.get(key, "").strip()
        if value:
            return _normalize_database_url(value)

    # Optional fallback for Streamlit secrets.
    try:
        import streamlit as st  # type: ignore

        secret_value = str(st.secrets.get("HSK_DATABASE_URL", "")).strip()
        if secret_value:
            return _normalize_database_url(secret_value)
    except Exception:
        pass

    return ""


def _can_write_to(path: Path) -> bool:
    """Return True if the directory is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _select_database_path() -> Path:
    """Choose a writable database location.

    On Streamlit Community Cloud, source files under /mount/src are read-only.
    Fall back to /tmp so writes (login/mastery updates) can succeed.
    """
    env_override = os.environ.get("HSK_DB_PATH", "").strip()
    if env_override:
        return Path(env_override)

    default_path = DATA_DIR / "quizzes.sqlite3"
    if _can_write_to(DATA_DIR):
        return default_path

    tmp_dir = Path(tempfile.gettempdir()) / "chinese_hsk_app_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / "quizzes.sqlite3"


EXTERNAL_DATABASE_URL = _get_external_database_url()
if EXTERNAL_DATABASE_URL:
    DATABASE_PATH = None
    DATABASE_URL = EXTERNAL_DATABASE_URL
    engine = create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
else:
    DATABASE_PATH = _select_database_path()
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        future=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create all database tables and apply lightweight column migrations."""
    import models  # noqa: F401  # Ensure models are registered with metadata

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    """Add new columns to existing tables when they are missing.

    Streamlit Cloud and existing local DBs may carry an older schema. We do not
    rely on Alembic yet — each new column has its presence checked first and
    is added with ALTER TABLE only when needed.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    additions = {
        "user_vocab_mastery": [
            ("fsrs_state", "INTEGER"),
            ("fsrs_step", "INTEGER"),
            ("fsrs_stability", "FLOAT"),
            ("fsrs_difficulty", "FLOAT"),
            ("fsrs_due_at", "TIMESTAMP"),
            ("fsrs_last_review_at", "TIMESTAMP"),
            ("fsrs_last_rating", "INTEGER"),
        ],
    }

    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            current = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name, column_type in columns:
                if column_name in current:
                    continue
                connection.execute(
                    text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
                )


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy session and ensure it is closed."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
