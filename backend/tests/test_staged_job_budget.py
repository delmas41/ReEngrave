"""ROADMAP 3.3, second half: page cap -> job budget.

Three behaviours, each able to fail (CLAUDE.md rule 7 — a control must be
able to fail; every test below has a sibling on the other side of its own
assertion):

  * a `pages` query param on `omr_engine=staged` is parsed with the SAME
    `tools.omr.staged.__main__.parse_pages` the CLI uses, and a malformed
    range is a 400, not a silently-empty or silently-clamped job;
  * a request whose estimated cost (`tools.omr.staged.budget.
    estimate_job_budget_s`) exceeds `settings.omr_job_budget_s` is refused
    up front (413) with the estimate IN the error message, before the score
    is even marked "processing" — never started and truncated, never
    silently capped;
  * NO `pages` param on `omr_engine=staged` runs exactly as before this
    lane (the `OMR_MAX_PAGES` cap, `pages=None` reaching
    `staged_omr.run_staged_omr`) — the one thing this whole change must not
    touch for an existing caller.

Reuses `test_staged_omr_engine.py`'s helper shape (`fake_pipeline`,
`_minimal_pdf`, `app_client`, `_create_score`, `_fetch_score`) rather than
duplicating it — importing them, not restating them, is what keeps this
suite from drifting the way a second hand-copy always does.
"""

from __future__ import annotations

import asyncio

import pytest

# (`app_client` and `fake_pipeline` come from `conftest.py` by discovery.)
# ⚠️ SAME tmp-dir / env-var bootstrap `test_staged_omr_engine.py` does,
# BEFORE `main` is imported anywhere — importing that module here reuses its
# already-set env vars (`os.environ.setdefault`, so this is a no-op if that
# module's import ran first) rather than pointing `main` at a second,
# different throwaway DB.
from tests.test_staged_omr_engine import (  # noqa: E402
    _create_score,
    _fetch_score,
    _minimal_pdf,
)

from modules import staged_omr  # noqa: E402


# ---------------------------------------------------------------------------
# `staged_omr.parse_page_range` — the same parser the CLI uses
# ---------------------------------------------------------------------------


class TestParsePageRange:
    def test_a_dash_range_expands(self):
        assert staged_omr.parse_page_range("0-3") == [0, 1, 2, 3]

    def test_a_bare_page_is_one_element(self):
        assert staged_omr.parse_page_range("5") == [5]

    def test_commas_and_dashes_combine(self):
        assert staged_omr.parse_page_range("0,2,4-6") == [0, 2, 4, 5, 6]

    def test_garbage_raises_rather_than_returning_something(self):
        with pytest.raises(Exception):
            staged_omr.parse_page_range("not-a-page-range")


# ---------------------------------------------------------------------------
# `staged_omr.estimate_budget_s` — the shared constants, not restated here
# ---------------------------------------------------------------------------


class TestEstimateBudgetS:
    def test_more_pages_cost_more(self):
        small = staged_omr.estimate_budget_s(1)
        large = staged_omr.estimate_budget_s(100)
        assert large["total_s_upper_bound"] > small["total_s_upper_bound"]

    def test_zero_pages_is_zero_cost_not_an_error(self):
        est = staged_omr.estimate_budget_s(0)
        assert est["total_s_expected"] == 0
        assert est["total_s_upper_bound"] == 0


# ---------------------------------------------------------------------------
# The route: pages only for staged
# ---------------------------------------------------------------------------


class TestPagesOnlyForStaged:
    def test_pages_with_local_engine_is_refused(self, tmp_path, app_client):
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "local", "pages": "0-2"},
        )
        assert resp.status_code == 400, resp.text
        assert "staged" in resp.text.lower()


# ---------------------------------------------------------------------------
# The route: a malformed range is a 400
# ---------------------------------------------------------------------------


class TestMalformedPagesIsRejected:
    def test_garbage_pages_is_400_not_500_not_silently_empty(
            self, tmp_path, fake_pipeline, app_client):
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged", "pages": "not-a-range"},
        )
        assert resp.status_code == 400, resp.text

        # ⚠️ AND THE SCORE WAS NEVER MARKED "processing" — a rejected
        # request must not leave a job half-started.
        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "pending"


# ---------------------------------------------------------------------------
# The route: over-budget is refused up front, with the estimate in the error
# ---------------------------------------------------------------------------


class TestOverBudgetIsRefusedUpFront:
    def test_a_huge_range_is_413_with_the_estimate_in_the_message(
            self, tmp_path, fake_pipeline, app_client):
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        # 1001 pages, against the default ~14h (OMR_JOB_BUDGET_S) budget --
        # a single page of this document's actual length (1) is irrelevant:
        # the estimate prices what was REQUESTED, before anything is opened.
        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged", "pages": "0-1000"},
        )
        assert resp.status_code == 413, resp.text
        detail = resp.json()["detail"]
        assert "1001 pages" in detail
        assert "s (" in detail or "h" in detail        # a seconds/hours figure
        assert "OMR_JOB_BUDGET_S" in detail

        # ⚠️ NEVER SILENTLY TRUNCATED: the score must still be "pending",
        # not started against a smaller page count than was asked for.
        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        assert score.status == "pending"

    def test_the_same_range_is_accepted_with_a_raised_budget(
            self, tmp_path, fake_pipeline, app_client, monkeypatch):
        """The SAME 1001-page request the test above refuses -- the
        sibling that proves the refusal is a real threshold check and not a
        request this route rejects unconditionally (CLAUDE.md §6b: "a
        refusal test needs a positive control in the same class")."""
        main_module, client, session_factory, Score = app_client
        monkeypatch.setattr(main_module.settings, "omr_job_budget_s", 10**9)
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged", "pages": "0-1000"},
        )
        assert resp.status_code == 200, resp.text

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        meta = score.metadata_json or {}
        assert meta.get("omr_pages_requested") == list(range(1001))
        assert meta.get("omr_budget", {}).get("n_pages") == 1001


# ---------------------------------------------------------------------------
# The route: no `pages` param -> the pre-existing OMR_MAX_PAGES cap
# ---------------------------------------------------------------------------


class TestNoPagesParamKeepsTheOldCap:
    def test_no_pages_param_runs_and_never_computes_a_budget(
            self, tmp_path, fake_pipeline, app_client, monkeypatch):
        """⚠️ THE ONE THING THIS LANE MUST NOT CHANGE for an existing
        caller. `run_staged_omr` is monkeypatched to assert it was called
        with `pages=None` — proof this request took the OLD path, not a
        `pages=[0, 1, ..., OMR_MAX_PAGES-1]` reconstruction of it."""
        main_module, client, session_factory, Score = app_client
        pdf_path = _minimal_pdf(str(tmp_path / "score.pdf"))
        score_id = asyncio.run(_create_score(session_factory, Score, pdf_path))

        seen = {}

        async def _fake_run_staged_omr(pdf_path, output_dir, pages=None):
            seen["pages"] = pages
            return staged_omr.StagedOmrResult(
                musicxml_path=str(tmp_path / "out.musicxml"),
                record_path=str(tmp_path / "out.record.json"),
                pages_processed=1, held_out_staves=0, unread_bars=0,
                status_census={},
            )

        (tmp_path / "out.musicxml").write_text("<score-partwise/>")
        (tmp_path / "out.record.json").write_text("{}")
        monkeypatch.setattr(staged_omr, "run_staged_omr", _fake_run_staged_omr)
        monkeypatch.setattr(main_module.staged_omr, "run_staged_omr",
                            _fake_run_staged_omr)

        resp = client.post(
            f"/api/scores/{score_id}/process/omr",
            params={"omr_engine": "staged"},   # no `pages`
        )
        assert resp.status_code == 200, resp.text

        score = asyncio.run(_fetch_score(session_factory, Score, score_id))
        meta = score.metadata_json or {}
        assert "omr_budget" not in meta
        assert "omr_pages_requested" not in meta
        assert seen.get("pages") is None
