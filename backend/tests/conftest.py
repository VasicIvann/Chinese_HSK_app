"""Test fixtures: in-memory SQLite + FastAPI TestClient."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Configure environment BEFORE importing the app.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="hsk_api_tests_"))
_DB_PATH = _TMP_DIR / "test.db"
os.environ["HSK_DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-prod"
os.environ["ANTHROPIC_API_KEY"] = "sk-test"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["ALLOWED_REGISTRATION_EMAILS"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base, register_models  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Entry, Quiz  # noqa: E402


get_settings.cache_clear()
register_models()


@pytest.fixture(scope="session", autouse=True)
def _setup_database() -> Iterator[None]:
    """Create tables once per test session, drop them at the end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _truncate_between_tests() -> Iterator[None]:
    """Wipe table content between tests to keep them isolated."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def seed_quizzes() -> None:
    """Insert a couple of quizzes with one entry each."""
    from app.db.session import SessionLocal

    now = __import__("datetime").datetime.utcnow()
    with SessionLocal() as session:
        hsk1 = Quiz(key="HSK1", title="HSK 1", description="Niveau 1", level=1, created_at=now, updated_at=now)
        hsk2 = Quiz(key="HSK2", title="HSK 2", description="Niveau 2", level=2, created_at=now, updated_at=now)
        session.add_all([hsk1, hsk2])
        session.flush()
        session.add_all(
            [
                Entry(
                    quiz_id=hsk1.id,
                    hanzi="爱",
                    pinyin="ài",
                    translation="aimer",
                    is_active=True,
                    created_at=now,
                ),
                Entry(
                    quiz_id=hsk2.id,
                    hanzi="北京",
                    pinyin="běi jīng",
                    translation="Pékin",
                    is_active=True,
                    created_at=now,
                ),
            ]
        )
        session.commit()
