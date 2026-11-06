"""2.269 follow-ups, both OFF by default: `OMR_PAGE_BEAM_SPLIT` (a fused stack of beams filed as one view per level, by the page's own single-beam thickness) and
`OMR_PAGE_TIP_REFUTES_BOX` (a clean PAGE stem tip refutes a detector beam box that touches no stem). Synthetic rows only."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from tools.omr.staged import page_beams as PB


def beam(th, fused=False, role="beam", peak=None):
    return dict(role=role, thickness_spaces=th, peak_spaces=th if peak is None else peak, head_fused=fused)


class Split(unittest.TestCase):
    def test_levels_are_the_nearest_whole_number_of_the_pages_own_beam(self):
        bs = [beam(0.62)] * 5 + [beam(1.29), beam(0.97), beam(0.8), beam(2.0)]
        PB.split_levels(bs)
        self.assertEqual([b["levels"] for b in bs], [1] * 5 + [2, 2, 1, 3])

    def test_a_head_fused_stroke_is_counted_on_its_median_not_its_peak(self):     # control that can fail: a head blob lifts the peak, not the median
        bs = [beam(0.62)] * 4 + [beam(0.64, fused=True, peak=1.4), beam(1.3, fused=True, peak=1.4)]
        PB.split_levels(bs)
        self.assertEqual([b["levels"] for b in bs[-2:]], [1, 2])

    def test_no_page_measure_means_one_level(self):             # cannot tell is never "two"
        bs = [beam(0.6), beam(1.3)]
        PB.split_levels(bs)
        self.assertEqual([b["levels"] for b in bs], [1, 1])


class Ev:
    def __init__(self, stems, tips):
        self._stems, self._tips = stems, tips

    def rows(self, q, scope=None, subject=None):
        from tools.omr.staged.record import Q
        return self._stems if q == Q.STEM else self._tips


class Cell:
    def to_key(self):
        return "cell/0/0/0/0"


def stem(i, x, y, w, h):
    from tools.omr.staged.record import READERS
    return SimpleNamespace(id=i, reader=READERS.CV_LINES, value=[x, y, w, h])


def tip(i, end, clean=True, beams=()):
    return SimpleNamespace(detail=dict(cells=["cell/0/0/0/0"], stem_rows=[i], end=end, tip_clean=clean, beams=list(beams), hooks=[], stubs=[], doubt=[], stem_beamed=bool(beams)))


class TipRefutes(unittest.TestCase):
    def box(self, y=100):
        return SimpleNamespace(value=[0, y, 400, 50])           # above a stem that starts at y=200

    def test_a_clean_tip_refutes_a_box_that_touches_no_stem(self):
        ev = Ev([stem("s", 150, 200, 20, 300)], [tip("s", "top")])
        self.assertTrue(PB.refuted_by_page_tips(ev, Cell(), self.box(), ev._stems))

    def test_a_tip_with_a_beam_does_not(self):                  # control that can fail
        ev = Ev([stem("s", 150, 200, 20, 300)], [tip("s", "top", beams=[7])])
        self.assertFalse(PB.refuted_by_page_tips(ev, Cell(), self.box(), ev._stems))

    def test_a_box_touching_the_stem_is_kept(self):
        ev = Ev([stem("s", 150, 200, 20, 300)], [tip("s", "top")])
        self.assertFalse(PB.refuted_by_page_tips(ev, Cell(), self.box(y=160), ev._stems))

    def test_no_page_tip_row_means_not_refuted(self):
        ev = Ev([stem("s", 150, 200, 20, 300)], [])
        self.assertFalse(PB.refuted_by_page_tips(ev, Cell(), self.box(), ev._stems))

    def test_flags_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PB.SPLIT_ENV, None)
            os.environ.pop(PB.TIP_REFUTES_ENV, None)
            self.assertFalse(PB.split_enabled())
            self.assertFalse(PB.tip_refutes_enabled())


if __name__ == "__main__":
    unittest.main()
