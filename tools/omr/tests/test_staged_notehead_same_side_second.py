"""ROADMAP 2.40: DECISIONS 2026-09-30, Sean -- "a second is always on
opposite sides of the stem." Widens 2.30's `_notehead_duplicate_box_refusal`
for ONE case its 0.25 sp centre gate misses: two same-class, OVERLAPPING
notehead boxes that share ONE `Q.STEM` row and stand on the SAME side of it
are one physical head boxed twice, even up to 0.75 sp apart (the midpoint
between a second, 0.5 sp, and a third, 1.0 sp) -- because a REAL second
always straddles the stem, so "same side" is never a real interval at any
distance this rule tests.

⚠️ RUN RED FIRST, against the tree before this branch's edit to
`notehead_precision.py`: `test_same_side_overlapping_pair_past_2_30s_gate_is_
refused` fails because `_notehead_same_side_second_refusal` does not exist
and the pair (dy 0.5 sp, past 2.30's 0.25 sp gate) comes back
`value=False, reason="notehead"` on both boxes.

⚠️ THE POSITIVE CONTROLS (CLAUDE.md §6b), each failing for a DIFFERENT
reason a sloppy rule could pass on:
  - `test_same_side_pair_past_the_0_75_sp_gate_stands` -- a real third
    (dy 1.0 sp, past the widened gate too) is not caught by widening it
    further than measured.
  - `test_non_overlapping_adjacent_pair_stands` -- two real, separate notes
    with no box overlap at all are not refused just for standing near a
    shared stem.
  - `test_no_stem_read_does_not_refuse_but_is_counted` -- where the stem
    side cannot be read, the rule may not convert "cannot tell" into an
    answer (CLAUDE.md rule 8); it must still record the case rather than
    drop it silently (CLAUDE.md §4b).

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.tests.test_staged_notehead_precision import (
    CELL, Log, _cell_geometry, _notehead, _run, _verdict)


def _stem(log, *, x_c, y_c, w_c=20.0, h_c=200.0):
    """One CV-read stem box, cell canonical, `Q.STEM`'s own `[x, y, w, h]`
    shape (NOT `x, y0, y1`) -- `gather._gather_beam_and_stem_rows`'s own
    frame, restated here rather than imported (this is a test fixture, not a
    production reader)."""
    log.observe(CELL, Q.STEM, (x_c, y_c, w_c, h_c),
               reader=READERS.CV_LINES, frame="cell:0")


class TestNoteheadSameSideSecond(unittest.TestCase):
    """`_notehead_same_side_second_refusal`, in isolation."""

    def test_same_side_overlapping_pair_past_2_30s_gate_is_refused(self):
        """Two boxes 0.5 sp apart (past 2.30's 0.25 sp centre gate, so 2.30
        itself does not fire), overlapping in ink, sharing ONE stem, BOTH
        centres on the same side of it. One mark boxed twice."""
        log = Log()
        _cell_geometry(log)
        lo = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        hi = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=250.0, w_c=140.0, h_c=100.0, conf=0.6)  # dy=0.5 sp
        # Stem spans both heads' y-range and sits inside both x-ranges
        # (200-340); both centres (270) fall on its right, i.e. the SAME
        # side.
        _stem(log, x_c=260.0, y_c=190.0, w_c=20.0, h_c=200.0)
        log = _run(log)

        v_lo = _verdict(log, lo)
        v_hi = _verdict(log, hi)
        self.assertEqual(v_lo.outcome, Outcome.DECIDED)
        self.assertIs(v_lo.value, True)
        self.assertEqual(v_lo.reason, "same_side_second")

        self.assertEqual(v_hi.outcome, Outcome.DECIDED)
        self.assertIs(v_hi.value, False)
        self.assertEqual(v_hi.reason, "notehead")

    def test_same_side_pair_past_the_0_75_sp_gate_stands(self):
        """⚠️ THE CONTROL THAT CAN FAIL (dy=1.0 sp, a real third). Overlapping
        in ink, sharing one stem, same side -- but PAST
        `NOTEHEAD_SAME_SIDE_MAX_DY_STAFF_SPACES`. Not refused."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=200.0, w_c=140.0, h_c=110.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=300.0, w_c=140.0, h_c=110.0, conf=0.6)  # dy=1.0 sp
        _stem(log, x_c=260.0, y_c=190.0, w_c=20.0, h_c=250.0)
        log = _run(log)

        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, False)

    def test_non_overlapping_adjacent_pair_stands(self):
        """Two real, separate notes far apart in x (no box overlap at all),
        near a shared stem's y-span -- never refused; there is no ink
        overlap to make this "one mark"."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=900.0,
                     y_c=230.0, w_c=140.0, h_c=100.0, conf=0.6)
        _stem(log, x_c=260.0, y_c=190.0, w_c=20.0, h_c=200.0)
        log = _run(log)

        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, False)

    def test_no_stem_read_does_not_refuse_but_is_counted(self):
        """The SAME overlapping, 0.5 sp pair as the first test, but with NO
        `Q.STEM` row at all. CLAUDE.md rule 8: a missing witness may not be
        converted into an answer -- neither box is refused -- but the case
        is still recorded (CLAUDE.md §4b), not silently dropped."""
        log = Log()
        _cell_geometry(log)
        lo = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        hi = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=250.0, w_c=140.0, h_c=100.0, conf=0.6)
        log = _run(log)

        v_lo = _verdict(log, lo)
        v_hi = _verdict(log, hi)
        self.assertIs(v_lo.value, False)
        self.assertIs(v_hi.value, False)
        self.assertEqual(v_lo.reason, "notehead")
        signal = (v_lo.detail or {}).get("same_side_signal")
        self.assertIsNotNone(signal)
        self.assertTrue(signal.get("no_stem_read"))

    def test_a_real_third_with_tall_overlapping_boxes_stands(self):
        """⚠️ MANAGER FINDING, 2026-09-30, Litolff p3 `glyph/3/0/0/2/4` +
        `glyph/3/0/0/2/9` (and the `/1`+`/3` pair at x~920): two REAL heads a
        THIRD apart, both in spaces above the staff between ledger lines.
        The detector's boxes are TALLER than the heads (this staff's own
        spacing ~15.5 page px, box height ~22 px), so they overlap by ~7 px
        even though the heads themselves do not touch -- `restate_pitch`
        rounds each box centre and writes a SECOND (F6/E6), which is why this
        reads at first as a doubled box, but the ink is two real heads. THIS
        RULE must not refuse the pair: dy ~0.9 sp is past the 0.75 sp gate."""
        log = Log()
        _cell_geometry(log)
        # h_c=142 canonical (1.42 sp, the same over-tall-box ratio the
        # manager measured on the print) so the two boxes overlap by ~52
        # canonical px despite standing 0.9 sp apart at the centres.
        lo = _notehead(log, 0, cls="noteheadBlackInSpace",
                      x_c=200.0, y_c=0.0, w_c=140.0, h_c=142.0, conf=0.6)
        hi = _notehead(log, 1, cls="noteheadBlackInSpace",
                      x_c=200.0, y_c=90.0, w_c=140.0, h_c=142.0, conf=0.6)
        _stem(log, x_c=260.0, y_c=-40.0, w_c=20.0, h_c=300.0)
        log = _run(log)

        self.assertIs(_verdict(log, lo).value, False)
        self.assertIs(_verdict(log, hi).value, False)

    def test_the_reason_is_named_apart_from_2_30s(self):
        """The two mechanisms stay tellable apart on a census (CLAUDE.md
        §4d): this rule's own reason string is not 2.30's."""
        self.assertNotEqual(NP.NOTEHEAD_SAME_SIDE_REASON,
                            "notehead_is_a_duplicate_box")


if __name__ == "__main__":
    unittest.main()
