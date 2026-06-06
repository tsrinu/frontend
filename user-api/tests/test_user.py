"""Tests for user-api in isolation (stubbed JWT verify)."""
import jwt
import time
import pytest


@pytest.fixture
def stub_jwt(app_module, monkeypatch):
    """Stub _verify so we don't need a running auth-api to test user-api."""
    def fake_verify(token):
        if token == "bogus":
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="bad")
        return {"sub": "usr_test123", "email": "test@example.com"}
    monkeypatch.setattr(app_module, "_verify", fake_verify)
    return fake_verify


@pytest.fixture
def headers():
    return {"Authorization": "Bearer fake-token-good"}


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_metrics(client):
    assert client.get("/metrics").status_code == 200


def test_users_me(client, stub_jwt, headers):
    r = client.get("/users/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_users_me_bogus_token(client, stub_jwt):
    assert client.get("/users/me",
                       headers={"Authorization": "Bearer bogus"}).status_code == 401


def test_devices_list_and_signout_all(client, stub_jwt, headers):
    n0 = len(client.get("/users/me/devices", headers=headers).json())
    assert n0 == 2
    assert client.delete("/users/me/devices/all", headers=headers).status_code == 204
    n1 = len(client.get("/users/me/devices", headers=headers).json())
    assert n1 == 1


def test_pin_lifecycle_scrypt_hashed(client, stub_jwt, headers, app_module):
    assert client.post("/users/me/pin", headers=headers,
                        json={"pin": "1357"}).status_code == 204
    # Verify PIN is hashed, not plaintext
    stored = list(app_module.PINS.values())[0]
    assert isinstance(stored["hash"], bytes) and len(stored["hash"]) == 32
    assert stored["hash"] != b"1357"
    # Correct PIN verifies
    assert client.post("/users/me/pin/verify", headers=headers,
                        json={"pin": "1357"}).status_code == 200
    # Wrong PIN rejected
    assert client.post("/users/me/pin/verify", headers=headers,
                        json={"pin": "9999"}).status_code == 401


def test_pin_rejects_all_same(client, stub_jwt, headers):
    assert client.post("/users/me/pin", headers=headers,
                        json={"pin": "0000"}).status_code == 400


def test_pin_rejects_non_numeric(client, stub_jwt, headers):
    assert client.post("/users/me/pin", headers=headers,
                        json={"pin": "abcd"}).status_code == 400


def test_privacy_six_flags(client, stub_jwt, headers):
    r = client.get("/users/me/privacy", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 6


def test_profile_cap_5(client, stub_jwt, headers):
    for i in range(4):
        client.post("/users/me/profiles", headers=headers,
                     json={"name": f"p{i}", "isKidProfile": False})
    r = client.post("/users/me/profiles", headers=headers,
                     json={"name": "6th", "isKidProfile": False})
    assert r.status_code == 400


def test_profile_invalid_age(client, stub_jwt, headers):
    assert client.post("/users/me/profiles", headers=headers,
                        json={"name": "p", "age": 999,
                              "isKidProfile": True}).status_code == 422
