"""Minimal debug: verify dependency_overrides works."""
import sys
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient

# Must import schemas BEFORE creating engine to register models
sys.path.insert(0, r"c:\Users\aliha\OneDrive\Desktop\Fastapi test project\MYproject")
import schemas  # noqa
from main import app, get_session

# Check what's in metadata
print("Tables in metadata:", list(SQLModel.metadata.tables.keys()))

# Create in-memory test engine
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(test_engine)

# Verify tables exist
from sqlalchemy import inspect
inspector = inspect(test_engine)
print("Tables in test DB:", inspector.get_table_names())

# Override
def override_get_session():
    print(">>> OVERRIDE CALLED <<<", file=sys.stderr)
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session
print("Override set for:", get_session)
print("Current overrides:", app.dependency_overrides)

client = TestClient(app)
try:
    r = client.post("/register", json={"username": "test", "email": "test@test.com", "password": "pw123"})
    print("Status:", r.status_code)
    print("Body:", r.text[:300])
except Exception as e:
    print("Error:", e)
finally:
    app.dependency_overrides.clear()
