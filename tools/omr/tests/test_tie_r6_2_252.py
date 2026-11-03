"""ROADMAP 2.252 r6 (STAGED; rides `OMR_HEAD_HOLE_POSITION`, default ON): a staff line found LOCALLY through an arc box on a tilted
staff (Sean's r5 tile 10: a 'tie' box on the fourth line kept as an arc), and a head whose own two readings name two positions."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import head_hole_position as HP

SP = 16.0


def _page_with_line(y_line: int, w: int = 200, h: int = 120):
    img = np.full((h, w), 255, dtype=np.uint8)
    img[y_line - 1:y_line + 2, :] = 0                  # a 3 px staff line across the page
    return img


class TestArcBoxOnATiltedLine(unittest.TestCase):
    """The staff-wide line ys stand 6-8 px off the line at the box's x; the box is a 5 px sliver ON the line."""

    def setUp(self):
        self.img = _page_with_line(60)
        self.box = (40.0, 57.5, 100.0, 62.5)             # the line inside, a 'tie' box 0.31 sp tall
        self.lines = [52.0, 68.0]                       # staff-wide values 8 px above and below: outside the 0.15 sp pad

    def test_OFF_reads_no_line_and_a_full_curve(self):
        m = G.arc_ink_shape(self.img, self.box, SP, self.lines)
        self.assertEqual(m["lines_in_box"], 0)
        self.assertEqual(m["coverage"], 1.0)

    def test_local_line_is_found_once_and_taken_out(self):
        m = G.arc_ink_shape(self.img, self.box, SP, self.lines, local_lines=True)
        self.assertEqual(m["lines_in_box"], 1)          # two staff-wide ys snap to ONE line run
        self.assertEqual(m.get("lines_found_locally"), 1)
        self.assertLess(m["coverage"], 0.35)            # nothing curved is left: the decision refuses it as a staff line

    def test_RED_a_tie_along_a_line_already_taken_out_is_not_erased(self):
        # first build: a staff-wide y just outside the pad snapped to the line the in-window y had already taken out, and grew
        # into the tie's half-full rows beside it (Litolff p3 `3/0/3/4/2`: coverage 0.76 -> 0.32, refused as a staff line)
        img = _page_with_line(60)
        for x in range(40, 100):                         # a flat tie lying along the line, just under it
            yc = int(round(63 + 3 * ((x - 70) / 30.0) ** 2))
            img[yc:yc + 2, x] = 0
        box, lines = (40.0, 56.0, 100.0, 70.0), [60.0, 72.5]
        off = G.arc_ink_shape(img, box, SP, lines)
        on = G.arc_ink_shape(img, box, SP, lines, local_lines=True)
        self.assertEqual(off["coverage"], on["coverage"])
        self.assertEqual(off["lines_in_box"], on["lines_in_box"])

    def test_a_curved_tie_near_a_line_is_not_a_line(self):
        img = np.full((120, 200), 255, dtype=np.uint8)
        for x in range(40, 100):                         # a bowed stroke: no row is ink across the box
            yc = int(round(58 + 4 * ((x - 70) / 30.0) ** 2))
            img[yc - 1:yc + 1, x] = 0
        m = G.arc_ink_shape(img, (40.0, 55.0, 100.0, 64.0), SP, self.lines, local_lines=True)
        self.assertEqual(m["lines_in_box"], 0)
        self.assertGreater(m["coverage"], 0.9)


class TestContestedPosition(unittest.TestCase):
    def test_hole_one_step_off_the_box_is_contested(self):
        c = HP.contested_position({"rounded": 0, "hole_refused": "off_grid", "hole_steps": [0.59]}, 0.1)
        self.assertEqual((c["own"], c["alternative"]), (0, 1))

    def test_ink_disagreeing_hole_is_contested(self):
        c = HP.contested_position({"rounded": 1, "hole_refused": "ink_disagrees", "hole_steps": [2.02]}, 1.34)
        self.assertEqual(c["alternative"], 2)

    def test_settled_heads_are_not_contested(self):
        self.assertIsNone(HP.contested_position({"rounded": 1, "from_head_hole": [1.05]}, 1.05))
        self.assertIsNone(HP.contested_position({"rounded": 1}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "same_position", "hole_steps": [1.1]}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "holes:2", "hole_steps": [0.9, 3.0]}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "off_grid", "hole_steps": [3.4]}, 1.2))

    def test_flag(self):
        with mock.patch.dict(os.environ, {"OMR_HEAD_HOLE_POSITION": "0"}):
            self.assertFalse(HP.r6_enabled())
        with mock.patch.dict(os.environ, {"OMR_HEAD_HOLE_POSITION": "1"}):
            self.assertTrue(HP.r6_enabled())


class TestOneEndContested(unittest.TestCase):
    """Sean's r5 tile 3: the start's box reads the top line, its hole 0.59; the stop's hole reads the top space -- the start is named."""

    def test_the_contested_end_is_named(self):
        from tools.omr.staged.adjudicators.ownership import one_end_contested
        a = ({"rounded": 0, "hole_refused": "off_grid", "hole_steps": [0.59]}, 0.1)
        b = ({"rounded": 1, "from_head_hole": [1.05]}, 1.05)
        c = one_end_contested("A", "B", 0, 1, a, b)
        self.assertEqual((c["end"], c["alternative"]), ("A", 1))

    def test_both_or_neither_contested_names_none(self):
        from tools.omr.staged.adjudicators.ownership import one_end_contested
        plain = ({"rounded": 1}, 1.1)
        self.assertIsNone(one_end_contested("A", "B", 0, 1, ({"rounded": 0}, 0.1), plain))
        a = ({"rounded": 0, "hole_refused": "off_grid", "hole_steps": [0.59]}, 0.1)
        b = ({"rounded": 1, "hole_refused": "ink_disagrees", "hole_steps": [0.1]}, 1.2)
        self.assertIsNone(one_end_contested("A", "B", 0, 1, a, b))

    def test_an_alternative_away_from_the_partner_names_none(self):
        from tools.omr.staged.adjudicators.ownership import one_end_contested
        a = ({"rounded": 0, "hole_refused": "off_grid", "hole_steps": [-0.6]}, 0.1)
        self.assertIsNone(one_end_contested("A", "B", 0, 1, a, ({"rounded": 1}, 1.0)))


class TestTieEndUnsure(unittest.TestCase):
    def _rec(self, verdicts, obs):
        from tools.omr.staged.export import Record
        return Record({"record": {"observations": obs, "verdicts": verdicts, "abstentions": []}})

    def test_far_head_ledger_unread_and_contested_hole_are_named(self):
        from tools.omr.staged.export import _tie_end_unsure
        rec = self._rec(
            [{"id": "v1", "quantity": "notehead_position", "subject": "A", "outcome": "abstained", "value": None}],
            [{"quantity": "notehead_staff_position", "subject": "B", "value": 1.34,
              "detail": {"rounded": 1, "hole_refused": "ink_disagrees", "hole_steps": [2.02]}}])
        got = _tie_end_unsure(rec, "A", "B")
        self.assertEqual([g["end"] for g in got], ["A", "B"])
        self.assertEqual(got[0]["why"], "far_head_ledger_unread")
        self.assertEqual(got[1]["alternative"], 2)

    def test_settled_ends_are_not_named(self):
        from tools.omr.staged.export import _tie_end_unsure
        rec = self._rec([{"id": "v1", "quantity": "notehead_position", "subject": "A", "outcome": "decided", "value": -2}],
                        [{"quantity": "notehead_staff_position", "subject": "B", "value": 1.0, "detail": {"rounded": 1}}])
        self.assertEqual(_tie_end_unsure(rec, "A", "B"), [])


class TestJudgedFollowsTallSplit(unittest.TestCase):
    """r5's landing-check UNWRITTEN->WRONG (Litolff `11/0/2/12/2`, Sean "2"): the tall box is refused as the duplicate of the two
    halves split from it; the answer is scored on the halves (same ink), not as a refused note."""

    def _S(self, child_beats):
        refused = {"outcome": "decided", "value": True, "reason": "stacked_head_duplicate"}
        S = {("T", "notehead_is_not_a_notehead"): refused, ("__tall_split__", "T"): ["C1", "C2"]}
        for k, b in zip(("C1", "C2"), child_beats):
            S[(k, "duration")] = {"outcome": "decided", "value": {"beats": b}, "reason": "head_and_marks"}
        return S

    def test_split_child_with_seans_value_is_right(self):
        from tools.omr.staged import judged as J
        st, note = J._duration("T", 2.0, self._S([2.0, 2.0]))
        self.assertEqual(st, "right", note)

    def test_split_child_with_another_value_is_wrong(self):
        from tools.omr.staged import judged as J
        st, _ = J._duration("T", 2.0, self._S([1.0, 1.0]))
        self.assertEqual(st, "wrong")

    def test_an_unsplit_refused_box_is_still_wrong(self):
        from tools.omr.staged import judged as J
        S = {("T", "notehead_is_not_a_notehead"): {"outcome": "decided", "value": True, "reason": "x"}}
        self.assertEqual(J._duration("T", 2.0, S)[0], "wrong")


if __name__ == "__main__":
    unittest.main()
