"""Pytest fixtures — boot every gap-service in-process with FastAPI TestClient."""
import importlib.util
import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAP = os.path.join(ROOT, "gap-services")

_test_db = os.path.join(tempfile.gettempdir(), "distrebute-test.db")
if os.path.exists(_test_db):
    os.remove(_test_db)

os.environ.setdefault("JWT_KEY_DIR", "/tmp/distrebute-test-keys")
os.environ.setdefault("DEV_MODE", "true")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080")


def _flat_load(svc_dir, file, mod_name):
    svc_full = os.path.join(GAP, svc_dir)
    # Strip any previously-injected GAP/* path so sibling module names don't collide (e.g. ws.py)
    sys.path[:] = [p for p in sys.path if not p.startswith(GAP)]
    sys.path.insert(0, svc_full)
    # Drop cached sibling-named modules that would shadow what we're about to load
    for cached in list(sys.modules):
        if cached in ("ws",) or cached.startswith("ws."):
            del sys.modules[cached]
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(svc_full, file))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _package_load_auth():
    auth_full = os.path.join(GAP, "auth-service")
    if auth_full not in sys.path:
        sys.path.insert(0, auth_full)
    if "app" in sys.modules:
        del sys.modules["app"]
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    import app.main as auth_main  # noqa
    return auth_main


@pytest.fixture(scope="session")
def auth_app():
    return _package_load_auth()


@pytest.fixture
def auth_client(auth_app):
    auth_app._RATE_BUCKETS.clear()
    # TestClient as context manager triggers lifespan -> init_db() -> creates tables
    with TestClient(auth_app.app) as c:
        yield c


@pytest.fixture
def user_client(auth_client):
    user = _flat_load("user-service", "main.py", "user_main_test")
    user._jwks_cache.clear()
    user._jwks_cache.update(auth_client.get("/.well-known/jwks.json").json())
    user._jwks_cache["fetched_at"] = 1.0
    return TestClient(user.app)


@pytest.fixture
def billing_client():
    return TestClient(_flat_load("billing-service", "main.py", "billing_main_test").app)


@pytest.fixture
def live_client():
    return TestClient(_flat_load("live-service", "main.py", "live_main_test").app)


@pytest.fixture
def social_client():
    return TestClient(_flat_load("social-service", "main.py", "social_main_test").app)


@pytest.fixture
def notify_client():
    return TestClient(_flat_load("notification-service", "main.py", "notify_main_test").app)


@pytest.fixture
def analytics_client():
    return TestClient(_flat_load("analytics-service", "main.py", "analytics_main_test").app)


@pytest.fixture
def auth_token(auth_client, auth_app):
    auth_app._RATE_BUCKETS.clear()
    auth_client.post("/auth/email/start", json={"email": "test@example.com"})
    r = auth_client.post("/auth/email/start", json={"email": "test@example.com"})
    code = r.json()["_devCode"]
    r = auth_client.post("/auth/email/verify",
                          json={"email": "test@example.com", "code": code})
    return r.json()["accessToken"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
