def test_security_headers_present(client):
    r = client.get("/healthz")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "x-request-id" in r.headers


def test_no_devCode_in_response(client):
    """The devCode security leak must not return — even in DEV_MODE it's _devCode."""
    r = client.post("/auth/email/start", json={"email": "leak@test.com"})
    assert "devCode" not in r.json()


def test_request_id_round_trip(client):
    r = client.get("/healthz", headers={"X-Request-Id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
