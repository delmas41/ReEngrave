"""ROADMAP 2.18c -- flag ink at a stem's tip the detector never boxed.

⚠️ WHY THIS FILE EXISTS. `benchmarks/omr-missing-notes-2026-09/FINDINGS.md`
SS11.4b: after 2.18b, 53 stemmed black heads on Breitkopf p1 stand at their
head value with no beam and no flag READ, and a by-eye pass found ~6 of them
PRINT a flag nothing on the record witnesses -- `cannot tell` written as
`quarter` (CLAUDE.md rule 8). Today nothing on the record says *ink hangs
off this stem's tip*. This is that row: `Q.STEM_TIP_INK`
(`gather.stem_tip_ink`, `gather._observe_stem_tip_ink`), a windowed density
test off the staff-ERASED raster (CLAUDE.md SS9), reusing `ledger_rung_ink`'s
own shape (a tested band with a background band for contrast).

⚠️ RUN RED FIRST: every test below fails to import before `gather.stem_tip_
ink` / `gather._observe_stem_tip_ink` / `Q.STEM_TIP_INK` /
`READERS.CV_STEM_TIP` exist.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS

SP = 20.0                        # one staff space, canonical px
STEM_X0, STEM_X1 = 190.0, 194.0   # a 4px-wide stem
TOP_Y, BOTTOM_Y = 100.0, 300.0    # a 10-space stem -- long enough that the
                                  # top and bottom windows do not overlap


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- the pure measurement, on synthetic rasters (0 = ink)
# ─────────────────────────────────────────────────────────────────────────────

class TestTheMeasurement(unittest.TestCase):
    """`gather.stem_tip_ink` -- a windowed ink-density ruler with a
    background band for contrast, no identity, no ownership."""

    def test_flag_ink_to_the_right_of_the_top_tip_is_found(self):
        """An up-stem's tip: ink drawn exactly in the tested band, to the
        RIGHT of the stem, nothing on the mirrored LEFT (background)."""
        img = _paper()
        _draw(img, STEM_X1, 120, 212, 150)     # right band, [120,150]
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertTrue(m["found"])
        self.assertGreaterEqual(m["right"], gather.STEM_TIP_INK_DENSE)
        self.assertLessEqual(m["left"], gather.STEM_TIP_INK_BACKGROUND_MAX)

    def test_POSITIVE_CONTROL_a_clean_tip_is_not_found(self):
        """⚠️ THE CONTROL, RUN FAILING FIRST if the density floor were 0: an
        untouched raster proves `found` can be False, not only True."""
        img = _paper()
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertFalse(m["found"])
        self.assertEqual(m["right"], 0.0)

    def test_ink_on_BOTH_sides_fails_the_background_guard(self):
        """A flag never prints on both sides of one stem -- ink this dense on
        the LEFT too means the window is not measuring a flag (a stain, a
        crossing slur), so `found` must stay False even though the RIGHT
        band alone would pass."""
        img = _paper()
        _draw(img, STEM_X1, 120, 212, 150)         # right
        _draw(img, 172, 120, STEM_X0, 150)         # mirrored left
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertFalse(m["found"])

    def test_the_BOTTOM_tip_walks_UP_into_the_stem_symmetrically(self):
        """A down-stem's tip: `into_sign=-1.0` walks UP from `BOTTOM_Y`, so
        the SAME window shape as the top case lands ABOVE the tip."""
        img = _paper()
        _draw(img, STEM_X1, 250, 212, 280)         # BOTTOM_Y - (50..20)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, BOTTOM_Y, -1.0, SP)
        self.assertTrue(m["found"])

    def test_window_off_the_raster_is_none(self):
        img = _paper(h=50, w=50)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertIsNone(m)

    def test_no_unit_is_none(self):
        img = _paper()
        self.assertIsNone(gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y,
                                              1.0, 0.0))
        self.assertIsNone(gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y,
                                              1.0, None))

    def test_no_raster_is_none(self):
        self.assertIsNone(gather.stem_tip_ink(None, STEM_X0, STEM_X1, TOP_Y,
                                              1.0, SP))


class _Det:
    """A detector row, the fields `_stem_tip_blockers` reads."""

    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class TestStemTipBlockersWidthCut(unittest.TestCase):
    """⚠️⚠️ THE FAULT, MEASURED ON A REAL GATHER: every one of the six
    confirmed missed-flag heads FINDINGS SS11.4b names sat under a `staff`
    detection box spanning the WHOLE SYSTEM's width (or an equally wide
    `tie`), so treating ANY overlapping detection as a blocker abstained
    `occupied` before the window was ever measured -- 1380 of 1584 window
    attempts on the first real gather. `_explaining_detections`'s own width
    cut (CLAUDE.md SS10: "a `staff` box is mostly paper") is the fix, and it
    must apply to the DETECTOR's boxes and NOT to this reader's own (narrow,
    by construction) beam strokes.
    """

    def test_a_page_wide_staff_box_is_NOT_a_blocker(self):
        wide_staff = _Det(0, 500, 2000, 40)     # ~100 spaces wide at SP=20
        out = gather._stem_tip_blockers([], [wide_staff], SP)
        self.assertEqual(out, [])

    def test_a_LOCAL_detection_still_blocks(self):
        local_rest = _Det(200, 500, 40, 60)     # 2 spaces wide
        out = gather._stem_tip_blockers([], [local_rest], SP)
        self.assertEqual(len(out), 1)

    def test_a_beam_stroke_blocks_REGARDLESS_of_the_width_cut(self):
        """⚠️ The cut is for the DETECTOR's classification boxes; a beam
        stroke is this reader's own CV rung and is never filtered by it."""
        wide_beam = _Det(0, 500, 2000, 8)
        out = gather._stem_tip_blockers([wide_beam], [], SP)
        self.assertEqual(len(out), 1)

    def test_no_space_unit_skips_the_detector_list_but_keeps_beams(self):
        out = gather._stem_tip_blockers([_Det(0, 0, 10, 10)],
                                        [_Det(0, 0, 10, 10)], None)
        self.assertEqual(len(out), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- `_observe_stem_tip_ink`: two rows per stem, the guards
# ─────────────────────────────────────────────────────────────────────────────

class FakeCell:
    def __init__(self, *, image_no_staff):
        self.image_no_staff = image_no_staff


def _stem_cell_with_top_ink():
    img = _paper()
    _draw(img, STEM_X1, 120, 212, 150)     # only the TOP window is inked
    return FakeCell(image_no_staff=img)


SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TOP_Y, STEM_X1 - STEM_X0, BOTTOM_Y - TOP_Y)   # x,y,w,h


class TestGatherIntegration(unittest.TestCase):

    def test_files_one_row_per_end_and_only_the_top_is_found(self):
        log = Log()
        gather._observe_stem_tip_ink(log, SUB, "cell:0",
                                     _stem_cell_with_top_ink(), "obs:stem-1",
                                     STEM_BOX, [], SP)
        log.freeze()
        rows = log.rows(Q.STEM_TIP_INK, SUB)
        self.assertEqual(len(rows), 2)
        by_end = {r.detail["end"]: r for r in rows}
        self.assertTrue(by_end["top"].value)
        self.assertFalse(by_end["bottom"].value)
        for r in rows:
            self.assertEqual(r.reader, READERS.CV_STEM_TIP)
            self.assertEqual(r.detail["stem_row_id"], "obs:stem-1")

    def test_a_beam_stroke_blocker_abstains_occupied(self):
        """A beam stroke overlapping the TOP window means that ink is
        already named -- this reader must not re-claim it."""
        log = Log()
        blocker = (STEM_X1, 125.0, 212.0, 135.0)      # corners, inside [120,150]
        gather._observe_stem_tip_ink(log, SUB, "cell:0",
                                     _stem_cell_with_top_ink(), "obs:stem-1",
                                     STEM_BOX, [blocker], SP)
        log.freeze()
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertEqual(abst["top"].reason, ABSTAIN.OCCUPIED)
        # the BOTTOM window is untouched by the blocker and still measures
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertFalse(rows["bottom"].value)

    def test_no_image_no_staff_abstains_no_mask(self):
        log = Log()
        gather._observe_stem_tip_ink(log, SUB, "cell:0",
                                     FakeCell(image_no_staff=None),
                                     "obs:stem-1", STEM_BOX, [], SP)
        log.freeze()
        abst = log.refusals(Q.STEM_TIP_INK, SUB)
        self.assertEqual(len(abst), 2)
        self.assertTrue(all(a.reason == ABSTAIN.NO_MASK for a in abst))

    def test_no_staff_space_unit_abstains_no_staff_geometry(self):
        log = Log()
        gather._observe_stem_tip_ink(log, SUB, "cell:0",
                                     _stem_cell_with_top_ink(), "obs:stem-1",
                                     STEM_BOX, [], None)
        log.freeze()
        abst = log.refusals(Q.STEM_TIP_INK, SUB)
        self.assertEqual(len(abst), 2)
        self.assertTrue(
            all(a.reason == ABSTAIN.NO_STAFF_GEOMETRY for a in abst))


if __name__ == "__main__":
    unittest.main()
