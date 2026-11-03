"""ROADMAP 2.260a M0 (`OMR_STROKE_CUT_FACT`): a stroke carries the cell-crop edges its ink reaches. Controls that can fail: the same beam moved off
the edge is NOT cut; a beam cut on the page's own border is not a cut; the reader says "cannot tell" only when the fact is filed AND the flag is on."""
import os
import unittest

import numpy as np

from tools.omr.staged import stroke_map as SM
from tools.omr.staged.adjudicators import rhythm as RH

SP = 100
LINES = [300 + SP * i for i in range(5)]


def _cell(beam_y0):
    img = np.full((1000, 1400), 255, np.uint8)
    raw = img.copy()
    for y in LINES:
        raw[y - 3:y + 4, :] = 0
    img[beam_y0:beam_y0 + 50, 600:1000] = 0                  # beam 4 sp x 0.5 sp
    img[beam_y0:beam_y0 + 400, 600:620] = 0                  # its stem hangs down
    return img, raw


def _beam(res):
    c = [s for s in res.strokes if s.kind == "horizontal"]
    assert len(c) == 1, [(s.kind, s.box) for s in res.strokes]
    return c[0]


class CutFact(unittest.TestCase):
    def test_beam_on_the_top_edge_is_cut_and_off_it_is_not(self):
        img, raw = _cell(0)
        self.assertIn("t", _beam(SM.map_strokes(img, SP, LINES, raw)).cut)
        img, raw = _cell(200)                                  # CONTROL: the same beam well inside the crop
        self.assertEqual(_beam(SM.map_strokes(img, SP, LINES, raw)).cut, "")

    def test_bottom_and_sides(self):
        self.assertEqual(SM.box_cut_edges(0, 10, 50, 990, 1000, 1400), "l")
        self.assertEqual(SM.box_cut_edges(10, 0, 1400, 1000, 1000, 1400), "tbr")
        self.assertEqual(SM.box_cut_edges(10, 10, 50, 50, 1000, 1400), "")

    def test_page_border_is_not_a_cut(self):
        self.assertEqual(SM.drop_page_border("tb", (100, 0, 900, 400), (3000, 2000)), "b")     # cell starts at the page top
        self.assertEqual(SM.drop_page_border("tb", (100, 50, 900, 3000), (3000, 2000)), "t")   # cell ends at the page bottom
        self.assertEqual(SM.drop_page_border("tb", (100, 50, 900, 400), (3000, 2000)), "tb")   # interior cell: both kept
        self.assertEqual(SM.drop_page_border("tb", (100, 50, 900, 3000), None), "tb")          # page shape unknown: a cut is said, not assumed away

    def test_flag_default_off(self):
        os.environ.pop(SM.STROKE_CUT_FACT_ENV, None)
        self.assertFalse(SM.stroke_cut_fact_enabled())

    def test_reader_says_cannot_tell_only_with_flag_and_fact(self):
        old = os.environ.get(RH.STROKE_CUT_FACT_ENV)
        try:
            os.environ[RH.STROKE_CUT_FACT_ENV] = "1"
            self.assertTrue(RH.stroke_cut_by_cell({"cut": "t"}))
            self.assertTrue(RH.stroke_cut_by_cell({"cut": "b"}))
            self.assertFalse(RH.stroke_cut_by_cell({"cut": "lr"}))      # a side cut says nothing about a beam's thickness
            self.assertFalse(RH.stroke_cut_by_cell({}))                 # no fact: as before
            os.environ[RH.STROKE_CUT_FACT_ENV] = "0"
            self.assertFalse(RH.stroke_cut_by_cell({"cut": "t"}))       # OFF arm of a replay ignores the fact
        finally:
            if old is None:
                os.environ.pop(RH.STROKE_CUT_FACT_ENV, None)
            else:
                os.environ[RH.STROKE_CUT_FACT_ENV] = old


if __name__ == "__main__":
    unittest.main()
