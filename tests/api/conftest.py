"""
Shared fixtures for API tests.
"""
import pytest
from fastapi.testclient import TestClient

TEST_API_KEY = "test-key-abc123"


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    """Inject a known API key before each test and reset the auth module."""
    import graphbus_api.auth as auth_mod
    monkeypatch.setenv("GRAPHBUS_API_KEY", TEST_API_KEY)
    auth_mod.init_api_key()
    yield
    # Reset so next test gets a clean slate
    auth_mod._api_key = ""


@pytest.fixture()
def client(set_api_key):
    """FastAPI TestClient with the API mounted."""
    from graphbus_api.main import app
    from graphbus_api.store import negotiation_store

    # Clear negotiation store between tests
    negotiation_store._sessions.clear()
    negotiation_store._proposals.clear()
    negotiation_store._commits.clear()
    negotiation_store._parties.clear()
    negotiation_store._messages.clear()

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    return {"X-Api-Key": TEST_API_KEY}


@pytest.fixture()
def bad_headers():
    return {"X-Api-Key": "wrong-key"}
