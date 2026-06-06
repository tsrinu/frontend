"""Tests for billing-api in isolation."""

def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_4_tiers(client):
    assert len(client.get("/billing/memberships/tiers/ch_x").json()) == 4


def test_subscribe_unknown_tier(client):
    assert client.post("/billing/memberships/subscribe",
                        json={"tierId": "fake",
                              "paymentMethodId": "pm_x"}).status_code == 400


def test_subscribe_valid(client):
    assert client.post("/billing/memberships/subscribe",
                        json={"tierId": "tier_supporter",
                              "paymentMethodId": "pm_x"}).status_code == 201


def test_super_chat_colors(client):
    assert client.post("/billing/super-chat",
                        json={"streamId": "s", "amount": 50,
                              "message": "hi"}).json()["color"] == "gold"
    assert client.post("/billing/super-chat",
                        json={"streamId": "s", "amount": 5,
                              "message": "hi"}).json()["color"] == "blue"


def test_super_chat_rejects_zero(client):
    assert client.post("/billing/super-chat",
                        json={"streamId": "s", "amount": 0,
                              "message": "hi"}).status_code == 422


def test_gift_sub_wrong_count(client):
    assert client.post("/billing/gift-subs",
                        json={"streamId": "s", "count": 7,
                              "tierId": "tier_supporter"}).status_code == 400


def test_gift_sub_valid(client):
    assert client.post("/billing/gift-subs",
                        json={"streamId": "s", "count": 25,
                              "tierId": "tier_supporter"}).status_code == 201


def test_earnings_invalid_range(client):
    assert client.get("/billing/creator/earnings?range=lifetime").status_code == 400


def test_regional_inr(client):
    assert client.get("/billing/pricing/regional?region=IN").json()["currency"] == "INR"
