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


def _run_rescue(cell, detector, detections=None):
    log = Log()
    local = {cell.staff_index: (0, 0)}
    detections = detections if detections is not None else {}
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
        """⚠️ Never rescues a bar 2.52 already read: the scratch re-run of
        `gather_empty_bar_rest_search` finds the SAME real whole rest its
        own pipeline call will, and this reader stands down."""
        cell = _FakeCell(_whole_rest_image())
        detector = _FakeDetector([_FakeDet("noteheadHalfOnLine", 0.15)])
        log, detections = _run_rescue(cell, detector)

        self.assertEqual(detector.calls, [])
        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        self.assertNotIn(_sub().to_key(), detections)

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
        cell = _FakeCell(_blank_image())
        log, detections = _run_rescue(cell, detector=None)
        self.assertEqual(log.all_rows(), ())


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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.55 EXTENSION, cause B (DECISIONS 2026-10-01, `lane-farhead-
# combined`): *"there should be plenty of shape to see 2 oval shapes with
# lines emerging from both sides of the note heads"* -- a head missed
# INSIDE a blob. Sean's own 10-01 rule: *"a line through a head always
# shows on both sides"* -- a ledger row with a thin, flat stub on BOTH
# sides of a head-sized gap, with no existing notehead/rest box in the
# gap, is itself a witness that a head sits there.
#
# ⚠️ RUN RED FIRST: `gather._ledger_both_sides_witnesses` and the
# `"ledger_both_sides"` witness kind do not exist before this round.
# ─────────────────────────────────────────────────────────────────────────────

def _ledger_both_sides_image(*, y_c=120.0, left=(10.0, 30.0),
                             right=(46.0, 70.0), space=SPACE, width=BAR_WIDTH,
                             height=BAR_HEIGHT):
    """A blank cell carrying a thin, flat ledger stub on both sides of the
    `[left[1], right[0]]` gap at `y_c` -- nothing boxed in the gap."""
    img = _blank_image(width, height)
    from tools.omr.staged import gather as _g
    thickness = _g.LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * space
    pad = _g.LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * space
    half_h = thickness / 2.0 + pad
    y0, y1 = int(round(y_c - half_h)), int(round(y_c + half_h))
    img[y0:y1, int(left[0]):int(left[1])] = 0
    img[y0:y1, int(right[0]):int(right[1])] = 0
    return img


class TestLedgerBothSidesWitness(unittest.TestCase):
    """`gather._ledger_both_sides_witnesses` -- pure, on a synthetic cell."""

    def test_a_stub_pair_with_an_empty_gap_is_a_witness(self):
        cell = _FakeCell(_ledger_both_sides_image())
        witnesses = gather._ledger_both_sides_witnesses(cell, [], HALF_STEP)
        kinds = [w["kind"] for w in witnesses]
        self.assertIn("ledger_both_sides", kinds)
        w = next(w for w in witnesses if w["kind"] == "ledger_both_sides")
        # The gap sits between x=30 and x=46 -- its own centre, x~38, must
        # fall inside the witness window.
        self.assertLessEqual(w["x_lo"], 38.0)
        self.assertGreaterEqual(w["x_hi"], 38.0)
        self.assertLessEqual(w["y_lo"], 120.0)
        self.assertGreaterEqual(w["y_hi"], 120.0)

    def test_a_gap_already_covered_by_an_existing_head_is_not_a_witness(self):
        """Cause B is a MISSED head only -- a gap the detector already
        boxed is not this witness's territory (cause A's, or no gap at
        all)."""
        cell = _FakeCell(_ledger_both_sides_image())
        existing = [_FakeDet("noteheadBlackOnLine", 0.6,
                             x_canonical=34.0, y_canonical=116.0,
                             width_canonical=8.0, height_canonical=8.0)]
        witnesses = gather._ledger_both_sides_witnesses(cell, existing,
                                                        HALF_STEP)
        kinds = [w["kind"] for w in witnesses]
        self.assertNotIn("ledger_both_sides", kinds)

    def test_a_gap_too_narrow_for_a_head_is_not_a_witness(self):
        """Two stubs almost touching are two ends of ONE broken ledger,
        never a head-sized gap."""
        cell = _FakeCell(_ledger_both_sides_image(left=(10.0, 34.0),
                                                   right=(36.0, 70.0)))
        witnesses = gather._ledger_both_sides_witnesses(cell, [], HALF_STEP)
        kinds = [w["kind"] for w in witnesses]
        self.assertNotIn("ledger_both_sides", kinds)

    def test_a_gap_too_wide_for_a_head_is_not_a_witness(self):
        cell = _FakeCell(_ledger_both_sides_image(left=(5.0, 15.0),
                                                   right=(90.0, 100.0)))
        witnesses = gather._ledger_both_sides_witnesses(cell, [], HALF_STEP)
        kinds = [w["kind"] for w in witnesses]
        self.assertNotIn("ledger_both_sides", kinds)

    def test_a_single_stub_with_nothing_on_the_other_side_is_not_a_witness(self):
        """One-sided ink alone is not this witness -- Sean's rule names
        BOTH sides for a line crossing a head."""
        img = _blank_image(BAR_WIDTH, BAR_HEIGHT)
        img[117:123, 10:30] = 0  # one stub only
        cell = _FakeCell(img)
        witnesses = gather._ledger_both_sides_witnesses(cell, [], HALF_STEP)
        kinds = [w["kind"] for w in witnesses]
        self.assertNotIn("ledger_both_sides", kinds)

    def test_no_grid_returns_no_witnesses(self):
        cell = _FakeCell(_ledger_both_sides_image())
        self.assertEqual(gather._ledger_both_sides_witnesses(cell, [], None),
                        [])


class TestLedgerBothSidesRescue(unittest.TestCase):
    """The witness wired into the full `gather_lowconf_rescue` reader."""

    def test_a_detector_box_found_in_the_gap_is_kept_as_a_rescue(self):
        cell = _FakeCell(_ledger_both_sides_image())
        det = _FakeDet("noteheadBlackOnLine", 0.12,
                      x_canonical=34.0, y_canonical=116.0,
                      width_canonical=8.0, height_canonical=8.0)  # c~(38,120)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector)

        glyph = R_glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.GLYPH_BOX, glyph)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("witness"), "ledger_both_sides")

    def test_no_box_found_in_the_gap_records_witness_unmet_never_invents_one(
            self):
        """⚠️ THE RULE THE BRIEF NAMES: a witness with nothing near it,
        even at `RESCUE_CONF_FLOOR`, is recorded (`witness_unmet`) --
        never a guessed box."""
        cell = _FakeCell(_ledger_both_sides_image())
        detector = _FakeDetector([])  # the rerun finds nothing at all
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        refusals = log.refusals(Q.GLYPH_BOX, _sub())
        reasons = [r.reason for r in refusals]
        self.assertIn("witness_unmet", reasons)
        self.assertEqual(detections.get(_sub().to_key(), []), [])


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.55 EXTENSION, 2026-10-01 (coordinator addendum, lane-farhead-
# box-ab): Sean, on 4 tall rescued boxes on the 2.55 rescue sheet (tiles
# 11/13/14/20): *"a few of the boxes look very tall and enclose 2 notes a
# 3rd away from each other"* -- then, on the same boxes: *"all of those
# are notes connected to ties"*. Each tie end predicts ONE head at its
# own staff position; a tall box with two tie ends a third apart is a
# split into two heads, one tie end is one head, none is dropped and
# recorded -- never invented either way.
#
# ⚠️ RUN RED FIRST: `gather.TALL_BOX_HEIGHT_RATIO_MIN`,
# `gather._tall_box_tie_end_centres` and `ABSTAIN.RESCUE_BOX_SPANS_TWO_
# HEADS` do not exist before this round.
# ─────────────────────────────────────────────────────────────────────────────

class TestTallBoxTieEndCentres(unittest.TestCase):
    """`gather._tall_box_tie_end_centres` -- pure."""

    def _tie(self, y_bottom):
        return _FakeDet("tie", 0.9, category="structural",
                       x_canonical=30.0, y_canonical=y_bottom - 10.0,
                       width_canonical=40.0, height_canonical=10.0)

    def _tall_box(self):
        return _FakeDet("noteheadBlackOnLine", 0.12,
                       x_canonical=78.0, y_canonical=50.0,
                       width_canonical=14.0, height_canonical=40.0)

    def test_two_tie_ends_a_third_apart_give_two_centres(self):
        cell = _FakeCell(_blank_image())
        tie1, tie2 = self._tie(60.0), self._tie(80.0)   # a space apart
        witnesses = gather._lowconf_rescue_witnesses(cell, [tie1, tie2],
                                                      HALF_STEP)
        centres = gather._tall_box_tie_end_centres(
            cell.image_no_staff, self._tall_box(), witnesses, SPACE)
        self.assertEqual(len(centres), 2)
        ys = sorted(c[1] for c in centres)
        self.assertAlmostEqual(ys[1] - ys[0], SPACE, delta=1.0)

    def test_one_tie_end_gives_one_centre_never_invents_a_second(self):
        cell = _FakeCell(_blank_image())
        witnesses = gather._lowconf_rescue_witnesses(cell, [self._tie(60.0)],
                                                      HALF_STEP)
        centres = gather._tall_box_tie_end_centres(
            cell.image_no_staff, self._tall_box(), witnesses, SPACE)
        self.assertEqual(len(centres), 1)

    def test_no_tie_end_witness_gives_no_centres(self):
        cell = _FakeCell(_blank_image())
        centres = gather._tall_box_tie_end_centres(
            cell.image_no_staff, self._tall_box(), [], SPACE)
        self.assertEqual(centres, [])

    def test_two_witnesses_that_converge_on_one_oval_are_deduped(self):
        """⚠️ REGRESSION (print-check finding, coordinator addendum crop
        sheet, tiles `cell/2/0/4/7`/`cell/2/1/3/14`): two tie ends start
        far enough apart to survive the RAW de-dup, but
        `_notehead_vertical_ink_extent` can lock onto the SAME ink peak
        from both -- a merged blob has one real oval, found twice. Must
        collapse to ONE centre, not report a duplicate second head."""
        img = _blank_image()
        # One real head's worth of ink, reachable from BOTH witnesses'
        # own search bands (+-1 staff space around each predicted y) --
        # nothing else in the raster for the extent search to find, so
        # both searches land on the SAME peak despite starting further
        # apart than the RAW de-dup's own 0.4-space threshold.
        img[63:73, 70:100] = 0
        cell = _FakeCell(img)
        tie1, tie2 = self._tie(60.0), self._tie(80.0)   # 1 sp apart RAW --
        # both searches still reach the SAME ink (+-1 space each)
        witnesses = gather._lowconf_rescue_witnesses(cell, [tie1, tie2],
                                                      HALF_STEP)
        centres = gather._tall_box_tie_end_centres(
            cell.image_no_staff, self._tall_box(), witnesses, SPACE)
        self.assertEqual(len(centres), 1)


class TestTallBoxRescueIntegration(unittest.TestCase):
    """The split wired into the full `gather_lowconf_rescue` reader."""

    def _tie(self, y_bottom):
        return _FakeDet("tie", 0.9, category="structural",
                       x_canonical=30.0, y_canonical=y_bottom - 10.0,
                       width_canonical=40.0, height_canonical=10.0)

    def _tall_box(self):
        return _FakeDet("noteheadBlackOnLine", 0.12,
                       x_canonical=78.0, y_canonical=50.0,
                       width_canonical=14.0, height_canonical=40.0)

    def test_a_tall_box_over_two_tie_ends_is_split_into_two_heads(self):
        cell = _FakeCell(_blank_image())
        tie1, tie2 = self._tie(60.0), self._tie(80.0)
        detections = {_sub().to_key(): [tie1, tie2]}
        detector = _FakeDetector([self._tall_box()])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector, detections)

        # gi=0,1 are the two ties already in `existing`; the split heads
        # land at gi=2,3.
        rows2 = log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 2))
        rows3 = log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 3))
        self.assertEqual(len(rows2), 1)
        self.assertEqual(len(rows3), 1)
        self.assertEqual(rows2[0].detail.get("witness"), "tall_box_split")
        self.assertIn("original_box", rows2[0].detail)
        # Each split box is a STANDARD head, never the tall original.
        self.assertLess(rows2[0].value[4], 35.0)
        self.assertLess(rows3[0].value[4], 35.0)
        self.assertEqual(len(detections[_sub().to_key()]), 4)

    def test_a_tall_box_with_one_tie_end_keeps_only_one_head(self):
        cell = _FakeCell(_blank_image())
        detections = {_sub().to_key(): [self._tie(60.0)]}
        detector = _FakeDetector([self._tall_box()])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": []}):
            log, detections = _run_rescue(cell, detector, detections)

        glyph1 = R_glyph(0, 0, 0, 0, 1)   # gi=1: index 0 is the tie itself
        rows = log.rows(Q.GLYPH_BOX, glyph1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("witness"), "tall_box_split")
        self.assertEqual(len(detections[_sub().to_key()]), 2)

    def test_a_tall_box_with_no_tie_witness_is_dropped_and_recorded(self):
        """⚠️ NEVER kept as one head spanning both, and never invented
        without a witness -- a stem witness alone matches the box's own
        centre (so the rescue is still guided), but carries no TIE end to
        split it by."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(84.0, 30.0, 2.0, 40.0)   # bottom end at y=70
        detector = _FakeDetector([self._tall_box()])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0)), ())
        refusals = log.refusals(Q.GLYPH_BOX, _sub())
        reasons = [r.reason for r in refusals]
        self.assertIn("rescue_box_spans_two_heads", reasons)
        self.assertEqual(detections.get(_sub().to_key(), []), [])

    def test_the_same_ink_boxed_twice_by_the_rerun_is_not_rescued_twice(
            self):
        """⚠️ REGRESSION (print-check finding, coordinator addendum crop
        sheet, tiles `cell/2/0/4/7`/`cell/2/1/3/14`): the real Litolff
        small re-gather showed the SAME ink boxed twice by the conf-0.10
        rerun at two different confidences (0.1986 vs 0.1631) -- each
        copy independently matched the SAME stem witness and was kept,
        giving one real note two rescued boxes. Only the higher-
        confidence copy survives."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)   # bottom end at y=80
        det_a = _FakeDet("noteheadHalfOnLine", 0.1986,
                        x_canonical=46.0, y_canonical=76.0,
                        width_canonical=10.0, height_canonical=8.0)
        det_b = _FakeDet("noteheadHalfOnLine", 0.1631,
                        x_canonical=47.0, y_canonical=77.0,
                        width_canonical=10.0, height_canonical=8.0)
        detector = _FakeDetector([det_a, det_b])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)

        rows = log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].score, 0.1986)
        self.assertEqual(log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 1)), ())
        self.assertEqual(len(detections[_sub().to_key()]), 1)

    def test_a_normal_height_box_is_unaffected(self):
        """Below `TALL_BOX_HEIGHT_RATIO_MIN`: unchanged single-head path,
        same shape `test_a_stem_end_witness_accepts_a_matching_rescued_
        head` already exercises."""
        cell = _FakeCell(_blank_image())
        stem = _FakeStem(50.0, 40.0, 2.0, 40.0)
        det = _FakeDet("noteheadHalfOnLine", 0.15,
                      x_canonical=46.0, y_canonical=76.0,
                      width_canonical=10.0, height_canonical=8.0)
        detector = _FakeDetector([det])
        with mock.patch("tools.omr.line_detection.detect_lines",
                        return_value={"stems": [stem]}):
            log, detections = _run_rescue(cell, detector)
        rows = log.rows(Q.GLYPH_BOX, R_glyph(0, 0, 0, 0, 0))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("witness"), "stem_end")


if __name__ == "__main__":
    unittest.main()
