def test_create_poll_requires_auth(unauth_client):
    r = unauth_client.post("/live/streams/s/poll",
        json={"question": "?", "options": ["a", "b"], "durationSec": 60})
    assert r.status_code == 401


def test_vote_poll_requires_auth(unauth_client):
    r = unauth_client.post("/live/streams/s/poll/p/vote",
        json={"optionIndex": 0})
    assert r.status_code == 401


def test_create_prediction_requires_auth(unauth_client):
    r = unauth_client.post("/live/streams/s/prediction",
        json={"question": "?", "outcomes": [{"label":"y","color":"g"},{"label":"n","color":"r"}],
              "durationSec": 60})
    assert r.status_code == 401


def test_stream_read_remains_public(unauth_client):
    """Stream metadata is public — viewer count etc."""
    assert unauth_client.get("/live/streams/stream_demo").status_code == 200
