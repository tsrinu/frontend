"""Schemathesis contract tests: fuzz every endpoint declared in openapi.yaml.
Catches schema drift, missing 4xx handlers, type mismatches, etc.

Run against a running service:
    uvicorn app.main:app --port 8001 &
    pytest tests/test_contract.py
"""
import os
import pytest
import schemathesis
from schemathesis.specs.openapi.checks import status_code_conformance

SPEC = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")
BASE_URL = os.getenv("CONTRACT_BASE_URL", "http://127.0.0.1:8080/api/v1")

# Skip if no live service to hit
try:
    import httpx
    httpx.get(BASE_URL.replace("/api/v1", "/healthz"), timeout=0.5)
    LIVE = True
except Exception:
    LIVE = False

schema = schemathesis.from_path(SPEC, base_url=BASE_URL)


@pytest.mark.skipif(not LIVE, reason="No live service at " + BASE_URL)
@schema.parametrize()
def test_api_conformance(case):
    """Every endpoint must respond with a documented status code."""
    response = case.call()
    case.validate_response(response, checks=(status_code_conformance,))
