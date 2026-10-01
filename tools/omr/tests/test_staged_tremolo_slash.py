"""ROADMAP 2.49 -- a stroke crossing a stem is a tremolo slash, not a
notehead. REDESIGNED (Sean, DECISIONS 2026-10-01, on the manager's crop
review of the first build, ~25% of Litolff p3 heads firing, crop
`glyph/3/0/8/6/12` a plain head): *"it should first be recognized as a
thick diagonal line that crosses both sides of the stem significantly.
Some of the current firing looks like a notehead and a ledger line. Those
are at the end of a stem -- a trem slash wouldn't be and they primarily
are on one side of the stem with a tiny bleed. Not to mention that it is
round not a diagonal thick line."*

THREE TESTS, ALL REQUIRED, in this order:

  1. SHAPE    (`notehead_precision._tremolo_shape_ok`) -- the glyph's own
              ink (whole box, beam- AND stem-column-excluded) is a thick
              DIAGONAL stroke: principal-axis angle well off horizontal
              and vertical, clearly elongated, and not filling its own box
              the way a solid oval does.
  2. CROSSING (`_tremolo_crossing_ok`) -- each side of the stem (beyond its
              own edges) holds a REAL SHARE of the glyph's own TOTAL ink
              (not a fraction of that side's own possibly-tiny area) --
              "a tiny bleed" must fail even where the sliver itself reads
              dense.
  3. POSITION (`_tremolo_position_ok`) -- the box sits on the stem's own
              SHAFT, away from BOTH ends (a head always sits AT one end).

Four layers:

  A. `gather._box_ink_mask` / `gather._ink_shape_descriptors` -- pure, on
     constructed rasters. Calibrated against a real filled head (round,
     elongation ~1.3-1.4, fill ~0.6, angle ~0) and a real-proportioned
     tremolo slash (thick, 35 degrees, elongation ~6, fill ~0.25) --
     `calib.py`'s own numbers (manager review, this round): the thresholds
     below sit with real margin on both sides of that measured gap, never
     fitted to one case.
  B. `gather.gather_notehead_stem_cross_ink` -- wired into a Log; confirms
     the STEM COLUMN is excluded from the shape/share read (not only beam
     ink) -- the bug this redesign found and fixed (page-13 re-gather,
     manager review: computing over the WHOLE box read the real slash at
     elongation 1.5 because the stem's own near-vertical stroke runs
     straight through the box and dominates the moment calculation).
  C. `notehead_precision._tremolo_shape_ok` / `_crossing_ok` /
     `_position_ok` -- pure, on constructed detail dicts and boxes.
  D. `notehead_precision._tremolo_slash_crosses_stem` and its effect on
     `_stacked_head_duplicate_refusal`'s own keep-choice -- ADJUDICATE,
     with `Q.NOTEHEAD_STEM_CROSS_INK`/`Q.STEM`/`Q.STACKED_HEAD_FIT` rows
     injected directly.

⚠️ RUN RED FIRST: `gather._box_ink_mask`, `gather._ink_shape_descriptors`,
`notehead_precision._tremolo_shape_ok`/`_tremolo_crossing_ok`/
`_tremolo_position_ok`/`_tremolo_stem_box` and the new `Q.NOTEHEAD_STEM_
CROSS_INK` detail fields (`left_share`, `right_share`, `angle_deg`,
`elongation`, `fill`) do not exist on the tree before this round.

`TREMOLO_SLASH_SHIPS` is `True` since 2026-10-01 (Sean) -- see ROADMAP 2.49's own row for
the re-measured firing count on real data.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import math
import unittest
import unittest.mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Q, READERS, State

from tools.omr.tests.test_staged_notehead_recentre import _paper
from tools.omr.tests.test_staged_notehead_precision import (
    _cell_geometry, _notehead)
from tools.omr.tests.test_staged_stacked_head_fit import (
    _cell, _detection, _fit_row, _stem_row)

SPACING = 40.0


def _fill_ellipse(img, cx, cy, w, h):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = max(1.0, w / 2.0), max(1.0, h / 2.0)
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


def _diag_stroke(img, cx, cy, length, thickness, angle_deg):
    """A thick diagonal stroke, real-slash proportions: ~150 px long,
    ~26 px thick (a tremolo slash is a substantial mark, not a hairline),
    at a real slanted angle -- `calib.py`'s own construction."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    ang = math.radians(angle_deg)
    dx, dy = xx - cx, yy - cy
    u = dx * math.cos(ang) + dy * math.sin(ang)
    v = -dx * math.sin(ang) + dy * math.cos(ang)
    img[(np.abs(u) <= length / 2.0) & (np.abs(v) <= thickness / 2.0)] = 0


# ─────────────────────────────────────────────────────────────────────────────
# A. `gather._box_ink_mask` / `gather._ink_shape_descriptors` -- pure
# ─────────────────────────────────────────────────────────────────────────────


class TestBoxInkMaskPure(unittest.TestCase):

    def test_excludes_given_boxes(self):
        img = _paper(h=50, w=50)
        img[:, :] = 0
        mask = gather._box_ink_mask(img, (0, 0, 50, 50),
                                    exclude_boxes=[(10, 0, 10, 50)])
        self.assertTrue(mask[:, 5].all())
        self.assertFalse(mask[:, 15].any())

    def test_off_raster_is_none(self):
        img = _paper(h=50, w=50)
        self.assertIsNone(gather._box_ink_mask(img, (1000, 1000, 10, 10)))


class TestInkShapeDescriptorsPure(unittest.TestCase):
    """Calibration: a real filled head vs a real-proportioned tremolo
    slash, both read through the SAME stem-column-exclusion the GATHER
    reader applies (see `simulate` here, matching `gather_notehead_stem_
    cross_ink`'s own arithmetic)."""

    BOX = (100.0, 50.0, 140.0, 100.0)       # spans x 100-240
    STEM = (160.0, 0.0, 10.0, 300.0)        # centre x=165, tall shaft

    def _stem_excluded_mask(self, img):
        regions = gather._stem_cross_regions(self.BOX, self.STEM)
        left_box, right_box = regions
        full = gather._box_ink_mask(img, self.BOX)
        bx = self.BOX[0]
        lx1 = int(round(left_box[0] + left_box[2] - bx))
        rx0 = int(round(right_box[0] - bx))
        m = full.copy()
        if rx0 > lx1:
            m[:, lx1:rx0] = False
        return m

    def test_a_round_head_is_low_elongation_high_fill_near_horizontal(self):
        img = _paper(h=400, w=400)
        _fill_ellipse(img, 155, 100, 130, 100)
        d = gather._ink_shape_descriptors(self._stem_excluded_mask(img))
        self.assertLess(d["elongation"], 2.0)
        self.assertGreater(d["fill"], 0.55)

    def test_a_real_proportioned_slash_is_elongated_thin_and_diagonal(self):
        img = _paper(h=400, w=400)
        _diag_stroke(img, 165, 100, 150, 26, 35)
        d = gather._ink_shape_descriptors(self._stem_excluded_mask(img))
        self.assertGreater(d["elongation"], 4.0)
        self.assertLess(d["fill"], 0.35)
        self.assertTrue(20.0 <= d["angle_deg"] <= 70.0)

    def test_too_little_ink_reads_no_shape_at_all(self):
        img = _paper(h=50, w=50)
        mask = gather._box_ink_mask(img, (0, 0, 50, 50))
        self.assertIsNone(gather._ink_shape_descriptors(mask))


# ─────────────────────────────────────────────────────────────────────────────
# B. `gather.gather_notehead_stem_cross_ink` -- wired into a Log
# ─────────────────────────────────────────────────────────────────────────────


class TestGatherNoteheadStemCrossInkShapeFields(unittest.TestCase):

    def _run(self, img, dets, *, stem=(165.0, 40.0, 10.0, 300.0)):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        if stem is not None:
            _stem_row(log, sub, x_c=stem[0], y_c=stem[1], w_c=stem[2],
                     h_c=stem[3])
        gather.gather_notehead_stem_cross_ink(
            log, [cell], {0: (0, 0)}, {sub.to_key(): dets})
        return log

    def test_the_stem_column_is_excluded_from_the_shape_and_share_read(self):
        """THE BUG THIS REDESIGN FOUND AND FIXED: a head's box overlapping a
        TALL stem reads the stem's own near-vertical ink as part of the
        box's "shape" unless that column is excluded too (not only beam
        boxes). A real slash crossing this same tall stem must still read
        as elongated/diagonal, not dragged toward round by the stem's own
        vertical ink."""
        img = _paper(h=400, w=400)
        # the stem itself, drawn into the raster (not just declared as a
        # row) -- a thick vertical stroke the full height of the cell.
        img[0:400, 160:170] = 0
        _diag_stroke(img, 165.0, 190.0, 150, 26, 35)
        d = _detection("noteheadBlackInSpace", 200.0, 190.0, w=140.0, h=100.0)
        log = self._run(img, [d])
        g = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STEM_CROSS_INK, g)
        self.assertEqual(len(rows), 1)
        detail = rows[0].detail
        self.assertGreater(detail["elongation"], 3.0,
                           "the stem's own ink must not flatten the slash's "
                           "own elongation toward round")
        self.assertLess(detail["fill"], 0.4)
        self.assertGreater(detail["left_share"], 0.3)
        self.assertGreater(detail["right_share"], 0.3)

    def test_no_stem_at_all_gets_no_row(self):
        img = _paper(h=400, w=400)
        d = _detection("noteheadBlackInSpace", 200.0, 200.0, w=140.0, h=100.0)
        log = self._run(img, [d], stem=None)
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_STEM_CROSS_INK, g), State.ABSENT)


# ─────────────────────────────────────────────────────────────────────────────
# C. The three pure gates -- `notehead_precision._tremolo_*_ok`
# ─────────────────────────────────────────────────────────────────────────────


class TestTremoloShapeOk(unittest.TestCase):

    def test_a_real_slash_signature_passes(self):
        self.assertTrue(NP._tremolo_shape_ok(
            {"angle_deg": 34.8, "elongation": 6.07, "fill": 0.2481}))

    def test_a_round_head_signature_fails(self):
        self.assertFalse(NP._tremolo_shape_ok(
            {"angle_deg": 0.0, "elongation": 1.33, "fill": 0.62}))

    def test_a_horizontal_ledger_like_signature_fails_on_angle(self):
        self.assertFalse(NP._tremolo_shape_ok(
            {"angle_deg": 0.1, "elongation": 12.0, "fill": 0.1}))

    def test_a_vertical_stem_fragment_signature_fails_on_angle(self):
        self.assertFalse(NP._tremolo_shape_ok(
            {"angle_deg": 89.2, "elongation": 9.8, "fill": 0.07}))

    def test_missing_shape_reads_none_not_false(self):
        self.assertIsNone(NP._tremolo_shape_ok({"angle_deg": None,
                                                "elongation": None,
                                                "fill": None}))


class TestTremoloCrossingOk(unittest.TestCase):

    def test_a_real_slash_near_even_split_passes(self):
        self.assertTrue(NP._tremolo_crossing_ok(
            {"left_share": 0.4948, "right_share": 0.5052}))

    def test_a_tiny_bleed_fails(self):
        self.assertFalse(NP._tremolo_crossing_ok(
            {"left_share": 0.943, "right_share": 0.057}))

    def test_missing_shares_reads_none(self):
        self.assertIsNone(NP._tremolo_crossing_ok(
            {"left_share": None, "right_share": None}))


class TestTremoloPositionOk(unittest.TestCase):

    def test_mid_shaft_passes(self):
        box = (100.0, 150.0, 140.0, 100.0)     # centre y = 200
        stem = (160.0, 0.0, 10.0, 400.0)       # ends at 0 and 400
        self.assertTrue(NP._tremolo_position_ok(box, stem))

    def test_at_the_stems_end_where_a_head_sits_fails(self):
        box = (100.0, -10.0, 140.0, 100.0)     # centre y = 40
        stem = (160.0, 0.0, 10.0, 400.0)       # top end at 0 -- 40 px away
        self.assertFalse(NP._tremolo_position_ok(box, stem))


# ─────────────────────────────────────────────────────────────────────────────
# D. ADJUDICATE -- `_tremolo_slash_crosses_stem` and the stacked keep-choice
# ─────────────────────────────────────────────────────────────────────────────


def _cross_ink_row(log, g, *, stem_id, left_share, right_share,
                   angle_deg=35.0, elongation=6.0, fill=0.25,
                   left=0.5, right=0.5):
    return log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [left, right],
                       reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK,
                       frame="cell:0", stem=stem_id, left=left, right=right,
                       left_share=left_share, right_share=right_share,
                       angle_deg=angle_deg, elongation=elongation, fill=fill)


def _run_notehead(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


class TestTremoloSlashCrossesStemShipped(unittest.TestCase):
    """`TREMOLO_SLASH_SHIPS` patched True for these tests only -- the
    mechanism itself, isolated from the shipped-off question (see
    `TestTremoloSlashHeldBack` below for the real default)."""

    def _ship(self):
        return unittest.mock.patch.object(NP, "TREMOLO_SLASH_SHIPS", True)

    def test_all_three_tests_passing_is_refused(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=200.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        with self._ship():
            log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tremolo_slash_crosses_stem")

    def test_shape_fails_a_round_head_even_with_split_crossing_and_mid_shaft(self):
        """CONTROL: crossing and position both look like a slash's own, but
        the shape is round -- must still fail."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=200.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.49,
                       right_share=0.51, angle_deg=0.0, elongation=1.3,
                       fill=0.62)
        with self._ship():
            log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertFalse(v.detail["tremolo_slash_signal"]["shape_ok"])

    def test_crossing_fails_a_tiny_bleed_even_with_slash_shape_and_mid_shaft(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=200.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.94,
                       right_share=0.06)
        with self._ship():
            log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertFalse(v.detail["tremolo_slash_signal"]["crossing_ok"])

    def test_position_fails_at_the_stems_own_end_even_with_slash_shape_and_crossing(self):
        """CONTROL: Sean -- "[a slash is] at a stem's end -- a trem slash
        wouldn't be." A box sitting at the stem's own end (where a head
        attaches) must fail regardless of shape or crossing."""
        log = Log()
        _cell_geometry(log)
        # box TOP (canonical y, not centre -- `_notehead`'s "_c" suffix
        # means canonical, not centre) at -30, height 100 -> box CENTRE
        # y=20, 20px from the stem's own top end (y0=0) -- ratio 0.2,
        # below POSITION_MIN_END_RATIO_BOX_HEIGHTS (0.5).
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=-30.0,
                     h_c=100.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        with self._ship():
            log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertFalse(v.detail["tremolo_slash_signal"]["position_ok"])

    def test_a_beam_joining_two_stems_at_their_ends_is_not_this_rules_case(self):
        """CONTROL named in the brief: a real beam is never boxed as a
        notehead at all, so it never reaches this rule -- no cross-ink row
        at all."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace")
        with self._ship():
            log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        self.assertNotIn("tremolo_slash_signal", v.detail)

    def test_the_reason_is_named_apart_from_every_other_mechanism(self):
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON, "stacked_head_duplicate")
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON,
                            "notehead_is_a_duplicate_box")
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON, "same_side_second")


class TestTremoloSlashDefault(unittest.TestCase):
    """The REAL default since 2026-10-01 (Sean: "Switch it on"):
    `TREMOLO_SLASH_SHIPS` is `True`, and the default path refuses a box
    that passes all three tests. The OFF path (patched False) still only
    signals."""

    def test_it_ships_by_default(self):
        self.assertTrue(NP.TREMOLO_SLASH_SHIPS)

    def test_the_default_path_refuses_a_signature_passing_all_three(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=200.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tremolo_slash_crosses_stem")

    @unittest.mock.patch.object(NP, "TREMOLO_SLASH_SHIPS", False)
    def test_switched_off_it_SIGNALS_but_does_not_refuse(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", y_c=200.0)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, g, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertTrue(v.detail["tremolo_slash_signal"]["would_fire"])


class TestTremoloSlashNeverWinsAStackedKeepChoiceIfShipped(unittest.TestCase):
    """ROADMAP 2.49's own fixed case, mechanism verified with
    `TREMOLO_SLASH_SHIPS` patched True: a slash sharing a slot with a real
    head must be refused on its OWN three tests before the stacked
    comparison runs, and dropped from the group so it can never be chosen
    as the keeper."""

    def test_with_the_mechanism_SHIPPED_the_slash_loses_and_the_head_survives(self):
        log = Log()
        _cell_geometry(log)
        head = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=4.0,
                        y_c=200.0)
        slash = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=4.0,
                          y_c=250.0)
        _fit_row(log, head, k=1, slot=0, pos_float=4.0, ink=0.30)
        _fit_row(log, slash, k=1, slot=0, pos_float=4.0, ink=0.90)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, slash, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        log.freeze()
        adjudicate._ensure_decisions()
        with unittest.mock.patch.object(NP, "TREMOLO_SLASH_SHIPS", True):
            adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
        v_head = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)
        v_slash = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, slash)
        self.assertIs(v_slash.value, True)
        self.assertEqual(v_slash.reason, "tremolo_slash_crosses_stem")
        self.assertIs(v_head.value, False,
                      "the real head must survive now that its only "
                      "competitor in the stacked group is a tremolo slash")

    @unittest.mock.patch.object(NP, "TREMOLO_SLASH_SHIPS", False)
    def test_switched_off_the_slash_still_wins_the_keep_choice(self):
        log = Log()
        _cell_geometry(log)
        head = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=4.0,
                        y_c=200.0)
        slash = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=4.0,
                          y_c=250.0)
        _fit_row(log, head, k=1, slot=0, pos_float=4.0, ink=0.30)
        _fit_row(log, slash, k=1, slot=0, pos_float=4.0, ink=0.90)
        stem = _stem_row(log, R.cell(0, 0, 0, 0), x_c=200.0, y_c=0.0,
                         w_c=10.0, h_c=400.0)
        _cross_ink_row(log, slash, stem_id=stem.id, left_share=0.49,
                       right_share=0.51)
        log = _run_notehead(log)
        v_head = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)
        self.assertIs(v_head.value, True)
        self.assertEqual(v_head.reason, "stacked_head_duplicate")


if __name__ == "__main__":
    unittest.main()
