"""Confirm that revenue endpoints reject anonymous requests."""

def test_super_chat_requires_auth(unauth_client):
    r = unauth_client.post("/billing/super-chat",
        json={"streamId": "s", "amount": 50, "message": "hi"})
    assert r.status_code == 401


def test_subscribe_requires_auth(unauth_client):
    r = unauth_client.post("/billing/memberships/subscribe",
        json={"tierId": "tier_supporter", "paymentMethodId": "pm_x"})
    assert r.status_code == 401


def test_gift_subs_requires_auth(unauth_client):
    r = unauth_client.post("/billing/gift-subs",
        json={"streamId": "s", "count": 25, "tierId": "tier_supporter"})
    assert r.status_code == 401


def test_earnings_requires_auth(unauth_client):
    r = unauth_client.get("/billing/creator/earnings?range=30d")
    assert r.status_code == 401


def test_tier_list_remains_public(unauth_client):
    """Tier listing is intentionally public — pricing page needs it."""
    r = unauth_client.get("/billing/memberships/tiers/ch_demo")
    assert r.status_code == 200
