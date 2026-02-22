"""Pytest configuration and fixtures. Set test env before any app import."""

import os
import tempfile

import pytest

# Use file-based SQLite so all connections share the same DB (in-memory can differ per connection)
_test_db_dir = tempfile.gettempdir()
_test_db_path = os.path.join(_test_db_dir, "ai_compliance_backend_test.sqlite")
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", f"sqlite:///{_test_db_path}")
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test-dummy-for-pytest")
os.environ["USE_LOCAL_EMBEDDINGS"] = os.environ.get("USE_LOCAL_EMBEDDINGS", "true")

# Clear config cache so get_settings() uses test env when app is first loaded
from app.config import get_settings

get_settings.cache_clear()


def get_client():
    """Return a FastAPI TestClient for the app (lifespan runs)."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    # Ensure tables exist (lifespan runs on first request; explicit init for file DB)
    from app.database import init_db

    init_db()
    return client


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return get_client()
