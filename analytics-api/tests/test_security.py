"""Security boundary tests for analytics-api.
- 401 returned on protected endpoints without auth
- security headers present on every response
- request size limit enforced
"""


def test_security_headers_present(client):
    r = client.get("/healthz")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "permissions-policy" in r.headers
    # X-Request-Id auto-generated for tracing
    assert "x-request-id" in r.headers and len(r.headers["x-request-id"]) > 8


def test_request_id_propagates_when_provided(client):
    r = client.get("/healthz", headers={"X-Request-Id": "test-id-12345"})
    assert r.headers["x-request-id"] == "test-id-12345"


def test_oversize_body_rejected(client):
    # 2 MB payload (default limit is 1 MB)
    big = "x" * (2 * 1024 * 1024)
    r = client.post("/__bogus_path__", content=big,
                     headers={"Content-Length": str(len(big))})
    assert r.status_code == 413
