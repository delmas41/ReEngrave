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
import os
import tempfile
from pathlib import Path

from tests.conftest import _TEST_USER_ID  # noqa: E402

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


# ---------------------------------------------------------------------------
# The tiny fake staged record (`_one_note_record`) and the `fake_pipeline` /
# `app_client` fixtures live in `conftest.py`.
# ---------------------------------------------------------------------------


def _minimal_pdf(path: str) -> str:
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


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


async def _create_score(session_factory, Score, pdf_path: str) -> str:
    import uuid
    from datetime import datetime
    score_id = str(uuid.uuid4())
    async with session_factory() as session:
        session.add(Score(
            id=score_id, user_id=_TEST_USER_ID,
            title="Test", composer="Test", era="romantic",
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
