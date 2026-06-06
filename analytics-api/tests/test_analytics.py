def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_event_ingest(client):
    r = client.post("/analytics/events",
                     json={"name": "video_started", "properties": {"id": "v1"}})
    assert r.status_code == 202
    assert r.json()["received"] is True


def test_oversize_name_rejected(client):
    r = client.post("/analytics/events",
                     json={"name": "x" * 200, "properties": {}})
    assert r.json()["received"] is False


def test_recent_returns_list(client):
    client.post("/analytics/events", json={"name": "view", "properties": {}})
    r = client.get("/analytics/events/recent?limit=10")
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_recent_limit_clamped(client):
    r = client.get("/analytics/events/recent?limit=10000")
    assert r.status_code == 200


def test_watch_time_today(client):
    r = client.get("/analytics/watch-time/today")
    assert r.status_code == 200 and r.json()["totalMinutesWatched"] == 47
