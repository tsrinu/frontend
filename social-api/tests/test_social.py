def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_follow_unfollow(client):
    assert client.post("/social/follow/ch_x").status_code == 204
    assert client.delete("/social/follow/ch_x").status_code == 204


def test_watch_party_create(client):
    r = client.post("/social/watch-party",
                     json={"videoId": "v", "inviteOnly": False})
    assert r.status_code == 201 and "roomId" in r.json()


def test_comments_fixture(client):
    assert len(client.get("/social/comments/v1").json()) >= 2
