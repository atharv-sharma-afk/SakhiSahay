from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Point every test run at throw-away storage BEFORE the app modules read settings.
_TMP = Path(tempfile.mkdtemp(prefix="sakhisahay-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["QDRANT_PATH"] = str(_TMP / "qdrant")
os.environ["LLM_PROVIDER"] = "none"
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    from app.db.init_db import init_db

    init_db()


@pytest.fixture(scope="session")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def second_user():
    """A second account used to prove per-user isolation of health records."""
    with get_sessionmaker()() as session:
        user = session.get(models.User, "second-user-00000000000000000000")
        if user is None:
            user = models.User(id="second-user-00000000000000000000", display_name="Other")
            session.add(user)
            session.commit()
        return user.id


@pytest.fixture(autouse=True)
def _clean_records():
    yield
    with get_sessionmaker()() as session:
        session.query(models.SymptomRecord).delete()
        session.query(models.PeriodRecord).delete()
        session.commit()
