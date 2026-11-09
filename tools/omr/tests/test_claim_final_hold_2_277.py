"""ROADMAP 2.277, the landing hold (Sean's Brahms file-change tiles 1 and 2): a claim may rename a refusal's first cause and remove a false gap; it may not
change what the readers of the SHAPE reason see, promote a neighbour from GUESSED to READ, or cost a read note. Every control can fail."""
from __future__ import annotations

import types
import unittest

from tools.omr.staged import claim_final as CF
from tools.omr.staged import export as E
from tools.omr.staged.adjudicators import aug_dot_join as ADJ
from tools.omr.staged.adjudicators import narrow_rest as NR
from tools.omr.staged.adjudicators import rhythm as RH


class TestTheClaimRenamesTheCauseOnly(unittest.TestCase):
    def test_barline_is_shape_equivalent_and_a_later_layer_is_not(self):
        self.assertEqual(CF.SHAPE_EQUIVALENT_REASONS, ("claimed_by:barline",))
        self.assertIn("claimed_by:page_claim", RH.NOT_A_NOTE_REFUSALS)       # a slash's ink has no duration
        self.assertNotIn("claimed_by:barline", RH.NOT_A_NOTE_REFUSALS)       # a barline sliver keeps the duration view its too_narrow had

    def test_the_dot_rescue_and_the_narrow_rest_look_see_a_barline_refusal_as_the_shape_refusal(self):
        self.assertIn("claimed_by:barline", ADJ.DOT_SHAPED_REFUSALS)
        self.assertIn("too_narrow", ADJ.DOT_SHAPED_REFUSALS)

    def test_CONTROL_the_meter_column_test_is_unchanged_for_other_reasons(self):
        # a refusal that is neither too_narrow nor the barline claim never reaches the meter-column branch
        ev = types.SimpleNamespace(rows=lambda *a, **k: [], subject=types.SimpleNamespace())
        self.assertIsNone(RH._not_a_note_mark(ev, types.SimpleNamespace(reason="is_a_dot")))
        self.assertEqual(RH._not_a_note_mark(ev, types.SimpleNamespace(reason="claimed_by:page_claim")), "claimed_by:page_claim")

    def test_the_claim_reasons_are_no_gap(self):
        for r in E._CLAIM_GAP_REASONS:
            self.assertIn(r, E._NOT_A_GAP_REASONS)

    def test_CONTROL_a_shape_refusal_is_still_a_gap(self):
        self.assertNotIn("too_narrow", E._NOT_A_GAP_REASONS)


class TestNoPromotion(unittest.TestCase):
    def _bar(self):
        return [{"kind": "note", "noteheads": [{"pitch": "D4"}]}, {"kind": "rest", "rest": {"beats": 1}},
                {"kind": "note", "noteheads": [{"pitch": "E4", "guess": {"rule": "own"}}]}]

    def test_a_bar_that_lost_a_false_gap_keeps_its_notes_guessed(self):
        evs = self._bar()
        n = E._mark_claimed_gap_events(evs)
        self.assertEqual(n, 2)
        self.assertEqual(evs[0]["noteheads"][0]["guess"]["rule"], "bar_sum_wrong_after_claimed_gap")
        self.assertEqual(evs[1]["rest"]["guess"]["rule"], "bar_sum_wrong_after_claimed_gap")

    def test_CONTROL_a_guess_a_note_already_carries_is_never_replaced(self):
        evs = self._bar()
        E._mark_claimed_gap_events(evs)
        self.assertEqual(evs[2]["noteheads"][0]["guess"]["rule"], "own")

    def test_CONTROL_a_bar_with_nothing_to_mark_marks_nothing(self):
        self.assertEqual(E._mark_claimed_gap_events([]), 0)


if __name__ == "__main__":
    unittest.main()
