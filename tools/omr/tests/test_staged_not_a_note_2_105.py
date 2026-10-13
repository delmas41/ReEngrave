"""ROADMAP 2.105: two leftovers Sean's tiles proved, STAGED ADJUDICATE.

(b) 2.92 -- a twin-box pair on one printed head that REFUSED EACH OTHER. 2.30
    (`notehead_is_a_duplicate_box`) ordered two same-class boxes by a SATURATING
    shape, so an over-wide box that had merged a neighbour's ink tied a clean
    head and won on detector score; 2.42 (`stacked_head_duplicate`) chose by
    ink and took the clean one. Each refused the other and the head had NO box
    (14 mutual circles, 33 slot groups on Litolff 984073).
(c) a BARLINE boxed `restQuarter` kept as a rest (`out/print/2.100-review-2`
    tile 1, Sean: "Barline"). New reason `rest_is_a_barline` (family_precision).

(a) 2.91, an `sf` boxed as a notehead, is NOT fixed here: no dynamic-letter box
    exists on that ink, and no box-geometry rule separates it from real heads
    (benchmarks/omr-notehead-precision-2026-09 FINDINGS, ROADMAP 2.105).

RUN RED FIRST against the unrepaired tree: the (b) circle test leaves BOTH boxes
refused and the barline is kept as `rest`; every control passes on both trees.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests import test_staged_family_refusals as FR
from tools.omr.tests.test_staged_notehead_precision import (
    SPACING, _cell_geometry, _notehead)


def _fit_row(log, g, *, ink, slot=0):
    return log.observe(g, Q.STACKED_HEAD_FIT, [1, slot, 4.0, 0.2],
                       reader=READERS.CV_STACKED_HEAD_FIT, frame="cell:0",
                       side="right", stem="stem/0/0/0/0", ink=ink, scores={})


def _run_notehead(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


def _refused(log, g):
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g).value is True


class TestTwinBoxesNeverRefuseEachOther(unittest.TestCase):

    def _pair(self, a_w):
        """A (detector conf 0.9, ink 0.70, width `a_w` spaces) and B (conf 0.4,
        ink 1.0, a clean 1.5 x 1.1 head) boxed on one head: same centre."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", conf=0.9,
                      w_c=a_w * SPACING, h_c=1.1 * SPACING, x_c=200.0 - (a_w - 1.5) * SPACING / 2.0)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", conf=0.4,
                      w_c=1.5 * SPACING, h_c=1.1 * SPACING, x_c=200.0)
        _fit_row(log, a, ink=0.70)
        _fit_row(log, b, ink=1.00)
        return _run_notehead(log), a, b

    def test_an_overwide_twin_loses_and_the_clean_head_keeps_the_mark(self):
        log, a, b = self._pair(a_w=2.5)
        self.assertTrue(_refused(log, a), "the over-wide merged box is the one refused")
        self.assertFalse(_refused(log, b), "the clean head box is kept: the head has a box")

    def test_a_genuine_duplicate_still_collapses_to_exactly_one(self):
        """CONTROL, same class and geometry: two PLAUSIBLE twins. Exactly one
        survives -- not both, not neither -- as before this item."""
        log, a, b = self._pair(a_w=1.5)
        live = [g for g in (a, b) if not _refused(log, g)]
        self.assertEqual(len(live), 1)

    def test_two_plausible_heads_on_different_slots_both_stay(self):
        """CONTROL: the rule never merges two different heads."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", conf=0.9, y_c=200.0)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", conf=0.8, y_c=330.0)
        _fit_row(log, a, ink=1.0, slot=0)
        _fit_row(log, b, ink=1.0, slot=1)
        log = _run_notehead(log)
        self.assertFalse(_refused(log, a))
        self.assertFalse(_refused(log, b))


class TestRestBoxThatIsABarline(unittest.TestCase):
    # fixture scale (family_refusals): 100 canonical px = 20 page px = 1 space
    BAR = (400.0, 900.0, 800.0, 1200.0)

    def _verdict(self, cls, page_box):
        log = Log()
        FR._staff_geometry(log)
        log.observe(FR.CELL, Q.CELL_BOX, list(self.BAR), reader=READERS.GEOMETRY, frame="cell:0")
        w_c = (page_box[2] - page_box[0]) * 5.0
        h_c = (page_box[3] - page_box[1]) * 5.0
        g = FR._box(log, 0, cls, quantity=Q.REST, page_box=page_box, w_c=w_c, h_c=h_c)
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=(Q.REST_IS_NOT_A_REST,))
        return log.verdict(Q.REST_IS_NOT_A_REST, g)

    def test_a_thin_tall_box_on_the_cell_edge_is_refused_as_a_barline(self):
        v = self._verdict("restQuarter", [798.0, 1000.0, 802.0, 1080.0])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_is_a_barline")
        sig = v.detail["barline_signal"]
        self.assertLess(sig["margin_width"], 0)        # the margin is recorded, signed

    def test_a_real_quarter_rest_stays_a_rest(self):
        """CONTROL, same class: 1.2 sp wide, 3 sp tall, mid-bar."""
        v = self._verdict("restQuarter", [590.0, 1010.0, 614.0, 1070.0])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_a_thin_tall_box_mid_bar_is_not_this_rules_barline(self):
        """CONTROL: the geometry alone is not enough; it must stand on a cell
        edge (a barline column)."""
        v = self._verdict("restQuarter", [598.0, 1000.0, 602.0, 1080.0])
        self.assertNotEqual(v.reason, "rest_is_a_barline")

    def test_a_rest_box_beside_the_barline_but_rest_wide_stays_a_rest(self):
        """CONTROL: a quarter rest printed near the barline (flush, but a full
        1.2 sp wide) is still a rest."""
        v = self._verdict("restQuarter", [770.0, 1010.0, 794.0, 1070.0])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


if __name__ == "__main__":
    unittest.main()
