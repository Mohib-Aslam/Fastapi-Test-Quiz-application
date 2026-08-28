
import os
import sys
from pathlib import Path

# main.py reads SECRET_KEY from the environment at import time, so it must
# be set before "import main" happens anywhere.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-do-not-use-in-prod")

# main.py and schemas.py import each other with plain "import schemas" /
# "from main import app", which only works if MYproject/ is on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session




from sqlmodel.pool import StaticPool

@pytest.fixture(name="client")
def client_fixture():
    """Provide a fresh in-memory database and TestClient for every test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,          
    )
    SQLModel.metadata.create_all(test_engine)

    def _override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def register_and_login(client):
    """Factory fixture: call it with a username to register + login and get auth headers."""
    _counter = 0

    def _do(username=None):
        nonlocal _counter
        if username is None:
            _counter += 1
            username = f"user{_counter}"
        email = f"{username}@example.com"
        client.post(
            "/register",
            json={"username": username, "email": email, "password": "password123"},
        )
        r = client.post("/login", data={"username": username, "password": "password123"})
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _do
