"""ROADMAP 2.102 -- Sean's four tiles from the held-out check (2026-10-12).

(a) STAGED INFER. A bar the arithmetic sums ignoring a tuplet is not a bar the
    arithmetic can speak for: tile 6 (Dvorak 8, a quarter of a 3-quarter
    tuplet decided an eighth) and tile 10 (Schumann 2, whose cause was NOT a
    tuplet: six two-note columns grouped as twelve events, so the sum counted
    every column twice). `inferences.bar_has_tuplet` is the helper any bar-sum
    rule calls.
(b) STAGED ADJUDICATE. A head `adjudicate_notehead_is_not_a_notehead` already
    refused as a mark that is not a note -- a tremolo slash across a stem
    (tile 17), a C meter sign in a meter column (tile 11) -- has no duration:
    the ink of its box used to be read as a HOLLOW head and decided a half.

Every refusal is paired with a positive control in the same class (CLAUDE.md
6b): a bar with no tuplet still settles; a real hollow half next to nothing
stays a half; a refused-narrow box NOT in a meter column is not touched.
RUN RED FIRST against the unrepaired tree (`fcacfa10`): the RED tests fail there.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, infer, inferences
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import (READERS, Kind, Log, Outcome, Q, Subject,
                                     Verdict)

from tools.omr.tests.test_staged_bare_stem_2_81 import (_Bar, _cell, _run,
                                                         _fired, _sub)
from tools.omr.tests.test_staged_hollow_tip_unread_2_88 import (
    CELL, _staff_space, _two_raster_ink, _unread_tip)
from tools.omr.tests.test_staged_duration import _beam, _stem


def _solve(bar):
    log = bar.finish()
    return log, inferences.solve_bare_stem_bar(log, _cell(0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# (a) tuplets
# ─────────────────────────────────────────────────────────────────────────────


def _half_and_four_bares():
    """4/4: a decided half and FOUR bare stems. Plain arithmetic forces four
    eighths (2 + 4 x .5); but three of them could be a triplet of eighths (one
    beat) with the fourth a quarter -- a second landing. (Dvorak 8, tile 6.)"""
    b = _Bar()
    b.decided(2.0)
    for _ in range(4):
        b.bare()
    return b


class TestABarThatPrintsATupletIsNotSettled(unittest.TestCase):

    def test_CONTROL_without_a_tuplet_the_plain_bar_still_settles(self):
        """The positive control of the class: 3 quarters + a bare stem."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        log, out = _solve(b)
        self.assertEqual(len(out.proposals), 1)
        self.assertIsNone(out.decline)

    def test_a_tuplet_marker_in_the_bar_declines_it_RED(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        b.log.observe(_sub(0, 90), Q.TUPLET_MARKER, "3",
                      reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log, out = _solve(b)
        self.assertEqual(out.decline, "tuplet_in_bar")
        self.assertEqual(out.proposals, [])
        # and nothing reaches the record
        rep = _run(log)
        self.assertEqual(_fired(rep), [])

    def test_bar_has_tuplet_names_its_reason(self):
        b = _Bar()
        b.decided(1.0)
        b.log.observe(_sub(0, 90), Q.TUPLET_MARKER, "3",
                      reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log = b.finish()
        self.assertEqual(inferences.bar_has_tuplet(log, _cell(0, 0)),
                         ("tuplet_marker",))

    def test_bar_has_tuplet_is_empty_where_none_is_read(self):
        b = _Bar()
        b.decided(1.0)
        self.assertEqual(inferences.bar_has_tuplet(b.finish(), _cell(0, 0)), ())

    def test_CONTROL_a_marker_a_human_struck_out_does_not_count(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        m = b.log.observe(_sub(0, 90), Q.TUPLET_MARKER, "3",
                          reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        b.log.record(Verdict(
            id=b._id(), subject=_sub(0, 90), quantity=Q.TUPLET_MARKER_IS_NOT_A_MARKER,
            outcome=Outcome.DECIDED, value=True, decider="human:test",
            reason="human", basis=(m.id,)))
        log, out = _solve(b)
        self.assertEqual(inferences.bar_has_tuplet(log, _cell(0, 0)), ())
        self.assertEqual(len(out.proposals), 1)

    def test_a_decided_tuplet_ratio_is_named_by_the_helper(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        b.log.record(Verdict(
            id=b._id(), subject=_cell(0, 0), quantity=Q.TUPLET_RATIO,
            outcome=Outcome.DECIDED, value={"actual": 3, "normal": 2},
            decider="adjudicate_tuplet", reason="digit"))
        log, out = _solve(b)
        self.assertEqual(inferences.bar_has_tuplet(log, _cell(0, 0)),
                         ("tuplet_ratio",))

    # ---- the tuplet the readers did NOT see (tile 6: no marker on the record)
    def test_an_UNMARKED_triplet_is_never_inferred_RED(self):
        """Sean 2026-10-13: a tuplet exists only where its 3 / bracket is seen.
        Half + four bare stems (Dvorak 8 tile 6's shape): the plain sum forces
        four eighths, which the no-eighth rule refuses (no stroke read), and no
        3:2 reading is assumed to supply quarters -- nothing is settled."""
        log, out = _solve(_half_and_four_bares())
        self.assertEqual(out.proposals, [])
        self.assertEqual(out.shortened_refused, 4)

    def test_a_marker_with_a_DECIDED_ratio_does_not_decline_the_bar(self):
        """A SEEN tuplet whose ratio was decided has its members' lengths
        already scaled, so the sum is the bar's."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        b.log.observe(_sub(0, 90), Q.TUPLET_MARKER, "3", reader=READERS.DETECTOR,
                      frame="cell:0", score=0.9)
        b.log.record(Verdict(
            id=b._id(), subject=_cell(0, 0), quantity=Q.TUPLET_RATIO,
            outcome=Outcome.DECIDED, value={"actual": 3, "normal": 2},
            decider="adjudicate_tuplet", reason="digit"))
        log, out = _solve(b)
        self.assertIsNone(out.decline)
        self.assertEqual(len(out.proposals), 1)

    def test_CONTROL_a_bar_with_fewer_than_three_unknowns_in_a_row_still_settles(
            self):
        """Two quarters and two bare stems in 3/4 (the 2.81 suite's own bar):
        no three consecutive unknowns, so no 3:2 group to test. Without this
        control the guard passes by declining every bar."""
        b = _Bar(3, 4)
        b.decided(1.0)
        b.decided(1.0)
        b.bare()
        b.bare()
        log, out = _solve(b)
        self.assertEqual(out.landings, 1)   # reached the arithmetic: no guard fired

    def test_CONTROL_three_decided_quarters_and_one_bare_still_settle(self):
        """3 decided quarters... + 1 bare: no 3:2 window can land it differently."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        log, out = _solve(b)
        self.assertEqual(out.proposals[0].value["beats"], 1.0)


class TestAnEighthNeedsItsOwnEvidence(unittest.TestCase):
    """Sean 2026-10-12: the sum may confirm a value the ink supports, never
    supply one."""

    def _bar_7_8(self, levels_possible):
        b = _Bar(7, 8)
        for _ in range(3):
            b.decided(1.0)
        b.bare()
        b.members[-1].detail["levels_possible"] = levels_possible
        return _solve(b)

    def test_a_bare_stem_forced_to_an_eighth_is_refused(self):
        log, out = self._bar_7_8(0)
        self.assertEqual(out.proposals, [])
        self.assertEqual(out.shortened_refused, 1)

    def test_CONTROL_the_same_bar_with_a_stroke_read_on_the_stem_settles_eighth(
            self):
        log, out = self._bar_7_8(1)
        self.assertEqual(len(out.proposals), 1)
        self.assertEqual(out.proposals[0].value["beats"], 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# (a) tile 10: columns the grouping left apart
# ─────────────────────────────────────────────────────────────────────────────


def _two_columns(offset):
    """1/4: two bare stems, the second `offset` px right of the first (40 px
    wide heads), one eighth each. (Three or more events would also let a 3:2
    group land the bar -- the other guard -- so two keeps this one alone.)"""
    b = _Bar(1, 4)
    for k in range(2):
        g = b.bare()
        b.log.observe(_sub(0, g), Q.GLYPH_BOX,
                      ("noteheadBlack", 100 + offset * k, 40 + 80 * k, 40, 30),
                      reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return b


class TestTwoHeadsInOneColumnAreNotSuccessiveInTime(unittest.TestCase):

    def test_two_heads_in_one_column_grouped_as_two_events_decline_RED(self):
        log, out = _solve(_two_columns(offset=8))
        self.assertEqual(out.decline, "simultaneous_heads_not_grouped")
        self.assertEqual(out.proposals, [])

    def test_CONTROL_the_same_bar_with_the_columns_a_head_apart_settles(self):
        """A head apart (offset >= the head's width) is a sequence: the same
        four events settle, so the guard is not a refusal of everything."""
        log, out = _solve(_two_columns(offset=60))
        self.assertIsNone(out.decline)
        self.assertEqual(out.landings, 1)   # no guard fired (eighths are refused by Sean's rule)


# ─────────────────────────────────────────────────────────────────────────────
# (b) a mark that is not a note has no duration
# ─────────────────────────────────────────────────────────────────────────────


def _hollow_head(log, *, with_page_box=False):
    """A head whose ink reads hollow on two rasters, bare stem, beamless cell:
    the 2.88 fixture. -> (glyph, stem_row)."""
    _staff_space(log)
    log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES, frame="cell:0",
                reason=R.ABSTAIN.NO_LINE_ACCEPTED)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    extra = {}
    if with_page_box:
        extra = {"bbox_page_px": [1400.0, 1800.0, 1426.0, 1847.0],
                 "x_center_page": 1413.0}
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9, **extra)
    s = _stem(log, x=135, y=38, h=60)
    _two_raster_ink(log, g)
    _unread_tip(log, s.id, "crosses_both_sides")
    return g, s


def _refuse(log, g, reason):
    log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
        outcome=Outcome.DECIDED, value=True,
        decider="adjudicate_notehead_is_not_a_notehead", reason=reason))


def _duration(log, g):
    # every decision but the refusal, which the test files itself
    adjudicate.run(log, order=[q for q in adjudicate.ORDER
                               if q != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD])
    return log.verdict(Q.DURATION, g)


class TestAMarkThatIsNotANoteHasNoDuration(unittest.TestCase):

    def test_CONTROL_an_unrefused_hollow_head_is_still_a_half(self):
        log = Log()
        g, _ = _hollow_head(log)
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.value["beats"], 2.0)

    def test_a_tremolo_slash_refused_as_a_notehead_is_not_a_half_RED(self):
        """Tile 17 (Schumann 2, Peters p4): base said a quarter, main a half."""
        log = Log()
        g, _ = _hollow_head(log)
        _refuse(log, g, "tremolo_slash_crosses_stem")
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_a_note_mark")

    def test_a_narrow_box_in_a_meter_signs_column_is_not_a_half_RED(self):
        """Tile 11 (Dvorak 8, p4): a C read as a head, 0.79 spaces wide, 15 px
        from a `timeSigCommon` on another staff of the system."""
        log = Log()
        g, _ = _hollow_head(log, with_page_box=True)
        _refuse(log, g, "too_narrow")
        sig = R.glyph(0, 0, 3, 1, 0)
        log.observe(sig, Q.GLYPH_BOX, ("timeSigCommon", 10, 10, 30, 30),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    bbox_page_px=[1380.0, 4000.0, 1415.0, 4040.0],
                    x_center_page=1398.0)
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_a_note_mark")
        self.assertEqual(v.detail["why"], "meter_sign_column")

    def test_CONTROL_a_narrow_box_with_no_meter_sign_in_its_column_is_not_abstained(
            self):
        """The same refusal, the sign 400 px away: the box is not the meter
        sign, so the duration rule is not told it is not a note."""
        log = Log()
        g, _ = _hollow_head(log, with_page_box=True)
        _refuse(log, g, "too_narrow")
        sig = R.glyph(0, 0, 3, 1, 0)
        log.observe(sig, Q.GLYPH_BOX, ("timeSigCommon", 10, 10, 30, 30),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    bbox_page_px=[1780.0, 4000.0, 1815.0, 4040.0],
                    x_center_page=1798.0)
        v = _duration(log, g)
        self.assertNotEqual(v.reason, "not_a_note_mark")

    def test_CONTROL_a_meter_sign_on_the_SAME_staff_does_not_count(self):
        log = Log()
        g, _ = _hollow_head(log, with_page_box=True)
        _refuse(log, g, "too_narrow")
        sig = R.glyph(0, 0, 0, 0, 7)           # same staff as the head
        log.observe(sig, Q.GLYPH_BOX, ("timeSigCommon", 10, 10, 30, 30),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    bbox_page_px=[1380.0, 4000.0, 1415.0, 4040.0],
                    x_center_page=1398.0)
        v = _duration(log, g)
        self.assertNotEqual(v.reason, "not_a_note_mark")


if __name__ == "__main__":
    unittest.main()
