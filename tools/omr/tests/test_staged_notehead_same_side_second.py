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


def _ink(log, g, *, net_best):
    """`Q.NOTEHEAD_INK` on glyph `g`, carrying ONLY the `ink_net.best`
    field `_notehead_ink_net` reads -- the staff-line-ERASED fill fraction
    (manager review, S6: the KEEP choice reads this, never detector
    score)."""
    log.observe(g, Q.NOTEHEAD_INK, net_best, reader=READERS.CV_NOTEHEAD_INK,
               frame="cell:0", ink_net={"best": net_best}, ink_raw=None)


class TestNoteheadSameSideSecond(unittest.TestCase):
    """`_notehead_same_side_second_refusal`, in isolation."""

    def test_same_side_overlapping_pair_past_2_30s_gate_is_refused(self):
        """Two boxes 0.5 sp apart (past 2.30's 0.25 sp centre gate, so 2.30
        itself does not fire), overlapping in ink, sharing ONE stem, BOTH
        centres on the same side of it. One mark boxed twice -- `hi` carries
        the real head ink (`ink_net.best` 0.85) and survives; `lo` sits
        mostly on blank paper (0.10) and is refused, REGARDLESS of `lo`
        having the lower detector confidence too (score is not read here at
        all, manager review S6). ⚠️ `hi` is glyph 0 (processed FIRST by
        `subjects_for`'s ascending-subject sort) so its own verdict is
        DECIDED `False` before `lo` (glyph 1) is evaluated -- round 3's
        partner-survival check (`same_side_signal.partner_refused`) needs
        the partner ALREADY decided to let a real refusal through at all."""
        log = Log()
        _cell_geometry(log)
        hi = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=250.0, w_c=140.0, h_c=100.0, conf=0.6)  # dy=0.5 sp
        lo = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                      y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        _ink(log, lo, net_best=0.10)
        _ink(log, hi, net_best=0.85)
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

    def test_the_higher_score_box_on_blank_paper_is_the_one_refused(self):
        """⚠️ MANAGER FINDING, S6 (`cell/3/0/8/7`): the first build chose the
        survivor by DETECTOR SCORE and kept an EMPTY box over the real head.
        RED against that build: `hi_score` (conf 0.9) sits on blank paper
        (`ink_net.best` 0.08, S6's own shape -- mostly white paper plus one
        staff line) while `lo_score` (conf 0.3) carries the real ink (0.90).
        The higher-score, blank-paper box MUST be the one refused. ⚠️
        `lo_score` is glyph 0 (processed FIRST) so it is DECIDED `False`
        before `hi_score` (glyph 1) is evaluated -- round 3's partner-
        survival check needs the partner already decided."""
        log = Log()
        _cell_geometry(log)
        lo_score = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                            y_c=250.0, w_c=140.0, h_c=100.0, conf=0.3)
        hi_score = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                            y_c=200.0, w_c=140.0, h_c=100.0, conf=0.9)
        _ink(log, hi_score, net_best=0.08)
        _ink(log, lo_score, net_best=0.90)
        _stem(log, x_c=260.0, y_c=190.0, w_c=20.0, h_c=200.0)
        log = _run(log)

        v_hi_score = _verdict(log, hi_score)
        v_lo_score = _verdict(log, lo_score)
        self.assertIs(v_hi_score.value, True,
                      "the blank-paper box (higher score) must be refused")
        self.assertEqual(v_hi_score.reason, "same_side_second")
        self.assertIs(v_lo_score.value, False,
                      "the real-ink box (lower score) must stand")

    def test_no_ink_witness_does_not_refuse_but_is_counted(self):
        """The SAME overlapping, same-side, same-stem pair as the first
        test, but neither glyph carries a `Q.NOTEHEAD_INK` row at all
        (S6's lesson generalised: with no ink witness for the pair, rule 8
        applies exactly as it does for a missing stem) -- refuse NEITHER,
        but still count the case rather than silently drop it."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=200.0, w_c=140.0, h_c=100.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                     y_c=250.0, w_c=140.0, h_c=100.0, conf=0.6)
        _stem(log, x_c=260.0, y_c=190.0, w_c=20.0, h_c=200.0)
        log = _run(log)

        v_a = _verdict(log, a)
        v_b = _verdict(log, b)
        self.assertIs(v_a.value, False)
        self.assertIs(v_b.value, False)
        signal = (v_a.detail or {}).get("same_side_signal")
        self.assertIsNotNone(signal)
        self.assertTrue(signal.get("no_ink_witness"))

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

    def test_a_partner_thats_itself_refused_is_never_the_keeper(self):
        """⚠️ MANAGER REVIEW ROUND 3, one of the 3 real cases found on
        Litolff p3 (`cell/3/0/10/6`): the rule's chosen "better" partner
        (higher ink) was a genuinely TOO-NARROW sliver -- itself refused by
        2.4a's `too_narrow` -- so BOTH boxes of one real mark ended up
        refused and it had NO surviving box at all, worse than the doubled
        box this rule exists to fix.

        `partner` (glyph 0, processed FIRST -- `subjects_for` sorts by
        subject, ascending glyph index) is a genuine sliver: width 0.5 sp,
        under `TOO_NARROW_MIN_SPACES` (1.0), so 2.4a refuses it as
        `too_narrow` regardless of ink -- and its `ink_net.best` (0.95) is
        deliberately HIGHER than `this`'s (0.30), which is exactly the
        shape that made the first build refuse `this` in the partner's
        favour. `this` (glyph 1) must NOT be refused: its only same-side
        candidate is a box that will not survive, so rule 6/8 says count
        it and leave both alone."""
        log = Log()
        _cell_geometry(log)
        partner = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                           y_c=200.0, w_c=50.0, h_c=100.0, conf=0.6)
        this = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=200.0,
                        y_c=250.0, w_c=140.0, h_c=100.0, conf=0.6)  # dy=0.5sp
        _ink(log, partner, net_best=0.95)
        _ink(log, this, net_best=0.30)
        # Stem sits at the LEFT edge both boxes share (x 205-215) so both
        # centres (225, 270) fall on its right -- the SAME side -- despite
        # the two boxes having very different widths.
        _stem(log, x_c=205.0, y_c=190.0, w_c=10.0, h_c=200.0)
        log = _run(log)

        v_partner = _verdict(log, partner)
        v_this = _verdict(log, this)
        self.assertIs(v_partner.value, True)
        self.assertEqual(v_partner.reason, "too_narrow")

        self.assertIs(v_this.value, False,
                      "must not be refused in favour of a partner that "
                      "does not survive")
        self.assertEqual(v_this.reason, "notehead")
        signal = (v_this.detail or {}).get("same_side_signal")
        self.assertIsNotNone(signal)
        self.assertTrue(signal.get("partner_refused"))

    def test_the_reason_is_named_apart_from_2_30s(self):
        """The two mechanisms stay tellable apart on a census (CLAUDE.md
        §4d): this rule's own reason string is not 2.30's."""
        self.assertNotEqual(NP.NOTEHEAD_SAME_SIDE_REASON,
                            "notehead_is_a_duplicate_box")


if __name__ == "__main__":
    unittest.main()
