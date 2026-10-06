"""lane-local-staff-lines (Sean 2026-10-06: "the 5 line staff should be very obvious"): the LOCAL five lines of a known
staff are one comb fitted at the head's x, then one narrow window per line -- never two lines on one ink row.

Tile 6 (Litolff p16 `glyph/16/0/0/0/2`): the staff below was registered ~0.54 space too high, so the second line sat on
the first window's edge and the per-line +-0.5 space search put two lines (538.5, 540.0) on one ink row.

RUN RED FIRST: against the tree before this item there is no `local_staff_lines_in_windows`, `gaps_plausible` or
`READER_KEYWORDS['local_lines_in_window']`.
"""
from __future__ import annotations

import unittest

import numpy as np

from tools.omr.annotate import far_head_owner as FO
from tools.omr.annotate import far_head_reader as FH

SP = 16.0
THICK = 4


def raster(true_tops, h=300, w=400, skip=()):
    g = np.full((h, w), 191, np.uint8)
    for i, y in enumerate(true_tops):
        if i not in skip:
            g[int(y):int(y) + THICK, :] = 0
    return g


TRUE = [100 + SP * i for i in range(5)]                  # 100, 116 ... 164
BOX = (200.0, 40.0, 224.0, 60.0)                          # a head above the staff, flanks at x 152..200, 224..272


class TestWindows(unittest.TestCase):
    def test_tile6_shape_two_lines_not_on_one_row(self):
        # the known staff is registered 0.54 space HIGH of the ink (tile 6): global 91.4 .. 155.4
        gl = [y - 0.54 * SP for y in TRUE]
        g = raster(TRUE)
        old = FH.local_staff_lines(g, gl, BOX[0], BOX[2], 24.0)
        gaps = np.diff(sorted(old)) if old else []
        # the control that can fail: the old per-line search DOES land two lines on one row here
        self.assertTrue(old is None or min(gaps) < 0.6 * SP, old)
        r = FH.local_staff_lines_in_windows(g, gl, BOX[0], BOX[2], 24.0)
        self.assertIsNotNone(r["lines"])
        self.assertEqual(r["fallback"], [])
        self.assertTrue(FH.gaps_plausible(r["lines"], SP), r["lines"])
        for got, want in zip(r["lines"], TRUE):
            self.assertLess(abs(got - want), 2.0)          # the top edge of a 4 px line, the old convention

    def test_positive_control_a_well_registered_staff_is_unchanged(self):
        gl = [y + 1.0 for y in TRUE]
        g = raster(TRUE)
        old = FH.local_staff_lines(g, gl, BOX[0], BOX[2], 24.0)
        new = FH.local_staff_lines_in_windows(g, gl, BOX[0], BOX[2], 24.0)["lines"]
        self.assertEqual([round(v, 1) for v in old], [round(v, 1) for v in new])

    def test_one_line_missing_is_a_labelled_fallback(self):
        gl = list(TRUE)
        g = raster(TRUE, skip=(2,))
        r = FH.local_staff_lines_in_windows(g, gl, BOX[0], BOX[2], 24.0)
        self.assertEqual(r["fallback"], [2])
        self.assertAlmostEqual(r["lines"][2], TRUE[2], delta=2.0)     # the comb's place for it, not silence

    def test_two_lines_missing_abstains(self):
        g = raster(TRUE, skip=(1, 3))
        r = FH.local_staff_lines_in_windows(g, list(TRUE), BOX[0], BOX[2], 24.0)
        self.assertIsNone(r["lines"])
        self.assertEqual(sorted(r["fallback"]), [1, 3])

    def test_frame_lines_off_is_the_old_read(self):
        gl = [y - 0.54 * SP for y in TRUE]
        g = raster(TRUE)
        off = FH.frame_lines_for_head(g, gl, BOX, windowed=False)
        self.assertEqual(off, FH.local_staff_lines(g, gl, BOX[0], BOX[2], 24.0) or gl)
        on = FH.frame_lines_for_head(g, gl, BOX, windowed=True)
        self.assertTrue(FH.gaps_plausible(on, SP))

    def test_owner_witness_unread_not_global_when_staff_cannot_be_fitted(self):
        g = raster(TRUE, skip=(1, 3))
        ctx = type("C", (), dict(gray=g))()
        r = FO.read_toward(ctx, "glyph/0/0/0/0/0", BOX, "noteheadBlack", list(TRUE))
        self.assertFalse(r["fits"])
        self.assertTrue(r["unread"])
        self.assertEqual(r["reason"], "no_staff_lines")


if __name__ == "__main__":
    unittest.main()
