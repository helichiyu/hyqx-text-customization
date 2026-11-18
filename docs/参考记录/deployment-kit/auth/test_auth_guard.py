"""Authentication interceptor tests."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import auth_guard


def _clear_auth_env(monkeypatch):
    monkeypatch.delenv(auth_guard.DIGEST_ENV, raising=False)
    monkeypatch.delenv(auth_guard.PLAIN_ENV, raising=False)


def test_disabled_when_unset(monkeypatch):
    _clear_auth_env(monkeypatch)
    assert auth_guard.auth_enabled() is False
    assert auth_guard.expected_digests() == []
    ok, status, _ = auth_guard.verify("anything")
    assert ok is True
    assert status == 0


def test_digest_env(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(auth_guard.DIGEST_ENV, auth_guard._digest("token-a"))
    ok, status, _ = auth_guard.verify("token-a")
    assert ok is True
    assert status == 0
    ok, status, _ = auth_guard.verify("wrong")
    assert ok is False
    assert status == 403
    ok, status, _ = auth_guard.verify(None)
    assert ok is False
    assert status == 401


def test_plain_env_and_digest_priority(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(auth_guard.PLAIN_ENV, "plain-token")
    assert auth_guard.verify("plain-token")[0] is True
    monkeypatch.setenv(auth_guard.DIGEST_ENV, auth_guard._digest("digest-token"))
    assert auth_guard.verify("digest-token")[0] is True
    assert auth_guard.verify("plain-token")[0] is False


def test_multiple_digests(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(
        auth_guard.DIGEST_ENV,
        f"{auth_guard._digest('client-a')}, {auth_guard._digest('client-b')}",
    )
    assert auth_guard.verify("client-a")[0] is True
    assert auth_guard.verify("client-b")[0] is True
    assert auth_guard.verify("client-c")[0] is False


def test_token_headers_and_whitelist():
    assert auth_guard.token_from({"x-token": " a "}) == "a"
    assert auth_guard.token_from({"token": "b"}) == "b"
    assert auth_guard.token_from({"x-token": "a", "token": "b"}) == "a"
    assert auth_guard.token_from({"x-token": "  "}) is None
    assert auth_guard.is_whitelisted("/health")
    assert auth_guard.is_whitelisted("/health/")
    assert auth_guard.is_whitelisted("/healthz")
    assert auth_guard.is_whitelisted("/tag/healthz")
    assert auth_guard.is_whitelisted("/operators") is False


def test_middleware_protects_all_routes_and_keeps_health_public(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(auth_guard.DIGEST_ENV, auth_guard._digest("test-token"))

    app = FastAPI(**auth_guard.docs_off_kwargs())

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/operators")
    async def operators():
        return {"code": 0, "msg": "success", "data": []}

    assert auth_guard.install_auth(app) is True
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    missing = client.get("/operators")
    assert missing.status_code == 401
    assert missing.json()["msg"].startswith("AUTH_MISSING")
    wrong = client.get("/operators", headers={"X-Token": "wrong"})
    assert wrong.status_code == 403
    allowed = client.get("/operators", headers={"X-Token": "test-token"})
    assert allowed.status_code == 200
    headers = {"X-Token": "test-token"}
    assert client.get("/docs", headers=headers).status_code == 404
    assert client.get("/openapi.json", headers=headers).status_code == 404


def test_custom_whitelist_path(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(auth_guard.WHITELIST_ENV, "/health /ready")
    assert auth_guard.is_whitelisted("/ready")
    assert auth_guard.is_whitelisted("/healthz")
    assert auth_guard.is_whitelisted("/operators") is False
