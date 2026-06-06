"""Tests for auth-api — sign-in flows, JWT, security health, rate limits, WebAuthn."""
import pyotp


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_jwks(client):
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200 and len(r.json()["keys"]) >= 1


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200 and b"# HELP" in r.content


def test_email_otp_flow(client):
    r = client.post("/auth/email/start", json={"email": "u@x.com"})
    body = r.json()
    assert r.status_code == 202
    assert "devCode" not in body  # security leak guard
    assert "_devCode" in body
    code = body["_devCode"]
    r = client.post("/auth/email/verify", json={"email": "u@x.com", "code": code})
    assert r.status_code == 200
    assert len(r.json()["accessToken"]) > 200


def test_email_wrong_code(client):
    client.post("/auth/email/start", json={"email": "w@x.com"})
    r = client.post("/auth/email/verify", json={"email": "w@x.com", "code": "000000"})
    assert r.status_code == 400


def test_rejects_malformed_email(client):
    assert client.post("/auth/email/start", json={"email": "not-email"}).status_code == 422


def test_rate_limit(client):
    results = [client.post("/auth/email/start",
                            json={"email": f"rl{i}@x.com"}).status_code
                for i in range(7)]
    assert results[:5] == [202] * 5
    assert 429 in results[5:]


def test_attempt_limit(client):
    client.post("/auth/email/start", json={"email": "att@x.com"})
    for _ in range(5):
        client.post("/auth/email/verify", json={"email": "att@x.com", "code": "111111"})
    r = client.post("/auth/email/verify", json={"email": "att@x.com", "code": "111111"})
    assert r.status_code == 429


def test_sso_dev_fallback_when_no_keys(client):
    """Without GOOGLE_CLIENT_ID set, DEV_MODE allows email-in-body."""
    assert client.post("/auth/sso/google", json={"email": "sso@x.com"}).status_code == 200


def test_sso_unknown_provider(client):
    assert client.post("/auth/sso/twitter", json={"email": "x@x.com"}).status_code == 422


def test_2fa_flow(client, headers):
    r = client.post("/auth/2fa/setup", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["recoveryCodes"]) == 10
    code = pyotp.TOTP(data["secret"]).now()
    assert client.post("/auth/2fa/verify", headers=headers,
                        json={"code": code}).status_code == 200
    assert client.post("/auth/2fa/verify", headers=headers,
                        json={"code": "000000"}).status_code == 400


def test_security_health(client, headers):
    r = client.get("/auth/security/health", headers=headers)
    assert r.status_code == 200
    assert 0 <= r.json()["score"] <= 100


def test_bogus_token(client):
    assert client.get("/auth/security/health",
                       headers={"Authorization": "Bearer junk"}).status_code == 401


def test_introspect(client, headers, token):
    assert client.post("/internal/introspect", headers=headers).json()["active"] is True
    assert client.post("/internal/introspect",
                        headers={"Authorization": "Bearer junk"}).json()["active"] is False


def test_passkey_register_requires_auth(client):
    assert client.post("/auth/passkey/register/challenge",
                        json={"email": "x@x.com"}).status_code == 401


def test_passkey_register_challenge(client, headers):
    r = client.post("/auth/passkey/register/challenge",
                     headers=headers, json={"email": "test@example.com"})
    assert r.status_code == 200
    opts = r.json()
    assert "challenge" in opts
    assert opts["rp"]["id"] == "localhost"


def test_passkey_login_no_creds(client):
    assert client.post("/auth/passkey/login/challenge",
                        json={"email": "ghost@x.com"}).status_code == 404
