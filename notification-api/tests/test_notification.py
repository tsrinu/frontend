def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_inbox_has_items(client):
    assert len(client.get("/notifications/inbox").json()) >= 4


def test_preferences_get_put(client):
    r = client.get("/notifications/preferences")
    assert r.status_code == 200
    body = r.json()
    body["push"]["enabled"] = False
    r = client.put("/notifications/preferences", json=body)
    assert r.status_code == 200
