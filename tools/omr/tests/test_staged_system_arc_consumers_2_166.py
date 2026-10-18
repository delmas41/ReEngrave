"""ROADMAP 2.166 -- `tie_pair` and `arc_kind` READ `Q.SYSTEM_ARC` (the joined, once-per-system arc).

CONNECT, NEVER GUESS: a system arc fills in a tie ONLY where the local flank search found no head at an end
(`no_start_head`/`no_stop_head`/`no_head_near_the_arc`) AND the joined curve's two ends landed on two different heads
at one staff position with nothing between (`two_heads_one_position_adjacent`). Every other shape, and every local
refusal that is a positive finding (`not_adjacent`, `no_pair_at_one_position`), stays abstained. Each refusal carries
its positive control in the same class.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.record import Log, Outcome, Q, READERS

from .test_staged_tie_pair import ORDER, _arc, _cells, _head


def _scene(shape="two_heads_one_position_adjacent", with_row=True, anchors=True, cls="tie"):
    log = Log()
    _cells(log, 4)
    a = _head(log, 0, 0, 150.0, 100.0)
    b = _head(log, 3, 0, 650.0, 100.0)             # far past the local search reach
    h1 = _arc(log, 0, 5, 165.0, 200.0, cls=cls)
    h2 = _arc(log, 3, 5, 600.0, 645.0, cls=cls)
    if with_row:
        log.observe(h1, Q.SYSTEM_ARC, shape, reader=READERS.CV_SYSTEM_ARC, frame="page", score=None,
                    pieces=[h1.to_key(), h2.to_key()], cut_at_barline=True,
                    anchor_left=a.to_key() if anchors else None, anchor_right=b.to_key() if anchors else None,
                    anchor_dy_spaces=0.0)
    log.freeze()
    adjudicate.run(log, order=ORDER)
    return log, a, b, h1, h2


class TestTiePairReadsTheSystemArc(unittest.TestCase):
    def test_control_without_the_row_it_abstains(self):
        log, a, b, h1, h2 = _scene(with_row=False)
        v = log.verdict(Q.TIE_PAIR, h1)
        self.assertNotEqual(v.outcome, Outcome.DECIDED)

    def test_anchored_adjacent_same_position_pairs_both_halves(self):
        log, a, b, h1, h2 = _scene()
        want = {"start": a.to_key(), "stop": b.to_key()}
        for g in (h1, h2):
            v = log.verdict(Q.TIE_PAIR, g)
            self.assertEqual(v.outcome, Outcome.DECIDED, (g.to_key(), v.detail))
            self.assertEqual(v.value, want)
            self.assertEqual(v.reason, "paired_by_system_arc")

    def test_two_positions_stays_abstained(self):
        log, a, b, h1, h2 = _scene(shape="two_positions")
        self.assertNotEqual(log.verdict(Q.TIE_PAIR, h1).outcome, Outcome.DECIDED)

    def test_one_position_heads_between_stays_abstained(self):
        log, a, b, h1, h2 = _scene(shape="one_position_heads_between")
        self.assertNotEqual(log.verdict(Q.TIE_PAIR, h1).outcome, Outcome.DECIDED)

    def test_an_unanchored_end_stays_abstained(self):
        log, a, b, h1, h2 = _scene(anchors=False)
        self.assertNotEqual(log.verdict(Q.TIE_PAIR, h1).outcome, Outcome.DECIDED)

    def test_a_slur_is_never_paired(self):
        log, a, b, h1, h2 = _scene(cls="slur")
        self.assertNotEqual(log.verdict(Q.TIE_PAIR, h1).outcome, Outcome.DECIDED)


class TestArcKindRecordsTheSystemArc(unittest.TestCase):
    def test_recorded_never_acted_on(self):
        log, a, b, h1, h2 = _scene(shape="two_positions")
        v = log.verdict(Q.ARC_KIND, h1)
        self.assertEqual(v.value, "tie")                  # the detector's class stands
        sa = v.detail["grammar"]["system_arc"]
        self.assertEqual(sa["shape"], "two_positions")
        self.assertFalse(sa["agrees_with_reading"])

    def test_control_no_row_no_record(self):
        log, a, b, h1, h2 = _scene(with_row=False)
        self.assertNotIn("system_arc", log.verdict(Q.ARC_KIND, h1).detail["grammar"])


class TestEraseExemptionNeedsTheLeftEdgeTest(unittest.TestCase):
    """The tiny-box erase exemption holds only for 2.164's arc tail: left edge AND no head-tall oval."""

    def _fixture(self):
        import numpy as np
        from types import SimpleNamespace
        from tools.omr.staged import record as R
        page = np.full((200, 400), 255, dtype=np.uint8)
        page[100:103, 100:130] = 0                          # a thin stroke (3 px = 0.3 sp)
        page[90:110, 250:262] = 0                           # a real head-tall blob
        cell = SimpleNamespace(bbox_page_px=[100, 50, 300, 150])
        g = R.glyph(0, 0, 0, 1, 0).to_key()
        return page, {(0, 0, 0, 1): cell}, g

    def test_a_stroke_at_the_left_edge_is_exempt(self):
        from tools.omr.staged import arcs_system as A
        page, cells, g = self._fixture()
        self.assertTrue(A._is_arc_tail_box(g, (100, 95, 130, 108), page, cells, 10.0))

    def test_control_a_head_tall_blob_is_not(self):
        from tools.omr.staged import arcs_system as A
        page, cells, g = self._fixture()
        self.assertFalse(A._is_arc_tail_box(g, (250, 90, 262, 110), page, cells, 10.0))   # also not at the left edge

    def test_control_a_blob_AT_the_left_edge_is_not(self):
        import numpy as np
        from tools.omr.staged import arcs_system as A
        page, cells, g = self._fixture()
        page[90:110, 100:112] = 0
        self.assertFalse(A._is_arc_tail_box(g, (100, 90, 112, 110), page, cells, 10.0))

    def test_flag_off_or_unknown_cell_keeps_the_box(self):
        import os
        from tools.omr.staged import arcs_system as A
        page, cells, g = self._fixture()
        self.assertFalse(A._is_arc_tail_box(g, (100, 95, 130, 108), page, {}, 10.0))
        os.environ["OMR_ARC_TAIL_NOT_A_HEAD"] = "0"
        try:
            self.assertFalse(A._is_arc_tail_box(g, (100, 95, 130, 108), page, cells, 10.0))
        finally:
            del os.environ["OMR_ARC_TAIL_NOT_A_HEAD"]


if __name__ == "__main__":
    unittest.main()
