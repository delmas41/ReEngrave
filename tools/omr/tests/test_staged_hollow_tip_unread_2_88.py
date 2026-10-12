"""ROADMAP 2.88 -- a hollow head whose stem tip the tip reader CANNOT TELL is still a half, on the head's own reading.

2.83's shape reader declines the tip where it `crosses_both_sides`, has `no_room`, is `ink_not_flag_shaped` ...; the old clean-tip window
that used to say "clean" there is not trusted again (it made Brahms pdf 11 `glyph/11/1/10/3/10`, a fragment, a half). A hollow head cannot
carry a flag or a beam, so the tip only guards against a false hollow reading; the guard is now the head's own: the hollow reading on two of
the three rasters, a head-shaped box (not a sliver, not a cluster, not wider than a head), and a cannot-tell that is not an `occupied` tip.

RUN RED FIRST against the unrepaired tree (`51a01593`): the positive tests fail there; every control (a flag read at the tip, a dispute, a
filled head, one raster only, a sliver, a cluster, a wide box, an occupied tip, a head at the other end, no abstention at all) passes on both.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import (CELL, SPACE, _beam, _staff_space, _stem, _stem_tip_ink)


def _unread_tip(log, stem_row_id, why, end="top"):
    """The abstention `gather._observe_stem_tip_ink` files where the shape reader cannot tell: reason `ambiguous`, `why` in the detail."""
    log.abstain(CELL, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP, frame="cell:0", reason=ABSTAIN.AMBIGUOUS,
                stem_row_id=stem_row_id, end=end, why=why)


def _two_raster_ink(log, g, *, rasters=("ink_raw", "ink_net"), center=0.45, ring=0.85, filled=False):
    """ONE `Q.NOTEHEAD_INK` row carrying every named raster, as `gather.gather_notehead_ink` files it."""
    c, r = (1.0, 1.0) if filled else (center, ring)
    detail = {k: {"best": max(c, r), "best_window": "ring", "windows": {"center": c, "ring": r}} for k in rasters}
    return log.observe(g, Q.NOTEHEAD_INK, round(max(c, r), 4), reader=READERS.CV_NOTEHEAD_INK, frame="cell:0", **detail)


class TestAHollowHeadWithAnUnreadTipIsStillAHalf(unittest.TestCase):

    def _head(self, log, *, box_w=20, box_h=16, beam="decoy"):
        _staff_space(log)
        if beam == "ran_empty":
            log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES, frame="cell:0", reason=ABSTAIN.NO_LINE_ACCEPTED)
        else:
            _beam(log, y=2, x0=400, x1=460)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, box_w, box_h), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=38, h=60)
        return g, s

    def _verdict(self, log, g):
        adjudicate.run(log)
        return log.verdict(Q.DURATION, g)

    def test_unread_tip_two_rasters_head_shaped_box_is_a_decided_half_RED(self):
        for why in ("crosses_both_sides", "no_room", "ink_not_flag_shaped", "runs_on", "ink_past_the_tip"):
            log = Log()
            g, s = self._head(log, beam="ran_empty")
            _two_raster_ink(log, g)
            _unread_tip(log, s.id, why)
            v = self._verdict(log, g)
            self.assertEqual(v.outcome, Outcome.DECIDED, why)
            self.assertEqual(v.reason, "hollow_head_bare_stem", why)
            self.assertEqual(v.value["beats"], 2.0)
            self.assertEqual(v.detail["tip_unread"], why)

    def test_the_same_in_a_cell_with_beams(self):
        log = Log()
        g, s = self._head(log)
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")

    # ---- the controls: each passes on the unrepaired tree AND here ----
    def test_CONTROL_a_flag_READ_at_the_tip_is_not_a_half(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, witness="shape", hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_CONTROL_a_disputed_tip_is_not_a_half(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, tip_disagree=True, witness="disputed",
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_CONTROL_a_FILLED_head_with_an_unread_tip_is_not_a_half(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g, filled=True)
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.outcome, Outcome.DECIDED)

    def test_hollow_on_ONE_raster_only_stays_narrowed_RED(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g, rasters=("ink_raw",))
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")

    def test_a_SLIVER_box_stays_narrowed(self):
        log = Log()
        g, s = self._head(log, box_h=int(0.5 * SPACE) if SPACE else 6, beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_a_WIDE_box_stays_narrowed(self):
        log = Log()
        g, s = self._head(log, box_w=int(2.4 * 16), beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_a_CLUSTER_box_stays_narrowed(self):
        log = Log()
        g, s = self._head(log, box_h=3 * 16, beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "crosses_both_sides")
        v = self._verdict(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_an_OCCUPIED_tip_stays_narrowed(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "occupied")
        v = self._verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_a_head_AT_the_other_end_stays_narrowed(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "head_at_this_end")
        v = self._verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_the_abstention_at_the_WRONG_end_is_not_read(self):
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        _unread_tip(log, s.id, "crosses_both_sides", end="bottom")
        v = self._verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_NO_tip_row_at_all_stays_narrowed(self):
        """Rule 8: not even an abstention to read -- the reader never ran, and that is not 'cannot tell why'."""
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g)
        v = self._verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_CONTROL_a_CLEAN_tip_still_decides_the_half(self):
        """The control that can fail: the 2.70 half over a clean tip is untouched (one raster is enough there)."""
        log = Log()
        g, s = self._head(log, beam="ran_empty")
        _two_raster_ink(log, g, rasters=("ink_raw",))
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        v = self._verdict(log, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")
        self.assertNotIn("tip_unread", v.detail)


if __name__ == "__main__":
    unittest.main()
