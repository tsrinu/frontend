def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_get_stream(client):
    r = client.get("/live/streams/stream_demo")
    assert r.status_code == 200 and r.json()["viewerCount"] == 12438


def test_poll_create_vote_bounds(client):
    r = client.post("/live/streams/s/poll",
                     json={"question": "?", "options": ["a", "b", "c"],
                           "durationSec": 60})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.post(f"/live/streams/s/poll/{pid}/vote",
                        json={"optionIndex": 0}).status_code == 204
    assert client.post(f"/live/streams/s/poll/fake/vote",
                        json={"optionIndex": 0}).status_code == 404
    assert client.post(f"/live/streams/s/poll/{pid}/vote",
                        json={"optionIndex": 99}).status_code == 400


def test_poll_rejects_single_option(client):
    assert client.post("/live/streams/s/poll",
                        json={"question": "?", "options": ["a"],
                              "durationSec": 60}).status_code == 422
