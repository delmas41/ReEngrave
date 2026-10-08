"""ROADMAP 3.3c: the web app shows a staged job's accounting (unread /
held-out bars, held-out staves) and serves its marked PDF.

Three behaviours, each able to fail:

  * a staged job's `metadata_json` carries the exporter's own accounting —
    `staged_unread_bars` (bars we read NOTHING in), `staged_held_out_bars`
    (bars roadmap 2.8 held out because their durations do not sum to the
    meter), `staged_bars_total`, `staged_held_out_staves` and a small
    per-page tally of the held-out-by-sum bars — read straight off
    `staged.export.to_musicxml`'s report, never recomputed (CLAUDE.md §4d);
  * a `local`-engine job carries NONE of those `staged_*` keys — the
    positive control that proves the fields are staged-only rather than
    always present with zeroes;
  * the marked PDF a staged job's accounting panel links to
    (`GET /api/scores/{id}/export?format=pdf`) actually resolves, through
    the REAL `export_module` -> `staged.lilypond.to_lilypond` ->
    `lilypond` binary path (ROADMAP 3.1/3.5), not a mock.

Reuses `test_staged_omr_engine.py`'s fixture shape (`fake_pipeline`,
`_minimal_pdf`, `app_client`, `_create_score`, `_fetch_score`) — importing
them, not restating them, keeps this suite from drifting the way a second
hand-copy always does (the same reasoning `test_staged_job_budget.py`
states for its own imports).

RUN RED FIRST: before `staged_omr.py`'s roadmap-3.3c fix, `unread_bars` on
`StagedOmrResult` was `bars_held_out_sum["bars"]` (the DOES-NOT-ADD-UP
count) under the wrong name, and there was no `held_out_bars`, `bars_total`
or `held_out_bars_by_page` field at all — `TestStagedAccountingFields`
below asserts on all four and fails on the unrepaired tree with either an
`AttributeError` (no such field) or a wrong value (`staged_unread_bars`
reading the held-out count instead of the truly-unread one).
"""

from __future__ import annotations

import asyncio
import os

import pytest

# ⚠️ SAME tmp-dir / env-var bootstrap `test_staged_omr_engine.py` does,
# BEFORE `main` is imported anywhere — importing that module here reuses its
# already-set env vars (`os.environ.setdefault`, a no-op if that module's
# import ran first) rather than pointing `main` at a second, different
# throwaway DB. Same convention `test_staged_job_budget.py` follows.
# (`app_client` and `fake_pipeline` come from `conftest.py` by discovery.)
from tests.conftest import (  # noqa: E402
    _log_json,
    _obs,
    _one_note_record,
    _vrd,
)
from tests.test_staged_omr_engine import (  # noqa: E402
    _create_score,
    _fetch_score,
    _minimal_pdf,
)

from tools.omr.staged.record import Q  # noqa: E402


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}
TWO_FOUR = {"numerator": 2, "denominator": 4, "raw": "2/4"}


def _one_unread_and_one_held_out_bar_record() -> dict:
    """One staff, 2/4, two measures (cells):

      * cell 0 carries three quarter notes (C4, D4, E4) -- 3 beats into a
        2/4 bar, so roadmap 2.8 HOLDS IT OUT for not summing to the meter;
      * cell 1 carries no glyphs at all -- a bar we read NOTHING in.

    Same shape as `tools/omr/tests/test_staged_unread_bar_marks.py`'s
    `TestTheAccountingStillBalances` (imported nowhere here, since backend
    tests deliberately keep their own copy of the fixture builder, matching
    `test_staged_omr_engine.py`'s / `test_export_module_staged.py`'s own
    choice not to reach into `tools/omr/tests`).
    """
    obs, vrd = [], []
    n = 0
    for gi, pitch in enumerate(("C4", "D4", "E4")):
        sub = f"glyph/0/0/0/0/{gi}"
        obs.append(_obs(n, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", 100 * gi, 50, 40, 40],
                        category="notehead"))
        n += 1
        obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        n += 1
        vrd.append(_vrd(n, sub, Q.PITCH, pitch))
        n += 1
        vrd.append(_vrd(n, sub, Q.DURATION, QUARTER))
        n += 1
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 2))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    vrd.append(_vrd(904, "system/0/0", Q.METER, TWO_FOUR))
    return _log_json(obs, vrd)


def _fake_no_routing(pdf_path, pages, *, weights=None, route_weights=False,
                     **kw):
    return None, None, None


@pytest.fixture
def accounting_pipeline(monkeypatch):
    """Same shape as `test_staged_omr_engine.py`'s `fake_pipeline`, but the
    gather returns a record with ONE unread bar and ONE held-out-by-sum bar
    instead of the all-clean one-note fixture, so the two accounting
    figures this lane adds are exercised at a non-zero value."""
    monkeypatch.setattr(
        "tools.omr.staged.weight_routing.resolve_staged_weights",
        _fake_no_routing)
    monkeypatch.setattr(
        "tools.omr.staged.pipeline.run_staged",
        lambda pdf_path, pages, **kw: _one_unread_and_one_held_out_bar_record())


@pytest.fixture
def clean_staged_pipeline(monkeypatch):
    """The all-clean one-note fixture `test_staged_omr_engine.py` uses —
    for the PDF-link test, where a compilable `.ly`/PDF matters more than a
    non-zero accounting figure."""
    monkeypatch.setattr(
        "tools.omr.staged.weight_routing.resolve_staged_weights",
        _fake_no_routing)
    monkeypatch.setattr(
        "tools.omr.staged.pipeline.run_staged",
        lambda pdf_path, pages, **kw: _one_note_record())


class TestStagedAccountingFieldsAppearForAStagedJob:
    def test_unread_and_held_out_bars_are_named_separately(
            self, tmp_path, accounting_pipeline, app_client):
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score-acct.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged"},
        )
        assert resp.status_code == 200, resp.text

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "review", score.metadata_json
        meta = score.metadata_json or {}

        # The two reasons, each its own field, each off the exporter's own
        # report key -- never the pre-3.3c collapse where "unread" silently
        # meant "held out by sum".
        assert meta.get("staged_unread_bars") == 1, meta
        assert meta.get("staged_held_out_bars") == 1, meta
        assert meta.get("staged_bars_total") == 2, meta
        assert meta.get("staged_held_out_staves") == 0, meta

        # A small per-page tally of the held-out-by-sum bars, grouping the
        # exporter's own per-bar list -- both bars live on page 0.
        by_page = meta.get("staged_held_out_bars_by_page")
        assert by_page == {"0": 1}, meta

    def test_a_local_job_carries_none_of_the_staged_fields(
            self, tmp_path, app_client, monkeypatch):
        """POSITIVE CONTROL (CLAUDE.md §6b): a control that could not fail
        is not a control. If the staged fields were written unconditionally
        (e.g. defaulted to zero instead of omitted), this test catches it."""
        main_module, client, session_factory, Score = app_client

        async def _fake_run_local_omr(pdf_path, output_dir):
            from modules.local_omr import LocalOmrResult
            xml_path = os.path.join(output_dir, "score.musicxml")
            os.makedirs(output_dir, exist_ok=True)
            with open(xml_path, "w", encoding="utf-8") as fh:
                fh.write("<score-partwise/>")
            return LocalOmrResult(
                musicxml_path=xml_path, omr_json_path="",
                confidence_score=0.9, measures_count=1, pages_processed=1,
            )

        monkeypatch.setattr(
            "modules.local_omr.run_local_omr", _fake_run_local_omr)

        pdf_path = _minimal_pdf(str(tmp_path / "score-local.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "local"},
        )
        assert resp.status_code == 200, resp.text

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "review", score.metadata_json
        meta = score.metadata_json or {}
        assert meta.get("omr_engine") == "local"
        staged_keys = [k for k in meta if k.startswith("staged_")]
        assert staged_keys == [], meta


class TestTheMarkedPdfLinkResolves:
    def test_export_format_pdf_compiles_a_real_pdf_for_a_staged_score(
            self, tmp_path, clean_staged_pipeline, app_client):
        """Through the ACTUAL route, the ACTUAL `export_module` dispatch and
        the ACTUAL `lilypond` binary (CLAUDE.md rule 7 -- a control that
        cannot fail is a computation, not a measurement; this one really
        shells out and really compiles). No mock stands in for LilyPond
        here: `export_module.export_as_pdf` prefers the staged record over
        the legacy JSON / musicxml2ly fallback (see its own docstring), so
        this is also the proof that a staged job's "Open marked PDF" link
        in the frontend has something real to resolve to."""
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score-pdf.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged"},
        )
        assert resp.status_code == 200, resp.text
        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "review", score.metadata_json
        assert score.metadata_json.get("omr_record_path")

        pdf_resp = client.get(
            f"/api/scores/{score_id}/export", params={"format": "pdf"})
        assert pdf_resp.status_code == 200, pdf_resp.text
        assert pdf_resp.content[:4] == b"%PDF"
