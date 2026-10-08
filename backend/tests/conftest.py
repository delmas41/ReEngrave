"""Pytest configuration for ReEngrave backend tests."""

import os
import sys
import tempfile

# Add the backend directory to sys.path so modules can be imported directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point every module-level setting at a throwaway directory BEFORE any test
# module imports `core.config` / `database.connection` / `main` (both read
# the environment once, at import). Without this the first module to import
# `main` decides the DB file, and a stale ./reengrave.db from an older
# schema (e.g. before Score.user_id) breaks every route test.
_tmp_root = tempfile.mkdtemp(prefix="reengrave-tests-")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_root, "uploads"))
os.environ.setdefault("EXPORT_DIR", os.path.join(_tmp_root, "exports"))
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///" + os.path.join(_tmp_root, "test.db"))
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
os.makedirs(os.environ["EXPORT_DIR"], exist_ok=True)

# The app refuses to start with the shipped default SECRET_KEY unless this
# is set (core.config.check_startup_secret); tests run with the default.
os.environ.setdefault("ALLOW_DEFAULT_SECRET", "true")


# ---------------------------------------------------------------------------
# Shared fixtures for the staged-engine route tests
# (`test_staged_omr_engine.py`, `test_staged_accounting_3_3c.py`,
# `test_staged_job_budget.py`): moved here from `test_staged_omr_engine.py`
# so every test file gets `fake_pipeline` and `app_client` by discovery, not
# by importing them from a sibling test module.
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402

import pytest  # noqa: E402


def _log_json(observations, verdicts, abstentions=()):
    return {"record": {"observations": list(observations),
                       "verdicts": list(verdicts),
                       "abstentions": list(abstentions),
                       "counts": {}},
            "summary": {}}


def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "cell:0",
            "score": 0.9, "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
         candidates=()):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": list(candidates), "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}


def _one_note_record() -> dict:
    """A minimal one-staff, one-measure, one-note page — a fresh dict every
    call, enough for `to_musicxml` to write a real file."""
    from tools.omr.staged.record import Q

    obs = [
        _obs(0, "glyph/0/0/0/0/0", Q.GLYPH_BOX,
             ["noteheadBlackOnLine", 0, 50, 40, 40], category="notehead"),
        _obs(1, "glyph/0/0/0/0/0", Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"),
    ]
    vrd = [
        _vrd(2, "glyph/0/0/0/0/0", Q.PITCH, "C4"),
        _vrd(3, "glyph/0/0/0/0/0", Q.DURATION, QUARTER),
        _vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1),
        _vrd(901, "staff/0/0/0", Q.CLEF, "treble"),
        _vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1),
        _vrd(903, "document", Q.PART_PARTITION,
             {"join": "ordinal", "staves_per_system": 1}, reason="ordinal"),
    ]
    return _log_json(obs, vrd)


def _fake_no_routing(pdf_path, pages, *, weights=None, route_weights=False,
                     **kw):
    """The same shape `resolve_staged_weights` gives a no-weights,
    no-`--route-weights` CLI call: no detector, no classification."""
    return None, None, None


def _fake_run_staged(pdf_path, pages, *, detector=None, dpi=600,
                     conf_threshold=0.25, imgsz=None, roster=None,
                     dossier=None, input_domain_classification=None,
                     legacy=None, progress=False):
    return _one_note_record()


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Stand in for the heavy gather/detector/routing calls everywhere
    `staged_omr` reaches them, so a test needs no weights and does no real
    PDF rendering."""
    monkeypatch.setattr(
        "tools.omr.staged.weight_routing.resolve_staged_weights",
        _fake_no_routing)
    monkeypatch.setattr(
        "tools.omr.staged.pipeline.run_staged", _fake_run_staged)


@pytest.fixture
def app_client():
    """Import `main` (fresh sys.path / DB / upload dir already pointed at
    tmp by the module-level os.environ.setdefault calls above), override
    auth, and yield an ENTERED TestClient (so the app's lifespan runs —
    `create_all_tables()` — before any request) plus the pieces needed to
    drive the DB directly."""
    import main as main_module
    from dependencies import get_current_user
    from database.connection import AsyncSessionLocal
    from database.models import Score
    from fastapi.testclient import TestClient

    from database.models import User

    # Scores have an owner (Score.user_id); the route only finds a score
    # owned by the current user, so the override returns a real stored user.
    user = User(id=_TEST_USER_ID, email=f"{_TEST_USER_ID}@example.com",
                password_hash="x", role="user")
    main_module.app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(main_module.app) as client:
        asyncio.run(_ensure_user(AsyncSessionLocal, user))
        yield main_module, client, AsyncSessionLocal, Score
    main_module.app.dependency_overrides.pop(get_current_user, None)


_TEST_USER_ID = "staged-engine-test-user"


async def _ensure_user(session_factory, user) -> None:
    from database.models import User
    async with session_factory() as session:
        if await session.get(User, user.id) is None:
            session.add(User(id=user.id, email=user.email,
                             password_hash=user.password_hash, role=user.role))
            await session.commit()
