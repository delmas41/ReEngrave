"""Web app hardening (audit 2026-10-07 §3A).

Through the real routes with real JWTs (no auth override):

  * score ownership: user B cannot list, get, delete or export user A's
    score, nor read its diffs -- 404, never 403;
  * `/uploads` serves a file only with a valid signed `?t=` token, and the
    diff response hands out such a URL;
  * the Gradus and compare uploads store `<uuid>_<basename>` under their
    own directory, with an extension allowlist;
  * forgot-password's body carries no reset token by default;
  * startup refuses the shipped default SECRET_KEY unless allowed;
  * the upload size cap answers 413; a hung engraver is killed.

The environment (tmp upload dir, tmp DB, ALLOW_DEFAULT_SECRET) is set by
conftest.py before `main` is imported.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main as main_module
from core.config import settings
from core.security import create_access_token
from database.connection import AsyncSessionLocal
from database.models import FlaggedDifference, GradusScore, Score, User

PDF_BYTES = b"%PDF-1.4\n%test\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
XML_BYTES = (
    b'<?xml version="1.0"?><score-partwise version="3.1"><part-list/>'
    b"</score-partwise>"
)


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as c:
        yield c


def _run(coro):
    return asyncio.run(coro)


async def _make_user() -> User:
    uid = str(uuid.uuid4())
    async with AsyncSessionLocal() as s:
        u = User(id=uid, email=f"{uid}@example.com",
                 password_hash="unused-in-these-tests", role="user")
        s.add(u)
        await s.commit()
        return u


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.email)}"}


def _upload_pdf(client, user) -> str:
    resp = client.post(
        "/api/import/upload",
        files={"file": ("score.pdf", PDF_BYTES, "application/pdf")},
        data={"title": "T", "composer": "C", "era": "romantic"},
        headers=_auth(user),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. Ownership
# ---------------------------------------------------------------------------


class TestScoreOwnership:
    def test_owner_sees_own_score_other_user_gets_404(self, client):
        a, b = _run(_make_user()), _run(_make_user())
        sid = _upload_pdf(client, a)

        # Positive control: the owner can read it.
        assert client.get(f"/api/scores/{sid}", headers=_auth(a)).status_code == 200
        assert sid in [s["id"] for s in client.get("/api/scores", headers=_auth(a)).json()]

        # B: not listed, and every per-score route is 404 (not 403).
        assert sid not in [s["id"] for s in client.get("/api/scores", headers=_auth(b)).json()]
        for method, url in [
            ("get", f"/api/scores/{sid}"),
            ("get", f"/api/scores/{sid}/status"),
            ("get", f"/api/scores/{sid}/diffs"),
            ("get", f"/api/scores/{sid}/export?format=musicxml"),
            ("get", f"/api/scores/{sid}/export/status"),
            ("post", f"/api/scores/{sid}/theory-check"),
            ("delete", f"/api/scores/{sid}"),
        ]:
            resp = getattr(client, method)(url, headers=_auth(b))
            assert resp.status_code == 404, (method, url, resp.status_code, resp.text)

        # B's delete did not delete it.
        assert client.get(f"/api/scores/{sid}", headers=_auth(a)).status_code == 200

    def test_other_user_cannot_decide_a_diff(self, client):
        a, b = _run(_make_user()), _run(_make_user())
        sid = _upload_pdf(client, a)
        did = str(uuid.uuid4())

        async def _add_diff():
            async with AsyncSessionLocal() as s:
                s.add(FlaggedDifference(
                    id=did, score_id=sid, measure_number=1, instrument="vn",
                    difference_type="note", description="d",
                    created_at=datetime.utcnow()))
                await s.commit()
        _run(_add_diff())

        body = {"decision": "accept"}
        assert client.patch(f"/api/diffs/{did}/decision", json=body,
                            headers=_auth(b)).status_code == 404
        assert client.patch(f"/api/diffs/{did}/decision", json=body,
                            headers=_auth(a)).status_code == 200

    def test_learning_report_counts_only_own_scores(self, client):
        a, b = _run(_make_user()), _run(_make_user())
        _upload_pdf(client, a)
        _upload_pdf(client, a)
        ra = client.get("/api/analytics/report", headers=_auth(a)).json()
        rb = client.get("/api/analytics/report", headers=_auth(b)).json()
        assert ra["total_scores"] == 2
        assert rb["total_scores"] == 0

    def test_finetuning_export_is_admin_only(self, client):
        b = _run(_make_user())
        resp = client.get("/api/analytics/finetuning-export", headers=_auth(b))
        assert resp.status_code == 403

    def test_gradus_is_scoped_to_its_owner(self, client):
        a, b = _run(_make_user()), _run(_make_user())
        resp = client.post(
            "/api/gradus/",
            files={"xml_file": ("ref.xml", XML_BYTES, "application/xml")},
            data={"title": "T", "composer": "C"},
            headers=_auth(a),
        )
        assert resp.status_code == 200, resp.text
        gid = resp.json()["id"]
        assert gid in [g["id"] for g in client.get("/api/gradus/", headers=_auth(a)).json()]
        assert gid not in [g["id"] for g in client.get("/api/gradus/", headers=_auth(b)).json()]
        assert client.delete(f"/api/gradus/{gid}", headers=_auth(b)).status_code == 404


# ---------------------------------------------------------------------------
# 2. Signed /uploads
# ---------------------------------------------------------------------------


def _write_upload(rel: str, data: bytes = b"hello") -> str:
    path = Path(settings.upload_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return rel


class TestSignedUploads:
    def test_unsigned_path_is_refused(self, client):
        rel = _write_upload(f"{uuid.uuid4()}/snippets/x_pdf.png")
        assert client.get(f"/uploads/{rel}").status_code == 404

    def test_signed_path_is_served(self, client):
        from core import signed_urls
        rel = _write_upload(f"{uuid.uuid4()}/snippets/x_pdf.png", b"PNGDATA")
        url = signed_urls.signed_url(rel)
        assert url and url.startswith("/uploads/") and "?t=" in url
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.content == b"PNGDATA"

    def test_expired_or_tampered_token_is_refused(self, client):
        from core import signed_urls
        rel = _write_upload(f"{uuid.uuid4()}/a.png")
        expired = signed_urls.make_token(rel, now=0, ttl=1)
        assert client.get(f"/uploads/{rel}", params={"t": expired}).status_code == 404
        good = signed_urls.make_token(rel)
        exp, sig = good.split(".")
        tampered = f"{exp}.{'0' * len(sig)}"
        assert client.get(f"/uploads/{rel}", params={"t": tampered}).status_code == 404
        # A token for one file does not open another.
        other = _write_upload(f"{uuid.uuid4()}/b.png")
        assert client.get(f"/uploads/{other}", params={"t": good}).status_code == 404

    def test_traversal_is_refused_even_with_a_valid_signature(self, client):
        from fastapi import HTTPException
        from core import signed_urls
        secret = Path(settings.upload_dir).resolve().parent / f"secret-{uuid.uuid4()}.txt"
        secret.write_text("top secret")
        rel = f"../{secret.name}"
        token = signed_urls.make_token(rel)  # a signature for the raw string
        with pytest.raises(HTTPException) as exc:
            _run(main_module.serve_upload(rel, token))
        assert exc.value.status_code == 404
        # And through HTTP with an encoded `..`.
        resp = client.get(f"/uploads/%2e%2e/{secret.name}", params={"t": token})
        assert resp.status_code == 404
        assert b"top secret" not in resp.content

    def test_diff_response_carries_a_working_signed_url(self, client):
        a = _run(_make_user())
        sid = _upload_pdf(client, a)
        did = str(uuid.uuid4())
        rel = _write_upload(f"{sid}/snippets/{did}_pdf.png", b"SNIP")

        async def _add_diff():
            async with AsyncSessionLocal() as s:
                s.add(FlaggedDifference(
                    id=did, score_id=sid, measure_number=1, instrument="vn",
                    difference_type="note", description="d",
                    pdf_snippet_path=rel, created_at=datetime.utcnow()))
                await s.commit()
        _run(_add_diff())

        diffs = client.get(f"/api/scores/{sid}/diffs", headers=_auth(a)).json()
        (d,) = [d for d in diffs if d["id"] == did]
        assert d["musicxml_snippet_url"] is None
        resp = client.get(d["pdf_snippet_url"])
        assert resp.status_code == 200 and resp.content == b"SNIP"

        score = client.get(f"/api/scores/{sid}", headers=_auth(a)).json()
        assert client.get(score["pdf_url"]).content == PDF_BYTES


# ---------------------------------------------------------------------------
# 3. Upload filenames and size cap
# ---------------------------------------------------------------------------


class TestUploadNames:
    def test_gradus_stores_uuid_prefixed_basename(self, client):
        a = _run(_make_user())
        resp = client.post(
            "/api/gradus/",
            files={
                "xml_file": ("../../escape.musicxml", XML_BYTES, "application/xml"),
                "pdf_file": ("/etc/evil.pdf", PDF_BYTES, "application/pdf"),
            },
            data={"title": "T", "composer": "C"},
            headers=_auth(a),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        gradus_dir = (Path(settings.upload_dir) / "gradus" / body["id"]).resolve()
        for key, base in (("xml_path", "escape.musicxml"), ("pdf_path", "evil.pdf")):
            stored = Path(body[key]).resolve()
            assert stored.parent == gradus_dir, stored
            prefix, _, name = stored.name.partition("_")
            assert name == base
            uuid.UUID(prefix)
            assert stored.is_file()
        assert not (Path(settings.upload_dir) / "escape.musicxml").exists()

    def test_gradus_refuses_a_disallowed_extension(self, client):
        a = _run(_make_user())
        resp = client.post(
            "/api/gradus/",
            files={"xml_file": ("score.sh", XML_BYTES, "application/xml")},
            data={"title": "T", "composer": "C"},
            headers=_auth(a),
        )
        assert resp.status_code == 400

    def test_compare_stores_uuid_prefixed_basenames(self, client):
        a = _run(_make_user())
        resp = client.post(
            "/api/compare/",
            files=[
                ("xml_files", ("../a.xml", XML_BYTES, "application/xml")),
                ("xml_files", ("/tmp/b.mxl", XML_BYTES, "application/xml")),
            ],
            headers=_auth(a),
        )
        assert resp.status_code == 200, resp.text
        import json
        paths = [Path(p).resolve() for p in json.loads(resp.json()["xml_paths_json"])]
        compare_dir = (Path(settings.upload_dir) / "compare" / resp.json()["id"]).resolve()
        assert [p.name.partition("_")[2] for p in paths] == ["a.xml", "b.mxl"]
        assert all(p.parent == compare_dir for p in paths)

    def test_upload_over_the_cap_is_413(self, client, monkeypatch):
        a = _run(_make_user())
        monkeypatch.setattr(settings, "max_upload_bytes", 16)
        resp = client.post(
            "/api/import/upload",
            files={"file": ("score.pdf", PDF_BYTES, "application/pdf")},
            data={"title": "T", "composer": "C", "era": "romantic"},
            headers=_auth(a),
        )
        assert resp.status_code == 413
        resp = client.post(
            "/api/gradus/",
            files={"xml_file": ("ref.xml", XML_BYTES, "application/xml")},
            data={"title": "T", "composer": "C"},
            headers=_auth(a),
        )
        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# 4. Forgot-password
# ---------------------------------------------------------------------------


class TestForgotPassword:
    def test_body_has_no_token_by_default(self, client):
        u = _run(_make_user())
        resp = client.post("/api/auth/forgot-password", json={"email": u.email})
        assert resp.status_code == 200
        assert resp.json() == {"status": "If that email exists, a reset link has been sent"}

    def test_token_only_when_explicitly_exposed(self, client, monkeypatch):
        u = _run(_make_user())
        monkeypatch.setattr(settings, "expose_reset_token", True)
        resp = client.post("/api/auth/forgot-password", json={"email": u.email})
        assert resp.status_code == 200
        assert resp.json().get("dev_token")


# ---------------------------------------------------------------------------
# 5. Default secret
# ---------------------------------------------------------------------------


class TestDefaultSecret:
    def test_startup_refuses_default_secret(self, monkeypatch):
        from core.config import DEFAULT_SECRET_KEY
        monkeypatch.setattr(settings, "secret_key", DEFAULT_SECRET_KEY)
        monkeypatch.setattr(settings, "allow_default_secret", False)
        with pytest.raises(RuntimeError, match="SECRET_KEY is the shipped default"):
            with TestClient(main_module.app):
                pass

    def test_startup_accepts_default_secret_with_allow_flag(self, monkeypatch):
        from core.config import DEFAULT_SECRET_KEY
        monkeypatch.setattr(settings, "secret_key", DEFAULT_SECRET_KEY)
        monkeypatch.setattr(settings, "allow_default_secret", True)
        with TestClient(main_module.app) as c:
            assert c.get("/health").status_code == 200

    def test_startup_accepts_a_real_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "x" * 48)
        monkeypatch.setattr(settings, "allow_default_secret", False)
        with TestClient(main_module.app) as c:
            assert c.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# 6. Subprocess timeouts
# ---------------------------------------------------------------------------


class TestSubprocessTimeout:
    async def test_hung_process_is_killed(self):
        from modules.lilypond_engrave import SubprocessTimeout, communicate_with_timeout
        proc = await asyncio.create_subprocess_exec(
            "sleep", "30",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        with pytest.raises(SubprocessTimeout, match="timed out"):
            await communicate_with_timeout(proc, 0.2, "sleep")
        assert proc.returncode is not None

    async def test_engrave_score_turns_a_timeout_into_an_error(self, monkeypatch, tmp_path):
        from modules import lilypond_engrave
        real_exec = asyncio.create_subprocess_exec

        async def _fake_exec(*argv, **kw):
            return await real_exec("sleep", "30", **kw)

        monkeypatch.setattr(lilypond_engrave.asyncio, "create_subprocess_exec", _fake_exec)
        monkeypatch.setattr(lilypond_engrave, "LILYPOND_TIMEOUT_S", 0.2)
        ly = tmp_path / "x.ly"
        ly.write_text("{ c }")
        result = await lilypond_engrave.engrave_score(str(ly), str(tmp_path))
        assert result.full_score_pdf_path == ""
        assert "timed out" in (result.error_message or "")
