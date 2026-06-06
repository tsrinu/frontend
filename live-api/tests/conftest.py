"""Conftest for live-api — uses FastAPI dependency_overrides to stub JWT auth.

In production these endpoints require Bearer tokens; tests stub the
verifier so they don't need a running auth-api.
"""
import importlib.util, os, sys, pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(scope="session")
def app_module():
    for k in ("ws", "main"):
        if k in sys.modules:
            del sys.modules[k]
    spec = importlib.util.spec_from_file_location("live_main", os.path.join(ROOT, "main.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["main"] = m
    spec.loader.exec_module(m)
    return m


def _fake_auth():
    return {"sub": "usr_test", "email": "test@example.com"}


@pytest.fixture
def client(app_module):
    """Client with auth bypassed via FastAPI dependency_overrides."""
    if hasattr(app_module, "_require_auth"):
        app_module.app.dependency_overrides[app_module._require_auth] = _fake_auth
    yield TestClient(app_module.app)
    app_module.app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(app_module):
    """Client WITHOUT auth bypass — for testing 401 responses on protected endpoints."""
    app_module.app.dependency_overrides.clear()
    return TestClient(app_module.app)


@pytest.fixture
def headers():
    return {"Authorization": "Bearer test-token"}
