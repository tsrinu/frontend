def test_inbox_requires_auth(unauth_client):
    assert unauth_client.get("/notifications/inbox").status_code == 401


def test_get_preferences_requires_auth(unauth_client):
    assert unauth_client.get("/notifications/preferences").status_code == 401


def test_set_preferences_requires_auth(unauth_client):
    r = unauth_client.put("/notifications/preferences",
        json={"push": {"enabled": True}, "email": {}, "smartDigest": {}})
    assert r.status_code == 401
