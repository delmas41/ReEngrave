"""ROADMAP 2.252 r2 -- a tie over a dyad is the same-position pair on the ARC'S OWN SIDE (`OMR_TIE_PAIR_ARC_SIDE`, default OFF).

Sean 2.75 (page-facts): an arc above its notes joins the top note, below joins the bottom. Sean's 2.252 tiles 3, 7, 10, 12: a tie
over two half notes a third apart admits both members' pairs and narrowed `more_than_one_pair` (nothing written)."""
from __future__ import annotations

import os
import unittest

from tools.omr.staged.adjudicators import ownership as O


def _pair(name, y):            # (dx, dy, rl, rr, il, ir, yl, yr)
    return (1.0, 0.0, name + "L", name + "R", 0, 1, y, y)


UPPER, LOWER = _pair("up", 100.0), _pair("lo", 116.0)


class TestArcSide(unittest.TestCase):

    def test_an_arc_above_both_takes_the_top_pair(self):
        self.assertIs(O._pair_on_the_arcs_side([UPPER, LOWER], 85.0), UPPER)

    def test_an_arc_below_both_takes_the_bottom_pair(self):
        self.assertIs(O._pair_on_the_arcs_side([UPPER, LOWER], 130.0), LOWER)

    def test_an_arc_between_the_pairs_still_narrows(self):          # the control that can fail
        self.assertIsNone(O._pair_on_the_arcs_side([UPPER, LOWER], 108.0))

    def test_two_pairs_at_the_extreme_position_still_narrow(self):  # a duplicate head: not this rule's to choose
        self.assertIsNone(O._pair_on_the_arcs_side([UPPER, _pair("dup", 101.0), LOWER], 85.0))

    def test_one_position_only_is_not_this_rule(self):
        self.assertIsNone(O._pair_on_the_arcs_side([UPPER, _pair("dup", 100.0)], 85.0))

    def test_flag_default_off(self):
        old = os.environ.pop(O.TIE_ARC_SIDE_ENV, None)
        try:
            self.assertFalse(O.tie_arc_side_enabled())
            os.environ[O.TIE_ARC_SIDE_ENV] = "on"
            self.assertTrue(O.tie_arc_side_enabled())
        finally:
            os.environ.pop(O.TIE_ARC_SIDE_ENV, None)
            if old is not None:
                os.environ[O.TIE_ARC_SIDE_ENV] = old


if __name__ == "__main__":
    unittest.main()
