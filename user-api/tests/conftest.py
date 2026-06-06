"""Conftest scoped to user-api only."""
import importlib.util, os, sys, pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_PUBLIC_KEY_URL", "http://localhost:8001/.well-known/jwks.json")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

@pytest.fixture(scope="session")
def app_module():
    # purge ws.py cache if it exists (avoid sibling collisions across APIs)
    for k in ("ws", "main"):
        if k in sys.modules:
            del sys.modules[k]
    spec = importlib.util.spec_from_file_location("user_main", os.path.join(ROOT, "main.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["main"] = m
    spec.loader.exec_module(m)
    return m

@pytest.fixture
def client(app_module):
    return TestClient(app_module.app)
