def test_follow_requires_auth(unauth_client):
    assert unauth_client.post("/social/follow/ch_x").status_code == 401


def test_unfollow_requires_auth(unauth_client):
    assert unauth_client.delete("/social/follow/ch_x").status_code == 401


def test_post_comment_requires_auth(unauth_client):
    r = unauth_client.post("/social/comments/v1", json={"body": "hi"})
    assert r.status_code == 401


def test_create_watch_party_requires_auth(unauth_client):
    r = unauth_client.post("/social/watch-party",
        json={"videoId": "v", "inviteOnly": False})
    assert r.status_code == 401


def test_read_comments_remains_public(unauth_client):
    """Reading comments is public — they show below the video."""
    assert unauth_client.get("/social/comments/v1").status_code == 200
