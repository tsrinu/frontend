def test_ingest_requires_auth(unauth_client):
    r = unauth_client.post("/analytics/events",
        json={"name": "click", "properties": {}})
    assert r.status_code == 401


def test_read_recent_remains_public(unauth_client):
    """Reading event stream stays public (dashboard endpoint)."""
    assert unauth_client.get("/analytics/events/recent").status_code == 200
