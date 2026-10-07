"""ROADMAP 2.55: a low-confidence rerun of the SAME detector, on ONE cell,
restricted to notehead/rest classes, for a bar `_empty_bar_candidate_cells`
calls boxless and 2.52's own ink search (`Q.EMPTY_BAR_REST_SEARCH`) did not
find a whole rest in.

ROADMAP 2.53 diagnosed the population by hand on Litolff p3: 28 of 29
not-found cells already carry SOME detector box (ties, ledgers, beams,
slurs), never a whole-cell miss -- only the notehead/rest CLASS is missing
under crossing ink, and a `--conf 0.10` rerun recovers one in 24 of 29.
Sean, DECISIONS 2026-10-01: *"Yes"* to exactly this, filed as GLYPH boxes
from their own reader name, crop-checked before anything ships.

⚠️ SAME-DAY REFINEMENT (DECISIONS 2026-10-01, "rescue guided by stems,
ties and accidentals"): *"Every measure should have notes or rests. If the
bar shows ties then there are notes; if there are stems then there are
notes ... If there are ties the notes will be close to the end of the
ties. If there are accidentals then there are notes."* A rescued box is
kept ONLY within a witness's own window (`gather._lowconf_rescue_
witnesses`, `gather._matching_witness`); an unguided box is rejected and
recorded (`ABSTAIN.RESCUE_UNGUIDED`), and a witness with nothing near it
even at `RESCUE_CONF_FLOOR` is recorded too (`ABSTAIN.WITNESS_UNMET`) --
never read as an empty bar.

GATHER+ADJUDICATE ONLY. `gather.gather_lowconf_rescue` is the GATHER half
(reruns the detector, files rows ALWAYS, mutates `detections` in place);
`adjudicate.subjects_for`'s own `_is_rescue_only_glyph` gate is the
ADJUDICATE half -- it is the ONLY place `gather.RESCUE_SHIPS` is read, so
every existing check (duplicate/stacked/tremolo/timesig, ownership, staff
position) is reached unchanged once Sean switches it on.

⚠️ RUN RED FIRST, against the tree before `gather_lowconf_rescue` and
`adjudicate._is_rescue_only_glyph` existed: every test below fails on
`AttributeError`.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import gather
from tools.omr.staged.record import (
    Log, Q, READERS, cell as R_cell, glyph as R_glyph,
)

#: Mirrors `test_staged_empty_bar_rest_search.py`'s own synthetic staff.
LINES = [20.0, 40.0, 60.0, 80.0, 100.0]
TARGET_LINE = LINES[1]       # 4th line from the bottom -- where a whole
                              # rest hangs.
BAR_WIDTH = 120
BAR_HEIGHT = 160


class _FakeDet:
    """The handful of attributes a real `SymbolDetection` carries that
    `gather_lowconf_rescue` (and `gather_detections` before it) reads."""

    def __init__(self, smufl_name, confidence, *, category="noteheads",
                x_canonical=60.0, y_canonical=70.0,
                width_canonical=14.0, height_canonical=10.0):
        self.smufl_name = smufl_name
        self.confidence = confidence
        self.category = category
        self.x_canonical = x_canonical
        self.y_canonical = y_canonical
        self.width_canonical = width_canonical
        self.height_canonical = height_canonical


class _FakeCell:
    """The handful of attributes `gather_lowconf_rescue` and the
    `gather_empty_bar_rest_search` it reruns read off a real `MeasureCell`.
    `bbox_page_px`/`upscale_factor` left unset -- this reader must tolerate
    'no page box' exactly as `gather_detections` does."""

    def __init__(self, image_no_staff, *, line_ys=LINES, page_index=0,
                staff_index=0, measure_index=0):
        self.image_no_staff = image_no_staff
        self.staff_line_ys_canonical = list(line_ys)
        self.page_index = page_index
        self.staff_index = staff_index
        self.measure_index = measure_index
        self.bbox_page_px = None
        self.upscale_factor = None


class _FakeDetector:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def detect(self, cell, conf_threshold=0.25, imgsz=None):
        self.calls.append((conf_threshold, imgsz))
        return list(self.results)


def _blank_image(width=BAR_WIDTH, height=BAR_HEIGHT):
    return np.full((height, width), 255, dtype=np.uint8)


def _whole_rest_image(width=BAR_WIDTH, height=BAR_HEIGHT):
    """A real whole-rest-shaped, whole-rest-positioned block, centred in
    the bar -- the SAME shape `test_staged_empty_bar_rest_search.py` uses,
    so 2.52's own ink search finds it (`found=True`)."""
    img = _blank_image(width, height)
    x0 = width / 2.0 - 10.0
    img[int(TARGET_LINE):int(TARGET_LINE + 10.0), int(x0):int(x0 + 20.0)] = 0
    return img


def _sub():
    return R_cell(0, 0, 0, 0)


def _run_rescue(cell, detector, detections=None, *, search_first=True):
    """The rescue as `gather()` runs it: 2.52's search FIRST, on the same
    log, then the rescue reading its row (ROADMAP 2.58). `search_first=
    False` is the misorder the rescue must refuse, kept only for the test
    that proves it does."""
    log = Log()
    local = {cell.staff_index: (0, 0)}
    detections = detections if detections is not None else {}
    if search_first:
        gather.gather_empty_bar_rest_search(log, [cell], local, detections)
    gather.gather_lowconf_rescue(log, [cell], local, detections,
                                 detector=detector, imgsz=None)
    return log, detections


#: Shared staff-space unit for the witness-window arithmetic below --
#: `half_step = 10.0` (LINES' own spacing / 2), one staff SPACE = 20px.
HALF_STEP = 10.0
SPACE = HALF_STEP * 2.0


class _FakeStem:
    def __init__(self, x_canonical, y_canonical, width_canonical,
                height_canonical):
        self.x_canonical = x_canonical
        self.y_canonical = y_canonical
        self.width_canonical = width_canonical
        self.height_canonical = height_canonical


class TestTheGatherRescue(unittest.TestCase):
    def test_a_stem_end_witness_accepts_a_matching_rescued_head(self):
        """Sean: *"if there are stems then there are notes and the note
        heads will be connected to the stems"*. A stem from x=50..52,
        y=40..80 predicts a head at EITHER end; a rescued box near the
        bottom end (inside the window) is kept."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)  # bottom end at y=80
        det = _FakeDet("noteheadHalfOnLine", 0.15,
                      x_canonical=46.0, y_canonical=76.0,
                      width_canonical=10.0, height_canonical=8.0)  # c~(51,80)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(detector.calls, [(gather.RESCUE_CONF_FLOOR, None)])
        glyph = R_glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.GLYPH_BOX, glyph)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reader, READERS.RESCUE_LOWCONF)
        self.assertEqual(rows[0].detail.get("witness"), "stem_end")
        self.assertEqual(log.rows(Q.GLYPH_CONF, glyph)[0].value, 0.15)
        self.assertEqual(log.rows(Q.NOTEHEAD_CLASS, glyph)[0].value,
                         "noteheadHalfOnLine")
        # The rescued box reaches `detections` in place.
        self.assertEqual(len(detections[_sub().to_key()]), 1)
        self.assertIs(detections[_sub().to_key()][0], det)

    def test_a_tie_end_witness_accepts_a_matching_rescued_head(self):
        """Sean: *"if the bar shows ties then there are notes ... the
        notes will be close to the end of the ties"*. A tie box from
        x=30..70, y=50..60 predicts a head just BELOW its bottom edge
        (y=60) at each end; a box near the right end (x~75) is kept."""
        cell = _FakeCell(_blank_image())
        tie = _FakeDet("tie", 0.9, category="structural",
                      x_canonical=30.0, y_canonical=50.0,
                      width_canonical=40.0, height_canonical=10.0)
        detections = {_sub().to_key(): [tie]}
        det = _FakeDet("noteheadBlackOnLine", 0.12,
                      x_canonical=72.0, y_canonical=61.0,
                      width_canonical=8.0, height_canonical=8.0)  # c~(76,65)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector, detections)

        glyph = R_glyph(0, 0, 0, 0, 1)   # gi=1: index 0 is the tie itself
        rows = log.rows(Q.GLYPH_BOX, glyph)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("witness"), "tie_end")
        self.assertIs(detections[_sub().to_key()][1], det)

    def test_an_accidental_witness_accepts_a_matching_rescued_head(self):
        """Sean: *"if there are accidentals then there are notes"* --
        immediately to the accidental's right, same staff position."""
        cell = _FakeCell(_blank_image())
        acc = _FakeDet("accidentalSharp", 0.9, category="accidental",
                      x_canonical=20.0, y_canonical=50.0,
                      width_canonical=8.0, height_canonical=16.0)
        detections = {_sub().to_key(): [acc]}
        det = _FakeDet("noteheadBlackOnLine", 0.11,
                      x_canonical=31.0, y_canonical=54.0,
                      width_canonical=8.0, height_canonical=8.0)  # c~(35,58)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector, detections)

        glyph = R_glyph(0, 0, 0, 0, 1)
        rows = log.rows(Q.GLYPH_BOX, glyph)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("witness"), "accidental_right")

    def test_an_unguided_low_confidence_box_is_rejected_and_recorded(self):
        """A witness exists (a stem) but the rescued box sits nowhere near
        it -- not accepted on score alone, and recorded as unguided."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)
        det = _FakeDet("noteheadHalfOnLine", 0.15,
                      x_canonical=5.0, y_canonical=5.0,
                      width_canonical=8.0, height_canonical=8.0)  # far away
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        self.assertEqual(detections.get(_sub().to_key(), []), [])
        refusals = log.refusals(Q.GLYPH_BOX, _sub())
        reasons = [r.reason for r in refusals]
        self.assertIn("rescue_unguided", reasons)
        # The stem's own end witness matched nothing either -- OUR
        # failure, recorded, never read as an empty bar (rule 8).
        self.assertIn("witness_unmet", reasons)

    def test_no_witness_at_all_abstains_before_asking_the_detector(self):
        """No stem, no tie/slur, no accidental on record for this cell --
        nothing to be guided by, so the detector is never even asked."""
        cell = _FakeCell(_blank_image())
        detector = _FakeDetector([_FakeDet("noteheadHalfOnLine", 0.15)])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(detector.calls, [])
        refusals = log.refusals(Q.GLYPH_BOX, _sub())
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, "no_detections")

    def test_a_bar_with_a_kept_notehead_is_never_rerun(self):
        """⚠️ Never touches a bar that already has a note or rest: the
        candidate set excludes it before the detector is even asked."""
        cell = _FakeCell(_blank_image())
        existing = [_FakeDet("noteheadBlackOnLine", 0.6)]
        detections = {_sub().to_key(): list(existing)}
        detector = _FakeDetector([_FakeDet("noteheadHalfOnLine", 0.15)])
        log, detections = _run_rescue(cell, detector, detections)

        self.assertEqual(detector.calls, [])
        self.assertEqual(log.all_rows(), ())
        self.assertEqual(detections[_sub().to_key()], existing)

    def test_a_bar_where_2_52_already_found_a_whole_rest_is_never_rerun(self):
        """⚠️ Never rescues a bar 2.52 already read: the search's own
        `found=True` row is on the record (it ran first, as in `gather()`)
        and this reader stands down."""
        cell = _FakeCell(_whole_rest_image())
        detector = _FakeDetector([_FakeDet("noteheadHalfOnLine", 0.15)])
        log, detections = _run_rescue(cell, detector)

        self.assertTrue(log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())[-1].value)
        self.assertEqual(detector.calls, [])
        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        self.assertNotIn(_sub().to_key(), detections)

    def test_rescue_before_the_search_raises_rather_than_rescuing_everything(self):
        """ROADMAP 2.58, the control that can fail (CLAUDE.md rule 7). A
        candidate cell with no search row and no search refusal, ink on,
        means this reader ran before `gather_empty_bar_rest_search`. The
        old behaviour was silent: `log.rows()` returned nothing and every
        candidate was rescued."""
        cell = _FakeCell(_blank_image())
        detector = _FakeDetector([_FakeDet("noteheadHalfOnLine", 0.15)])
        with mock.patch.dict(os.environ, {gather.INK_ENV: "1"}):
            with self.assertRaises(gather.GatherOrderError):
                _run_rescue(cell, detector, search_first=False)
        self.assertEqual(detector.calls, [])

    def test_with_ink_off_the_search_files_nothing_and_the_rescue_proceeds(self):
        """The guard's own OFF branch: `OMR_INK=0` means the search files
        nothing BY DESIGN, so an empty record is not a misorder and the
        rescue runs on every candidate, as it did against an empty scratch
        log before 2.58."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)
        det = _FakeDet("noteheadHalfOnLine", 0.15,
                      x_canonical=46.0, y_canonical=76.0,
                      width_canonical=10.0, height_canonical=8.0)
        detector = _FakeDetector([det])
        with mock.patch.dict(os.environ, {gather.INK_ENV: "0"}), \
                mock.patch("tools.omr.line_detection.detect_lines",
                           return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub()), ())
        self.assertEqual(log.refusals(Q.EMPTY_BAR_REST_SEARCH, _sub()), ())
        self.assertEqual(detector.calls, [(gather.RESCUE_CONF_FLOOR, None)])
        self.assertEqual(len(detections[_sub().to_key()]), 1)

    def test_a_rescued_bar_keeps_its_found_false_search_row(self):
        """ROADMAP 2.58's one record change: the search ran on this bar and
        said `found=False`, then the rescue found a head. Both stay on the
        record -- before 2.58 the search ran AFTER the rescue and skipped
        the bar as no longer boxless, so the record never said the search
        had looked."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)
        det = _FakeDet("noteheadHalfOnLine", 0.15,
                      x_canonical=46.0, y_canonical=76.0,
                      width_canonical=10.0, height_canonical=8.0)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        search = log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())
        self.assertEqual(len(search), 1)
        self.assertFalse(search[0].value)
        self.assertEqual(search[0].reader, READERS.CV_REST_SEARCH)
        rescued = log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0))
        self.assertEqual(len(rescued), 1)
        self.assertEqual(rescued[0].reader, READERS.RESCUE_LOWCONF)

    def test_a_non_notehead_non_rest_class_at_low_confidence_is_not_kept(self):
        """Restricted to notehead/rest classes only -- a `beam` the lower
        floor turns up is not what this reader is for, even with a
        witness (a stem) present to ask the detector at all."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)
        detector = _FakeDetector([_FakeDet("beam", 0.15, category="beams")])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        self.assertEqual(detections.get(_sub().to_key(), []), [])

    def test_no_detector_is_a_supported_no_op(self):
        """The RESCUE files nothing without a detector. The search that ran
        before it (2.58) files its own row, which is not this reader's."""
        cell = _FakeCell(_blank_image())
        log, detections = _run_rescue(cell, detector=None)
        self.assertEqual(
            [r for r in log.all_rows()
             if r.reader == READERS.RESCUE_LOWCONF], [])
        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        self.assertNotIn(_sub().to_key(), detections)


class TestShipsGatesAdjudicate(unittest.TestCase):
    """`adjudicate.subjects_for` is the ONLY place `RESCUE_SHIPS` is read.
    GATHER always files the rows (above); this is the ADJUDICATE half of
    'recorded, not used'."""

    def _log_with_one_rescued_and_one_real_glyph(self):
        log = Log()
        real = R_glyph(0, 0, 0, 0, 0)
        rescued = R_glyph(0, 0, 0, 0, 1)
        # `ledgerLine` -- the class `Q.LEDGER_IS_NOT_A_LEDGER` is narrowed
        # to below; the test is about the GATE, not glyph semantics.
        log.observe(real, Q.GLYPH_BOX,
                   ("ledgerLine", 10.0, 10.0, 5.0, 5.0),
                   reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(rescued, Q.GLYPH_BOX,
                   ("ledgerLine", 60.0, 70.0, 14.0, 10.0),
                   reader=READERS.RESCUE_LOWCONF, frame="cell:0", score=0.15)
        return log, real, rescued

    def test_ships_false_records_but_excludes_the_rescued_glyph(self):
        log, real, rescued = self._log_with_one_rescued_and_one_real_glyph()
        spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
        with mock.patch.object(gather, "RESCUE_SHIPS", False):
            subs = adjudicate.subjects_for(log, spec)
        self.assertIn(real, subs)
        self.assertNotIn(rescued, subs)
        # The GATHER row itself is untouched either way -- "recorded" means
        # the row exists on the log regardless of what ADJUDICATE does.
        self.assertEqual(len(log.rows(Q.GLYPH_BOX, rescued)), 1)

    def test_ships_true_admits_the_rescued_glyph_like_any_other(self):
        log, real, rescued = self._log_with_one_rescued_and_one_real_glyph()
        spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
        with mock.patch.object(gather, "RESCUE_SHIPS", True):
            subs = adjudicate.subjects_for(log, spec)
        self.assertIn(real, subs)
        self.assertIn(rescued, subs)


if __name__ == "__main__":
    unittest.main()
