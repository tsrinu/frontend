"""Conftest scoped to auth-api only — loads as a package since it uses relative imports."""
import os, sys, tempfile, pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_test_db = os.path.join(tempfile.gettempdir(), "auth-api-test.db")
if os.path.exists(_test_db):
    os.remove(_test_db)

os.environ.setdefault("JWT_KEY_DIR", "/tmp/auth-api-test-keys")
os.environ.setdefault("DEV_MODE", "true")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

@pytest.fixture(scope="session")
def auth_app():
    for k in list(sys.modules):
        if k.startswith("app"):
            del sys.modules[k]
    import app.main as m
    return m

@pytest.fixture
def client(auth_app):
    auth_app._RATE_BUCKETS.clear()
    with TestClient(auth_app.app) as c:
        yield c

@pytest.fixture
def token(client):
    client.post("/auth/email/start", json={"email": "test@example.com"})
    r = client.post("/auth/email/start", json={"email": "test@example.com"})
    code = r.json()["_devCode"]
    r = client.post("/auth/email/verify", json={"email": "test@example.com", "code": code})
    return r.json()["accessToken"]

@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}
