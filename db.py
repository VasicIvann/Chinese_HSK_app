"""Database helpers for the quiz application."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
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

DATABASE_PATH = DATA_DIR / "quizzes.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create all database tables."""
    import models  # noqa: F401  # Ensure models are registered with metadata

    Base.metadata.create_all(bind=engine)


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
