"""Tests for export_module's STAGED branch — ROADMAP 3.3.

`export_as_lilypond` / `export_as_pdf` must render a score processed with
`omr_engine == "staged"` via the NATIVE staged exporter
(`tools.omr.staged.lilypond.to_lilypond`) over the pooled record written by
`staged_omr.run_staged_omr`, not via the legacy `tools.omr.export.to_lilypond`
JSON path and not via the `musicxml2ly` fallback.

Uses an in-memory SQLite DB (same pattern as test_analytics_db.py) and a
tiny synthetic staged record (same helpers as
tools/omr/tests/test_staged_export.py / test_staged_omr_engine.py) — no
weights, no PDF, no real gather.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base, Score
from modules.export_module import export_as_lilypond
from tools.omr.staged import record_io
from tools.omr.staged.record import Q


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


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


async def _make_staged_score(db_session, tmp_path) -> Score:
    record_path = str(tmp_path / "score.record.json")
    with open(record_path, "w", encoding="utf-8") as fh:
        fh.write(record_io.dumps_for_file(_one_note_record()))

    score = Score(
        id="staged-score-1", title="T", composer="C", era="romantic",
        source="upload", original_pdf_path=str(tmp_path / "score.pdf"),
        status="review",
        metadata_json={"omr_engine": "staged", "omr_record_path": record_path},
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db_session.add(score)
    await db_session.flush()
    return score


class TestExportAsLilypondPrefersTheStagedRecord:
    @pytest.mark.asyncio
    async def test_staged_engine_renders_via_the_native_staged_exporter(
            self, db_session, tmp_path):
        await _make_staged_score(db_session, tmp_path)
        out_dir = str(tmp_path / "out")

        ly_path = await export_as_lilypond("staged-score-1", out_dir, db_session)

        assert os.path.isfile(ly_path)
        text = open(ly_path, encoding="utf-8").read()
        assert text.startswith("\\version")
        assert "\\score" in text

    @pytest.mark.asyncio
    async def test_a_score_reprocessed_with_local_ignores_a_stale_staged_path(
            self, db_session, tmp_path):
        """A score whose CURRENT `omr_engine` is `local` must never be routed
        through a stale `omr_record_path` left over from an earlier staged
        run — `_staged_record_path_for` gates on the CURRENT engine, not on
        the mere presence of the key."""
        score = await _make_staged_score(db_session, tmp_path)
        score.metadata_json = {
            **score.metadata_json, "omr_engine": "local",
        }
        await db_session.flush()

        from modules.export_module import _staged_record_path_for
        assert _staged_record_path_for(score) == ""
