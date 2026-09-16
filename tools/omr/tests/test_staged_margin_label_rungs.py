"""Margin labels on the staged path: WHICH rung read it, and whether one ran.

⚠️⚠️ THE CENTRAL TESTS HERE ARE THE FOUR STATES OF AN EMPTY STAFF, and they
are what must go RED if the gatherer's reasons are collapsed back into one. A
machine with no `.venv-surya` and no Tesseract reads zero margin labels on
every page EXACTLY as a page that prints no instrument name does -- and until
2026-09-16 `gather_margin_labels` wrote `NO_INK` for both, plus for the far
commoner third case: the staged CLI's own default, where the OCR rungs are
opt-in and were simply never asked. CLAUDE.md's governing rule is that a
fallback must never convert *cannot tell* into a definite answer; "this page
prints no instrument name" is a definite answer.

⚠️ THE CASCADE IS NOT RE-IMPLEMENTED HERE AND MUST NOT BE. Which rung wins a
disagreement is `contextual._read_labels_for_page`'s business and is measured
on real pages (`benchmarks/omr-margin-labels-2026-08/`). What is pinned here
is (a) what GATHER writes down about the four answers the cascade can give,
and (b) that the cascade now SAYS which rung produced each label -- the one
fact `tiers`, a per-page count, structurally cannot carry.

⚠️ THE RECORD FIX CHANGES NO VERDICT, and the last class asserts it. Nothing
in the staged pipeline branches on an abstention's REASON, so an empty staff
still reaches `adjudicate_instrument` as an empty staff. A "fix" that moved a
decision would not be a record fix.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS


# ─────────────────────────────────────────────────────────────────────────────
# A page just real enough for the gatherer
# ─────────────────────────────────────────────────────────────────────────────


def _cell(staff_index=0, measure_index=0, page=0):
    return SimpleNamespace(page_index=page, system_index=0,
                           staff_index=staff_index,
                           measure_index=measure_index,
                           bbox_page_px=(100, 200, 200, 400),
                           upscale_factor=2.0)


def _pws(n_staves=2):
    staves = [SimpleNamespace(system_index=0, staff_index=i)
              for i in range(n_staves)]
    return SimpleNamespace(page=SimpleNamespace(page_index=0), staves=staves)


def _label(staff_index, text, alias=None, confidence=None):
    """A label the way a reader returns one -- RESOLVED THROUGH THE REAL
    LEXICON, not with `instrument=None`.

    ⚠️ It has to be. `_merge_key` ranks two whole-page reads on how many
    labels the lexicon can USE, so a fixture of unmatched labels makes every
    read score `(0, 0)`, every comparison a tie, and the cascade's own
    replace/add logic unreachable -- a test built on those would pass while
    exercising nothing. Found by this file's Surya-replaces case failing.
    """
    from tools.omr.instruments import lookup
    from tools.omr.staff_labels import StaffLabel
    m = lookup(text)
    return StaffLabel(staff_index=staff_index, text=text,
                      instrument=m.instrument if m else None,
                      fifths_offset=m.fifths_offset if m else 0,
                      y_center_px=100.0 + staff_index,
                      confidence=(confidence if confidence is not None
                                  else (m.confidence if m else "none")),
                      alias=(alias if alias is not None
                             else (m.alias if m else "")))


_CELLS = [_cell(0, 0), _cell(0, 1), _cell(1, 0), _cell(1, 1)]
_LOCAL = {0: (0, 0), 1: (0, 1)}


class _Rungs:
    """Stand in for the two installs, so a test can take either away.

    ⚠️ It patches `available` on the MODULES, not on the gatherer, because
    `_label_rung_state` asks the module -- that is the call the record fix is
    about, and stubbing the gatherer's own view of it would test the stub.
    """

    def __init__(self, *, surya=True, tesseract=True, labels=None,
                 raises=None, credit=None, reports=None):
        self.surya, self.tesseract = surya, tesseract
        self.labels = list(labels or ())
        self.raises = raises
        self.credit = dict(credit or {})
        #: A rung that was installed, was asked, THREW, and was swallowed --
        #: so the cascade RETURNS normally and the only trace is `failures`.
        #: A different path from `raises`, which kills the whole cascade.
        self.reports = list(reports or ())
        self.seen = {}

    def __enter__(self):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        self._old = (staff_labels_surya.available,
                     staff_labels_tesseract.available,
                     contextual._labels_for_page)
        staff_labels_surya.available = lambda: self.surya
        staff_labels_tesseract.available = lambda: self.tesseract

        def _fake(pws, pdf_path, page_index, *, assist, budget,
                  surya_fallback=True, ocr_fallback=True, tiers=None,
                  sources=None, failures=None, review_dir=None):
            self.seen = {"surya": surya_fallback, "ocr": ocr_fallback}
            if self.raises is not None:
                raise self.raises
            if tiers is not None:
                tiers[0] += len(self.labels)
            if sources is not None:
                sources.update(self.credit)
            if failures is not None:
                failures.extend(self.reports)
            return list(self.labels)

        contextual._labels_for_page = _fake
        return self

    def __exit__(self, *exc):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        (staff_labels_surya.available, staff_labels_tesseract.available,
         contextual._labels_for_page) = self._old
        return False


def _run(*, surya_flag, ocr_flag, **kw):
    log = Log()
    with _Rungs(**kw):
        G.gather_margin_labels(log, _pws(), _CELLS, _LOCAL,
                               pdf_path="/nonexistent/score.pdf",
                               surya_fallback=surya_flag,
                               ocr_fallback=ocr_flag)
    return log


def _staff_refusals(log):
    return [r for r in log.to_json()["abstentions"]
            if r["quantity"] == Q.MARGIN_LABEL
            and r["subject"].startswith("staff/")]


def _page_refusals(log):
    return [r for r in log.to_json()["abstentions"]
            if r["quantity"] == Q.MARGIN_LABEL
            and r["subject"].startswith("page/")]


def _observations(log):
    return [o for o in log.to_json()["observations"]
            if o["quantity"] == Q.MARGIN_LABEL]


# ─────────────────────────────────────────────────────────────────────────────
# 1. A requested rung that is not installed
# ─────────────────────────────────────────────────────────────────────────────


class TestARequestedRungThatCannotRun(unittest.TestCase):

    def test_an_absent_surya_makes_every_empty_staff_cannot_tell(self):
        log = _run(surya_flag=True, ocr_flag=True, surya=False)
        reasons = {r["reason"] for r in _staff_refusals(log)}
        self.assertEqual(reasons, {ABSTAIN.READER_UNAVAILABLE})

    def test_the_absent_rung_is_named_on_a_page_row(self):
        log = _run(surya_flag=True, ocr_flag=True, surya=False)
        rows = [r for r in _page_refusals(log)
                if r["reason"] == ABSTAIN.READER_UNAVAILABLE]
        self.assertEqual([r["reader"] for r in rows], [READERS.SURYA])
        self.assertEqual(rows[0]["detail"]["rungs_unavailable"], ["surya"])

    def test_an_absent_tesseract_is_named_too(self):
        log = _run(surya_flag=True, ocr_flag=True, tesseract=False)
        rows = [r for r in _page_refusals(log)
                if r["reason"] == ABSTAIN.READER_UNAVAILABLE]
        self.assertEqual([r["reader"] for r in rows], [READERS.TESSERACT])

    def test_POSITIVE_CONTROL_both_installed_and_asked_reads_no_ink(self):
        """The whole point: with every requested rung up, an empty staff is
        a DECISION about the page, and must not be softened to an abstention
        -- or the new reason would mean nothing."""
        log = _run(surya_flag=True, ocr_flag=True)
        reasons = {r["reason"] for r in _staff_refusals(log)}
        self.assertEqual(reasons, {ABSTAIN.NO_INK})
        self.assertEqual(_page_refusals(log), [])


# ─────────────────────────────────────────────────────────────────────────────
# 2. No OCR rung asked for -- the staged default, and the commonest case
# ─────────────────────────────────────────────────────────────────────────────


class TestNoRungRequested(unittest.TestCase):

    def test_the_staged_default_says_out_of_scope_not_no_ink(self):
        log = _run(surya_flag=False, ocr_flag=False)
        reasons = {r["reason"] for r in _staff_refusals(log)}
        self.assertEqual(reasons, {ABSTAIN.OUT_OF_SCOPE})

    def test_a_rung_that_is_off_is_not_reported_as_missing(self):
        """`off` and `absent` are different facts. A page row naming an
        uninstalled rung nobody asked for would make every default run look
        blind."""
        log = _run(surya_flag=False, ocr_flag=False, surya=False,
                   tesseract=False)
        self.assertEqual(_page_refusals(log), [])

    def test_the_flags_reach_the_cascade(self):
        with _Rungs() as rungs:
            G.gather_margin_labels(Log(), _pws(), _CELLS, _LOCAL,
                                   pdf_path="/nonexistent/score.pdf",
                                   surya_fallback=True, ocr_fallback=False)
        self.assertEqual(rungs.seen, {"surya": True, "ocr": False})


# ─────────────────────────────────────────────────────────────────────────────
# 3. The rung that read it is the rung that is named
# ─────────────────────────────────────────────────────────────────────────────


class TestTheRungThatReadItIsNamed(unittest.TestCase):

    def test_a_surya_read_is_not_filed_under_the_text_layer(self):
        log = _run(surya_flag=True, ocr_flag=True,
                   labels=[_label(0, "Flauti"), _label(1, "Oboi")],
                   credit={0: "surya", 1: "surya"})
        self.assertEqual({o["reader"] for o in _observations(log)},
                         {READERS.SURYA})

    def test_two_rungs_on_one_page_are_attributed_apart(self):
        """The case `tiers` cannot express: a per-page COUNT of `[1, 0, 1]`
        says one staff each and never which."""
        log = _run(surya_flag=True, ocr_flag=True,
                   labels=[_label(0, "Flauti"), _label(1, "Kl. Tr.")],
                   credit={0: "text_layer", 1: "tesseract"})
        by_text = {o["value"]: o["reader"] for o in _observations(log)}
        self.assertEqual(by_text, {"Flauti": READERS.TEXT_LAYER,
                                   "Kl. Tr.": READERS.TESSERACT})

    def test_an_uncredited_label_falls_back_to_the_text_layer(self):
        """A caller that passes no `sources` must not crash or invent a rung."""
        log = _run(surya_flag=False, ocr_flag=False,
                   labels=[_label(0, "Flauti")])
        self.assertEqual([o["reader"] for o in _observations(log)],
                         [READERS.TEXT_LAYER])


# ─────────────────────────────────────────────────────────────────────────────
# 4. A rung that was installed, was asked, and threw
# ─────────────────────────────────────────────────────────────────────────────


class TestASuryaFailureIsRecorded(unittest.TestCase):
    """Driving the REAL cascade, because the routing under test is its own."""

    def _read(self, *, raises):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        old = (staff_labels_surya.available,
               staff_labels_surya.read_staff_labels_surya,
               staff_labels_tesseract.available,
               contextual.read_staff_labels)
        failures, tiers, sources = [], [0] * 5, {}
        try:
            staff_labels_surya.available = lambda: True
            staff_labels_tesseract.available = lambda: False

            def _boom(pws):
                raise raises
            staff_labels_surya.read_staff_labels_surya = _boom
            contextual.read_staff_labels = lambda pws: []
            from tools.omr.assist import Assist
            from pathlib import Path
            labels = contextual._read_labels_for_page(
                _pws(), Path("/nonexistent/score.pdf"), 0,
                assist=Assist("none"), budget=[0],
                surya_fallback=True, ocr_fallback=True,
                tiers=tiers, sources=sources, failures=failures)
        finally:
            (staff_labels_surya.available,
             staff_labels_surya.read_staff_labels_surya,
             staff_labels_tesseract.available,
             contextual.read_staff_labels) = old
        return labels, failures

    def test_the_cascade_records_the_rung_that_threw(self):
        labels, failures = self._read(raises=RuntimeError("llama-server gone"))
        self.assertEqual(labels, [])
        self.assertEqual([f["rung"] for f in failures], ["surya"])
        self.assertEqual(failures[0]["error"], "RuntimeError")

    def test_POSITIVE_CONTROL_a_rung_that_works_records_no_failure(self):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        old = (staff_labels_surya.available,
               staff_labels_surya.read_staff_labels_surya,
               staff_labels_tesseract.available,
               contextual.read_staff_labels)
        failures = []
        try:
            staff_labels_surya.available = lambda: True
            staff_labels_tesseract.available = lambda: False
            staff_labels_surya.read_staff_labels_surya = \
                lambda pws: [_label(0, "Flauti")]
            contextual.read_staff_labels = lambda pws: []
            from tools.omr.assist import Assist
            from pathlib import Path
            labels = contextual._read_labels_for_page(
                _pws(), Path("/nonexistent/score.pdf"), 0,
                assist=Assist("none"), budget=[0], surya_fallback=True,
                ocr_fallback=True, tiers=[0] * 5, sources={},
                failures=failures)
        finally:
            (staff_labels_surya.available,
             staff_labels_surya.read_staff_labels_surya,
             staff_labels_tesseract.available,
             contextual.read_staff_labels) = old
        self.assertEqual(failures, [])
        self.assertEqual([lab.text for lab in labels], ["Flauti"])

    def test_the_gatherer_turns_a_cascade_crash_into_cannot_tell(self):
        log = _run(surya_flag=True, ocr_flag=True,
                   raises=RuntimeError("cascade exploded"))
        reasons = {r["reason"] for r in _staff_refusals(log)}
        self.assertEqual(reasons, {ABSTAIN.READER_UNAVAILABLE})

    def test_A_SWALLOWED_FAILURE_ALSO_POISONS_THE_PAGE(self):
        """⚠️ THE MUTATION BATTERY FOUND THIS GAP, not review. Dropping
        `or failures` from the empty-staff predicate left the whole suite
        green: every existing test drove the cascade CRASHING, which takes
        the outer `except`, and none drove it RETURNING while reporting a
        rung that threw and was swallowed. Those are two different paths and
        only one of them was reached -- a test named for a hazard it does not
        touch."""
        log = _run(surya_flag=True, ocr_flag=True,
                   labels=[_label(0, "Flauti")],
                   credit={0: "text_layer"},
                   reports=[{"rung": "surya", "error": "RuntimeError",
                             "note": "llama-server gone", "page_index": 0}])
        self.assertEqual({r["reason"] for r in _staff_refusals(log)},
                         {ABSTAIN.READER_UNAVAILABLE})

    def test_the_swallowed_failure_names_its_rung_on_a_page_row(self):
        log = _run(surya_flag=True, ocr_flag=True,
                   reports=[{"rung": "surya", "error": "RuntimeError",
                             "note": "llama-server gone", "page_index": 0}])
        rows = [r for r in _page_refusals(log)
                if r["detail"].get("rung_failed") == "surya"]
        self.assertEqual([r["reader"] for r in rows], [READERS.SURYA])
        self.assertEqual(rows[0]["detail"]["error"], "RuntimeError")

    def test_POSITIVE_CONTROL_no_failure_reported_leaves_no_ink(self):
        log = _run(surya_flag=True, ocr_flag=True, reports=[])
        self.assertEqual({r["reason"] for r in _staff_refusals(log)},
                         {ABSTAIN.NO_INK})

    def test_a_crash_is_never_filed_as_an_unwritten_stub(self):
        """`NOT_IMPLEMENTED` means the code does not exist. Filing a defect
        there puts it in the bucket `gather_coverage` reports as build
        progress."""
        log = _run(surya_flag=True, ocr_flag=True,
                   raises=RuntimeError("cascade exploded"))
        all_reasons = {r["reason"] for r in _staff_refusals(log)} | \
                      {r["reason"] for r in _page_refusals(log)}
        self.assertNotIn(ABSTAIN.NOT_IMPLEMENTED, all_reasons)


# ─────────────────────────────────────────────────────────────────────────────
# 5. The credit is per staff, and it partitions the page census
# ─────────────────────────────────────────────────────────────────────────────


class TestCreditIsPerStaffNotPerCount(unittest.TestCase):

    def _cascade(self, *, text_layer, surya_read, tess_read):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        old = (staff_labels_surya.available,
               staff_labels_surya.read_staff_labels_surya,
               staff_labels_tesseract.available,
               staff_labels_tesseract.read_staff_labels_tesseract,
               contextual.read_staff_labels)
        tiers, sources = [0] * 5, {}
        try:
            staff_labels_surya.available = lambda: surya_read is not None
            staff_labels_tesseract.available = lambda: tess_read is not None
            staff_labels_surya.read_staff_labels_surya = \
                lambda pws: list(surya_read or ())
            staff_labels_tesseract.read_staff_labels_tesseract = \
                lambda pws: list(tess_read or ())
            contextual.read_staff_labels = lambda pws: list(text_layer)
            from tools.omr.assist import Assist
            from pathlib import Path
            labels = contextual._read_labels_for_page(
                _pws(3), Path("/nonexistent/score.pdf"), 0,
                assist=Assist("none"), budget=[0], surya_fallback=True,
                ocr_fallback=True, tiers=tiers, sources=sources, failures=[])
        finally:
            (staff_labels_surya.available,
             staff_labels_surya.read_staff_labels_surya,
             staff_labels_tesseract.available,
             staff_labels_tesseract.read_staff_labels_tesseract,
             contextual.read_staff_labels) = old
        return labels, tiers, sources

    def test_tesseract_additions_are_credited_to_tesseract(self):
        labels, tiers, sources = self._cascade(
            text_layer=[_label(0, "Flauti", alias="flauti")],
            surya_read=None,
            tess_read=[_label(1, "Oboi", alias="oboi")])
        self.assertEqual(sources, {0: "text_layer", 1: "tesseract"})
        self.assertEqual({lab.staff_index for lab in labels}, {0, 1})

    def test_a_surya_win_erases_the_rung_it_overruled(self):
        """Surya REPLACES the page. Crediting without erasing would name two
        producers for one staff."""
        _labels, _tiers, sources = self._cascade(
            text_layer=[_label(0, "Yiolino II.")],
            surya_read=[_label(0, "Violino II.", alias="violino"),
                        _label(1, "Viola", alias="viola")],
            tess_read=None)
        self.assertEqual(sources, {0: "surya", 1: "surya"})

    def test_a_surya_win_drops_the_credit_for_a_label_it_DISCARDED(self):
        """⚠️ THE MUTATION BATTERY FOUND THIS GAP TOO. The erase-on-replace
        arm survived because the case above cannot see it: Surya read BOTH
        staves the text layer had, so plain assignment overwrote the stale
        credit anyway and `replaces=True` was doing nothing observable. The
        discriminating page is one where the text layer names a staff Surya
        does NOT -- that label is thrown away by the replacement, and without
        the erase `sources` still names a producer for it."""
        _labels, _tiers, sources = self._cascade(
            text_layer=[_label(0, "Yiolino II."), _label(2, "Flauti")],
            surya_read=[_label(0, "Violino II."), _label(1, "Viola")],
            tess_read=None)
        self.assertEqual(sources, {0: "surya", 1: "surya"})
        self.assertNotIn(2, sources)

    def test_THE_PARTITION_the_credit_agrees_with_the_page_census(self):
        """A control, not a restatement: `sources` and `tiers` are written at
        the same six sites by different code, so a rung credited but not
        counted (or the reverse) is a real defect in one of them."""
        _labels, tiers, sources = self._cascade(
            text_layer=[_label(0, "Flauti", alias="flauti")],
            surya_read=None,
            tess_read=[_label(1, "Oboi", alias="oboi")])
        counted = {"text_layer": tiers[0], "surya": tiers[1],
                   "tesseract": tiers[2]}
        credited = {name: sum(1 for v in sources.values() if v == name)
                    for name in counted}
        self.assertEqual(credited, counted)

    def test_sources_is_optional_and_the_cascade_is_unchanged_without_it(self):
        from tools.omr import contextual, staff_labels_surya
        from tools.omr import staff_labels_tesseract
        old = (staff_labels_surya.available, staff_labels_tesseract.available,
               contextual.read_staff_labels)
        try:
            staff_labels_surya.available = lambda: False
            staff_labels_tesseract.available = lambda: False
            contextual.read_staff_labels = lambda pws: [_label(0, "Flauti")]
            from tools.omr.assist import Assist
            from pathlib import Path
            labels = contextual._read_labels_for_page(
                _pws(), Path("/nonexistent/score.pdf"), 0,
                assist=Assist("none"), budget=[0],
                surya_fallback=False, ocr_fallback=False)
        finally:
            (staff_labels_surya.available, staff_labels_tesseract.available,
             contextual.read_staff_labels) = old
        self.assertEqual([lab.text for lab in labels], ["Flauti"])


# ─────────────────────────────────────────────────────────────────────────────
# 6. The progress header -- a control, not a courtesy
# ─────────────────────────────────────────────────────────────────────────────


class TestTheProgressHeader(unittest.TestCase):

    def test_it_names_the_label_rungs_and_the_direction_reader_apart(self):
        """⚠️ A header showing only the label flags would licence exactly the
        wrong conclusion. `gather_direction_words` spawns Surya on every page
        under `OMR_DIRECTION_TEXT`, so a run with neither `--surya` nor
        `--ocr` is NOT a run without Surya."""
        from tools.omr.staged.pipeline import _rung_header
        line = _rung_header(False, False)
        self.assertIn("labels", line)
        self.assertIn("directions", line)
        self.assertIn("OMR_DIRECTION_TEXT=", line)

    def test_a_requested_but_uninstalled_rung_is_shouted(self):
        from tools.omr import staff_labels_surya
        from tools.omr.staged.pipeline import _rung_header
        old = staff_labels_surya.available
        try:
            staff_labels_surya.available = lambda: False
            line = _rung_header(True, False)
        finally:
            staff_labels_surya.available = old
        self.assertIn("surya=on BUT NOT INSTALLED", line)

    def test_the_header_is_printed_under_progress(self):
        """Source-level, because the print site is one line and a test that
        drove the whole pipeline to see it would need weights."""
        import inspect
        from tools.omr.staged import pipeline
        src = inspect.getsource(pipeline.run_staged_on)
        self.assertIn("_rung_header(surya_fallback, ocr_fallback)", src)


# ─────────────────────────────────────────────────────────────────────────────
# 7. The control: a RECORD fix moves no decision
# ─────────────────────────────────────────────────────────────────────────────


class TestTheRecordFixChangesNoVerdict(unittest.TestCase):

    def test_identity_still_abstains_no_evidence_under_every_new_reason(self):
        from tools.omr.staged.adjudicators.identity import adjudicate_instrument
        from tools.omr.staged import adjudicate as A
        for kw in ({"surya_flag": False, "ocr_flag": False},
                   {"surya_flag": True, "ocr_flag": True, "surya": False},
                   {"surya_flag": True, "ocr_flag": True}):
            with self.subTest(**kw):
                log = _run(**kw)
                sub = R.staff(0, 0, 0)
                ev = A.Evidence(log, sub, adjudicate_instrument.spec)
                ruling = adjudicate_instrument(ev)
                self.assertIsNone(ruling.value)
                self.assertEqual(ruling.reason, "no_evidence")

    def test_an_observation_still_carries_the_readers_annotation(self):
        log = _run(surya_flag=True, ocr_flag=True,
                   labels=[_label(0, "Flauti", alias="flauti")],
                   credit={0: "surya"})
        obs = _observations(log)[0]
        self.assertEqual(obs["value"], "Flauti")
        self.assertEqual(obs["detail"]["reader_alias"], "flauti")
        self.assertEqual(obs["detail"]["rung"], "surya")


if __name__ == "__main__":
    unittest.main()
