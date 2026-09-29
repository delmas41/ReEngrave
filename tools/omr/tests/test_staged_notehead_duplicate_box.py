"""ROADMAP 2.30: a notehead physical mark boxed more than once by a
SHATTERING plate was never refused — the SAME mechanism ROADMAP 2.15 already
measured and shipped for RESTS (`family_precision.adjudicate_rest_is_not_a_
rest`'s `_duplicate_box_refusal`), ported to noteheads
(`notehead_precision._notehead_duplicate_box_refusal`).

⚠️ RUN RED FIRST, against the tree before this branch's edit to
`notehead_precision.py`: `test_two_overlapping_same_class_boxes_the_lower_
confidence_one_loses` fails because `adjudicate_notehead_is_not_a_notehead`
never compared a notehead box against another notehead box in its cell, so
BOTH verdicts come back `value=False, reason="notehead"`.

⚠️ THE POSITIVE CONTROL (CLAUDE.md §6b) is
`test_two_separate_noteheads_no_overlap_are_both_kept`: without it, a rule
that refused every notehead in a cell regardless of geometry would also
pass the RED->GREEN test.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged.record import Outcome
from tools.omr.staged.adjudicators import family_precision as FP
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.tests.test_staged_notehead_precision import (
    Log, _cell_geometry, _notehead, _run, _verdict)


class TestNoteheadDuplicateBox(unittest.TestCase):
    """`_notehead_duplicate_box_refusal`, in isolation."""

    def test_two_overlapping_same_class_boxes_the_lower_confidence_one_loses(
            self):
        """Two `noteheadBlackInSpace` boxes overlapping at 2.15's own
        crop-confirmed IoU range (~0.43) -- one mark, fragmented ink. The
        higher-confidence box survives; the lower one is refused and named."""
        log = Log()
        _cell_geometry(log)
        lo = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        hi = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=240.0,
                      y_c=200.0, w_c=140.0, h_c=100.0, conf=0.6)
        log = _run(log)

        v_lo = _verdict(log, lo)
        v_hi = _verdict(log, hi)
        self.assertEqual(v_lo.outcome, Outcome.DECIDED)
        self.assertIs(v_lo.value, True)
        self.assertEqual(v_lo.reason, "notehead_is_a_duplicate_box")

        self.assertEqual(v_hi.outcome, Outcome.DECIDED)
        self.assertIs(v_hi.value, False)
        self.assertEqual(v_hi.reason, "notehead")

    def test_two_separate_noteheads_no_overlap_are_both_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. Two real noteheads far enough apart
        that their boxes do not touch (IoU exactly 0.0) -- an ordinary bar
        with two notes. Neither is refused for being a duplicate."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=200.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=900.0,
                     y_c=200.0, conf=0.6)
        log = _run(log)

        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, False)

    def test_overlapping_DIFFERENT_class_boxes_are_left_alone(self):
        """A role-twin pair (`noteheadBlackInSpace`/`noteheadHalfInSpace`)
        at high overlap is a chord member's VALUE disagreement (FINDINGS
        §17c, "2.12g's role twins"), not a duplicate-ink question this rule
        answers -- refusing both would discard a real note. Deliberately
        NOT refused, unlike `family_precision`'s rest rule."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=200.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadHalfInSpace", x_c=201.0,
                     y_c=200.0, conf=0.5)
        log = _run(log)

        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, False)

    def test_the_two_duplicate_iou_floors_cannot_drift_apart(self):
        """`NOTEHEAD_DUPLICATE_IOU_MIN` cites, rather than restates,
        ROADMAP 2.15's `REST_DUPLICATE_IOU_MIN` (module docstrings on both
        sides). Pinned equal so an edit to one is caught here, not on the
        next document that disagrees."""
        self.assertEqual(NP.NOTEHEAD_DUPLICATE_IOU_MIN,
                         FP.REST_DUPLICATE_IOU_MIN)


if __name__ == "__main__":
    unittest.main()
