"""Tests for the `staged` OMR engine wiring — ROADMAP 3.3, first half.

Two layers:

  * Unit tests directly against `modules.staged_omr.run_staged_omr` — no
    FastAPI, no DB. These MONKEYPATCH the two heavy calls
    (`tools.omr.staged.weight_routing.resolve_staged_weights` and
    `tools.omr.staged.pipeline.run_staged`) with a tiny synthetic record
    built the same way `tools/omr/tests/test_staged_export.py` builds its
    fixtures, so no weights and no real PDF rendering/gather ever run.
  * An end-to-end test through the actual `/api/scores/{id}/process/omr`
    route (TestClient, with `get_current_user` overridden and a temp
    file-backed sqlite DB) — the only way to prove the route's own
    `omr_engine` validator actually accepts "staged" (a bad regex would 422
    before the handler ever runs; calling the handler function directly
    would not exercise that).

Importing `main` mounts a StaticFiles app on `Settings().upload_dir` and
opens the DB at `DATABASE_URL`, so both are pointed at a throwaway tmp
directory *before* import, following the same pattern
`test_main_omr_confidence.py` uses.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

_tmp_root = tempfile.mkdtemp(prefix="reengrave-staged-test-")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_root, "uploads"))
os.environ.setdefault("EXPORT_DIR", os.path.join(_tmp_root, "exports"))
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///" + os.path.join(_tmp_root, "test.db"),
)
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
os.makedirs(os.environ["EXPORT_DIR"], exist_ok=True)

from modules import staged_omr  # noqa: E402
from tools.omr.staged import export as staged_export  # noqa: E402
from tools.omr.staged import record_io  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


# ---------------------------------------------------------------------------
# A tiny fake staged record — the same shape
# tools/omr/tests/test_staged_export.py's `_one_staff_page` builds.
# ---------------------------------------------------------------------------


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


def _minimal_pdf(path: str) -> str:
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


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


# ---------------------------------------------------------------------------
# Unit tests: modules.staged_omr.run_staged_omr directly
# ---------------------------------------------------------------------------


class TestRunStagedOmrWritesFiles:
    def test_writes_a_musicxml_file_and_a_record(self, tmp_path, fake_pipeline):
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        out_dir = str(tmp_path / "out")

        result = asyncio.run(staged_omr.run_staged_omr(pdf_path, out_dir))

        assert result.error_message is None
        assert result.musicxml_path
        assert os.path.isfile(result.musicxml_path)
        assert result.record_path
        assert os.path.isfile(result.record_path)

        xml_text = Path(result.musicxml_path).read_text()
        assert "<score-partwise" in xml_text
        assert "<step>C</step>" in xml_text

        # A real record, readable the ONE way a staged record is read.
        record = record_io.load_record(result.record_path)
        assert "verdicts" in record["record"]

        # The accounting figures come straight off `to_musicxml`'s own
        # coverage report — this fixture holds one identified staff and one
        # bar with an event, so both are zero rather than absent.
        assert result.held_out_staves == 0
        assert result.unread_bars == 0
        assert isinstance(result.status_census, dict)

    def test_missing_pdf_is_reported_not_raised(self, tmp_path, fake_pipeline):
        result = asyncio.run(staged_omr.run_staged_omr(
            str(tmp_path / "nope.pdf"), str(tmp_path / "out")))
        assert result.musicxml_path == ""
        assert "not found" in (result.error_message or "").lower()


class TestUnbalancedBecomesAResultError:
    def test_unbalanced_is_caught_and_reported_never_swallowed(
            self, tmp_path, fake_pipeline, monkeypatch):
        """`staged.export.to_musicxml` RAISES `Unbalanced` rather than
        returning a flag (CLAUDE.md §4c). `run_staged_omr` must not turn
        that into a quiet, partial "success" — it must come back as an
        `error_message` naming the failure, with no musicxml_path."""
        def _boom(result):
            raise staged_export.Unbalanced("notes refused do not sum: 1 != 2")

        monkeypatch.setattr(
            "tools.omr.staged.export.to_musicxml", _boom)

        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        result = asyncio.run(
            staged_omr.run_staged_omr(pdf_path, str(tmp_path / "out")))

        assert result.musicxml_path == ""
        assert result.error_message is not None
        assert "Unbalanced" in result.error_message
        assert "notes refused do not sum" in result.error_message
        # And no record.json accidentally reported as the "output" either —
        # a failed run must not look like a run that finished.
        assert not os.path.isfile(
            os.path.join(str(tmp_path / "out"), "score.musicxml"))


# ---------------------------------------------------------------------------
# End-to-end: the route itself accepts "staged" and the job path runs
# ---------------------------------------------------------------------------


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

    main_module.app.dependency_overrides[get_current_user] = lambda: object()
    with TestClient(main_module.app) as client:
        yield main_module, client, AsyncSessionLocal, Score
    main_module.app.dependency_overrides.pop(get_current_user, None)


async def _create_score(session_factory, Score, pdf_path: str) -> str:
    import uuid
    from datetime import datetime
    score_id = str(uuid.uuid4())
    async with session_factory() as session:
        session.add(Score(
            id=score_id, title="Test", composer="Test", era="romantic",
            source="upload", original_pdf_path=pdf_path,
            status="pending", created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        await session.commit()
    return score_id


async def _fetch_score(session_factory, Score, score_id: str):
    from sqlalchemy import select
    async with session_factory() as session:
        res = await session.execute(select(Score).where(Score.id == score_id))
        return res.scalar_one()


class TestStagedEngineAcceptedByTheRoute:
    def test_staged_is_accepted_and_the_job_writes_musicxml(
            self, tmp_path, fake_pipeline, app_client):
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged"},
        )
        # Would be 422 (query validation) before "staged" joined the
        # route's regex — this is the behavioural check that matters, not
        # a source-text grep of the pattern string.
        assert resp.status_code == 200, resp.text
        assert resp.json()["omr_engine"] == "staged"

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "review", score.metadata_json
        assert score.musicxml_path
        assert os.path.isfile(score.musicxml_path)
        meta = score.metadata_json or {}
        assert meta["omr_engine"] == "staged"
        assert meta.get("omr_record_path")
        assert os.path.isfile(meta["omr_record_path"])
        assert meta.get("staged_held_out_staves") == 0
        assert meta.get("staged_unread_bars") == 0

    def test_unbalanced_becomes_a_job_error_via_the_route(
            self, tmp_path, fake_pipeline, monkeypatch, app_client):
        def _boom(result):
            raise staged_export.Unbalanced("boom")

        monkeypatch.setattr("tools.omr.staged.export.to_musicxml", _boom)

        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score2.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged"},
        )
        assert resp.status_code == 200, resp.text

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "error"
        meta = score.metadata_json or {}
        assert "Unbalanced" in meta.get("omr_error", "")
        assert "boom" in meta.get("omr_error", "")
        # No file was quietly written and called a success.
        assert not score.musicxml_path
