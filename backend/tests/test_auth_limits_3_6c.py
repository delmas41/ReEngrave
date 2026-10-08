"""ROADMAP 3.6c (audit 2026-10-07 §3A): logout revokes, every costly route is
rate-limited, and the limiter keys on the real client behind a proxy.

Through the real routes with real JWTs. The environment (tmp DB, tmp upload
dir, ALLOW_DEFAULT_SECRET) is set by conftest.py before `main` is imported.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import main as main_module
from core.config import settings
from core.limiter import client_key, limiter
from core.security import create_access_token
from database.connection import AsyncSessionLocal
from database.models import User


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limiter():
    limiter.reset()
    yield
    limiter.reset()


def _make_user() -> User:
    async def go():
        uid = str(uuid.uuid4())
        async with AsyncSessionLocal() as s:
            u = User(id=uid, email=f"{uid}@example.com",
                     password_hash="unused-in-these-tests", role="user")
            s.add(u)
            await s.commit()
            return u
    return asyncio.run(go())


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.email)}"}


# --------------------------------------------------------------------------
# 1. logout revokes both tokens
# --------------------------------------------------------------------------


@pytest.fixture
def cheap_hash(monkeypatch):
    # passlib's bcrypt backend is broken against the bcrypt wheel installed
    # in some environments; hashing is not what these tests are about.
    import routers.auth as auth_module
    monkeypatch.setattr(auth_module, "hash_password", lambda p: "h:" + p)
    # The test client speaks plain http; a Secure cookie would never be sent
    # back to logout (the dev compose sets COOKIE_SECURE=false for the same).
    monkeypatch.setattr(settings, "cookie_secure", False)


def test_logout_revokes_access_token_and_refresh_cookie(cheap_hash):
    # A private client: its own cookie jar, so the refresh cookie is the one
    # register set (path-scoped exactly as a browser would).
    with TestClient(main_module.app) as c:
        email = f"{uuid.uuid4()}@example.com"
        r = c.post("/api/auth/register",
                   json={"email": email, "password": "correct-horse-1"})
        assert r.status_code == 201, r.text
        access = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {access}"}
        assert c.get("/api/auth/me", headers=auth).status_code == 200

        # The old refresh cookie, to replay after logout.
        old_refresh = c.cookies.get("refresh_token")
        assert old_refresh, "register must set the refresh cookie"

        out = c.post("/api/auth/logout", headers=auth)
        assert out.status_code == 200, out.text

        # The same access token is dead ...
        assert c.get("/api/auth/me", headers=auth).status_code == 401
        # ... and so is the refresh token that was in the cookie.
        replay = c.post("/api/auth/refresh", cookies={"refresh_token": old_refresh})
        assert replay.status_code == 401


def test_refresh_cookie_reaches_the_logout_route(cheap_hash):
    """The cookie's path must cover /api/auth/logout, or a browser never
    sends it there and the refresh token cannot be revoked."""
    with TestClient(main_module.app) as c:
        r = c.post("/api/auth/register", json={
            "email": f"{uuid.uuid4()}@example.com", "password": "correct-horse-1"})
        assert r.status_code == 201, r.text
        sc = [v for k, v in r.headers.multi_items() if k == "set-cookie"
              and v.startswith("refresh_token=")]
        assert sc, "no refresh cookie set"
        live = [v for v in sc if "Max-Age" in v and "Max-Age=0" not in v]
        assert live and "Path=/api/auth;" in live[0] + ";", live


# --------------------------------------------------------------------------
# 2. rate limits: defaults, and a tiny limit actually answers 429
# --------------------------------------------------------------------------


def test_default_limits_are_the_declared_numbers():
    assert settings.rate_limit_refresh == "30/minute"
    assert settings.rate_limit_reset_password == "5/hour"
    for name in ("upload", "musicxml", "gradus", "compare"):
        assert getattr(settings, f"rate_limit_{name}") == "20/hour", name
    assert settings.rate_limit_process_omr == "10/hour"
    assert settings.rate_limit_process_compare == "10/hour"


def _form(files_key="file", n=1):
    """Valid multipart bodies, so validation (422) passes and the request
    reaches the limiter; the handler may then answer 400/404/415."""
    def kw():
        files = [(files_key, (f"x{i}.xml", b"<a/>", "text/xml")) for i in range(n)]
        return {"files": files,
                "data": {"title": "t", "composer": "c", "era": "e", "name": "n"}}
    return kw


# (setting, method, path, kwargs) -- each request answers a non-429 error
# (400/401/404/422) until the limit is spent, then 429. A route that is not
# decorated never reaches 429.
_ROUTES = [
    ("rate_limit_refresh", "/api/auth/refresh", lambda: {}, False),
    ("rate_limit_reset_password", "/api/auth/reset-password",
     lambda: {"json": {"token": "nope", "new_password": "x"}}, False),
    ("rate_limit_upload", "/api/import/upload", _form("file"), True),
    ("rate_limit_musicxml", "/api/import/musicxml", _form("file"), True),
    ("rate_limit_gradus", "/api/gradus/", _form("xml_file"), True),
    ("rate_limit_compare", "/api/compare/", _form("xml_files", 2), True),
    ("rate_limit_process_omr", "/api/scores/nope/process/omr", lambda: {}, True),
    ("rate_limit_process_compare", "/api/scores/nope/process/compare", lambda: {}, True),
]


@pytest.mark.parametrize("setting,path,kw,authed", _ROUTES,
                         ids=[r[0] for r in _ROUTES])
def test_route_answers_429_past_its_limit(client, monkeypatch, setting, path, kw, authed):
    monkeypatch.setattr(settings, setting, "2/minute")
    headers = _auth(_make_user()) if authed else {}
    codes = [client.post(path, headers=headers, **kw()).status_code for _ in range(4)]
    assert 422 not in codes, codes  # the request must reach the limiter
    assert codes[:2] != [429, 429] and 429 not in codes[:2], codes
    assert codes[2:] == [429, 429], codes


def test_a_limit_is_per_route_not_global(client, monkeypatch):
    """Positive control: spending one route's budget leaves another's intact."""
    monkeypatch.setattr(settings, "rate_limit_refresh", "1/minute")
    client.post("/api/auth/refresh")
    assert client.post("/api/auth/refresh").status_code == 429
    assert client.get("/health").status_code == 200


# --------------------------------------------------------------------------
# 3. proxy-aware key
# --------------------------------------------------------------------------


def _req(xff: str | None, peer: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234),
                    "method": "GET", "path": "/", "query_string": b""})


def test_key_ignores_forwarded_for_by_default(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    assert settings.trust_proxy_headers is False
    assert client_key(_req("203.0.113.7, 10.0.0.2")) == "10.0.0.9"


def test_key_uses_first_forwarded_hop_when_trusted(monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert client_key(_req("203.0.113.7, 10.0.0.2")) == "203.0.113.7"
    assert client_key(_req(" 203.0.113.7 ")) == "203.0.113.7"
    # no header, or an empty one: fall back to the socket, never to ""
    assert client_key(_req(None)) == "10.0.0.9"
    assert client_key(_req("")) == "10.0.0.9"
    assert client_key(_req(" , 10.0.0.2")) == "10.0.0.9"


def test_trusted_key_separates_clients_through_the_real_limiter(client, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    monkeypatch.setattr(settings, "rate_limit_refresh", "1/minute")
    h1, h2 = {"X-Forwarded-For": "198.51.100.1"}, {"X-Forwarded-For": "198.51.100.2"}
    assert client.post("/api/auth/refresh", headers=h1).status_code == 401
    assert client.post("/api/auth/refresh", headers=h1).status_code == 429
    assert client.post("/api/auth/refresh", headers=h2).status_code == 401
