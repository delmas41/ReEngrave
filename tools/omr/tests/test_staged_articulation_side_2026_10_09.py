"""ROADMAP 2.12f -- an articulation's SIDE is measured against the notehead it
is printed against, and where the class name and the measurement disagree the
disagreement is NAMED, never resolved by either party.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md Sec.2
rule 3): an articulation's side is where its ink sits relative to the notehead
it belongs to. It would be falsified by a Sean-adjudicated print crop where the
class names a side, the mark is measured on the other, and the mark belongs to
the head IN THE SAME CELL. The sample cut for this item (15 Brahms marks the
class and the cell disagree on) read the other way in ~11: the mark stands
between two staves, the class is right, and the head it belongs to is in the
NEIGHBOUR staff -- so the in-cell nearest head is the wrong witness, and the
decision records the contradiction instead of overturning the class
(`benchmarks/omr-shape-role-2026-09/FINDINGS.md` Sec.2.12f).

COHERENCE, NOT ACCURACY: positions are chosen to land cleanly on one side of a
cut, in the cell's own canonical frame (a mark and the head beside it share
that frame by construction, so a difference of y is a LOCAL measurement).

THE REFUSALS CARRY THEIR OWN POSITIVE CONTROL: each refusal sits beside the
same page with ONE fact changed that decides, so none passes by refusing
everything.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

# one head: x 97..117, y 40..60 (a 20 x 20 box, centre y 50).
HEAD_Y, HEAD_H = 40.0, 20.0


def _head(log, gi, x=97.0, y=HEAD_Y, *, w=20.0, h=HEAD_H, staff=0):
    g = R.glyph(0, 0, staff, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _mark(log, gi, x, y, cls, *, w=6.0, h=6.0):
    g = R.glyph(0, 0, 0, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    log.observe(g, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=x + w / 2.0, y_center=y + h / 2.0, side=side)
    return g


def _decide(log, gi=0):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, R.glyph(0, 0, 0, 0, gi))


class TestAContradictedClassIsNamedNotLumpedWithNoNotehead(unittest.TestCase):
    """Today a mark whose class says ABOVE and which stands BELOW every head in
    reach abstains `no_notehead` -- the same word as a cell with no head at
    all, so the population the class and the geometry disagree on is
    invisible. Both are abstentions and neither changes; only the NAME and the
    recorded measurement do."""

    def test_RED_class_above_but_measured_below_the_only_head(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentAbove")   # y 80..86: under the head
        _head(log, 1)
        v = _decide(log)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "suffix_contradicts_geometry")
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["measured_side"], "below")
        self.assertIn("gap_head_heights", v.detail)

    def test_POSITIVE_CONTROL_the_same_mark_named_below_is_decided(self):
        """One fact changed -- the class -- and the decision decides, so the
        refusal above is not refusing everything."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentBelow")
        head = _head(log, 1)
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["measured_side"], "below")

    def test_a_head_far_out_of_reach_on_the_other_side_is_NOT_a_contradiction(self):
        """A head seven head-heights away says nothing about the mark's side:
        the agreement between class and geometry falls to chance there (the
        measured curve, FINDINGS Sec.2.12f). Naming it a contradiction would
        be the same lumping in the other direction."""
        log = Log()
        _mark(log, 0, 100.0, 200.0, "articAccentAbove")  # 140px under the head
        _head(log, 1)
        v = _decide(log)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")

    def test_a_cell_with_no_head_in_the_x_window_stays_no_notehead(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentAbove")
        _head(log, 1, x=400.0)                           # same cell, far in x
        v = _decide(log)
        self.assertEqual(v.reason, "no_notehead")

    def test_the_contradicting_head_must_be_this_staffs_own(self):
        """ROADMAP 2.27 composes: a head `glyph_owner` DECIDED belongs to the
        neighbour is not evidence about this staff's mark, on either side."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentAbove")
        ghost = _head(log, 1)
        home, neighbour = R.staff(0, 0, 0), R.staff(0, 0, 1)
        log.observe(ghost, Q.GLYPH_BAND_DISTANCE, 4.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=home.to_key(), own=True,
                    position_in_candidate=2.0)
        log.observe(ghost, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=neighbour.to_key(), own=False,
                    position_in_candidate=2.0)
        v = _decide(log)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "owned_by_another_staff")


class TestLevelWithTheHeadAbstains(unittest.TestCase):
    """A mark never overlaps the notehead it is printed against. One whose
    centre stands inside the head's own vertical extent is neither above nor
    below it, and the old centre-against-centre test called it ABOVE or BELOW
    by a hair."""

    def test_RED_a_mark_centred_inside_the_heads_extent(self):
        log = Log()
        _mark(log, 0, 100.0, 44.0, "articAccentAbove")   # y 44..50, centre 47
        _head(log, 1)                                     # head centre 50
        v = _decide(log)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "level_with_head")

    def test_POSITIVE_CONTROL_clear_of_the_head_is_decided(self):
        log = Log()
        _mark(log, 0, 100.0, 20.0, "articAccentAbove")   # y 20..26, clear above
        head = _head(log, 1)
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["measured_side"], "above")

    def test_level_is_symmetric_below_the_centre(self):
        log = Log()
        _mark(log, 0, 100.0, 51.0, "articAccentBelow")   # y 51..57, centre 54
        _head(log, 1)
        self.assertEqual(_decide(log).reason, "level_with_head")


class TestADecidedOwnerCarriesTheMeasurement(unittest.TestCase):
    def test_RED_the_decided_verdict_records_what_was_measured(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articTenutoAbove")    # y 0..6 -> gap 34px
        head = _head(log, 1)
        v = _decide(log)
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["measured_side"], "above")
        self.assertAlmostEqual(v.detail["gap_head_heights"], 34.0 / HEAD_H,
                               places=3)
        self.assertFalse(v.detail["other_side_head_in_reach"])

    def test_a_mark_between_two_heads_records_that_the_class_chose(self):
        """The mark stands between the upper head and the lower one. The
        class says ABOVE, so the owner is the lower head -- the old rule's
        pick, unchanged -- but the geometry alone could not have chosen, and
        that is now on the verdict (`other_side_head_in_reach`) for the INFER
        rule that would own such a tie-break."""
        log = Log()
        _mark(log, 0, 100.0, 30.0, "articAccentAbove")   # y 30..36
        _head(log, 1, y=0.0)                              # upper, y 0..20
        lower = _head(log, 2, y=60.0)                     # lower, y 60..80
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, lower.to_key())
        self.assertTrue(v.detail["other_side_head_in_reach"])

    def test_POSITIVE_CONTROL_one_head_only_records_False(self):
        log = Log()
        _mark(log, 0, 100.0, 30.0, "articAccentAbove")
        _head(log, 1, y=60.0)
        v = _decide(log)
        self.assertFalse(v.detail["other_side_head_in_reach"])


class TestTheNearerHeadOfAColumnIsRecordedNotActedOn(unittest.TestCase):
    """The pick is NEAREST IN X ONLY (the legacy rule's), so within a column of
    heads sharing an x it is whichever the detector listed first. 119 of 802
    decided Brahms owners are 2.5-5 head heights from their mark while a head
    on the same declared side stands 0.2-0.6 from it. This lane RECORDS that
    and does not change the pick -- 15 % of the decided population, and no
    print has adjudicated it -- so the test PINS the current pick (a deliberate
    follow-up flips it on purpose, not by accident) and asserts the record."""

    def _column(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articTenutoAbove")        # y 0..6
        near = _head(log, 1, x=97.0, y=20.0)                  # gap 14  (0.7 heights)
        far = _head(log, 2, x=95.0, y=100.0)                  # gap 94 (4.7 heights), dx 2 < 4
        return log, near, far

    def test_RED_the_x_nearest_head_still_wins_and_the_nearer_is_named(self):
        log, near, far = self._column()
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, far.to_key(), "the pick is not changed here")
        self.assertEqual(v.detail["nearest_declared_side_head"], near.to_key())
        self.assertAlmostEqual(
            v.detail["nearest_declared_side_gap_head_heights"], 14.0 / HEAD_H,
            places=3)

    def test_POSITIVE_CONTROL_when_the_pick_IS_the_nearest_they_agree(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articTenutoAbove")
        only = _head(log, 1, x=97.0, y=20.0)
        v = _decide(log)
        self.assertEqual(v.value, only.to_key())
        self.assertEqual(v.detail["nearest_declared_side_head"], only.to_key())
        self.assertAlmostEqual(v.detail["gap_head_heights"],
                               v.detail["nearest_declared_side_gap_head_heights"])


class TestTheOwnerThatDecidedBeforeStillDecidesTheSameHead(unittest.TestCase):
    """The change is bookkeeping and two named refusals: it must not move a
    mark the old rule placed, on either side."""

    def test_above_and_below_both_keep_their_head(self):
        for cls, y in (("articAccentAbove", 0.0), ("articAccentBelow", 80.0)):
            log = Log()
            _mark(log, 0, 100.0, y, cls)
            head = _head(log, 1)
            v = _decide(log)
            self.assertEqual(v.outcome, "decided", cls)
            self.assertEqual(v.value, head.to_key(), cls)
            self.assertEqual(v.reason, "nearest_on_declared_side", cls)


# ─────────────────────────────────────────────────────────────────────────────
# The fermata half: RECORD-ONLY. Measured and written down, read by nothing.
# ─────────────────────────────────────────────────────────────────────────────

def _carrier(log, gi, x, *, y=40.0, w=20.0, category="notehead"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, 20.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category=category)
    return g


def _fermata(log, gi, x, y, cls, *, w=14.0, h=10.0):
    g = R.glyph(0, 0, 0, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    log.observe(g, Q.FERMATA_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=x + w / 2.0, y_center=y + h / 2.0, side=side)
    return g


def _decide_fermata(log, gi=0):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.FERMATA_OWNER, R.glyph(0, 0, 0, 0, gi))


class TestFermataSideIsMeasuredAndRecordedOnly(unittest.TestCase):
    def test_RED_the_measured_side_rides_the_owner_verdict(self):
        log = Log()
        _fermata(log, 0, 100.0, 0.0, "fermataAbove")     # y 0..10, over the head
        carrier = _carrier(log, 1, 97.0)
        v = _decide_fermata(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, carrier.to_key())
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["measured_side"], "above")
        self.assertTrue(v.detail["side_agrees"])

    def test_a_disagreement_is_recorded_and_the_owner_is_UNCHANGED(self):
        """`fermataBelow` standing ABOVE its carrier: the side is NOT a
        constraint on a fermata (it hangs over whatever sounds under it), so
        the owner decides exactly as before and the contradiction is only
        written down. This is the guard against wiring the record into a
        consumer."""
        log = Log()
        _fermata(log, 0, 100.0, 0.0, "fermataBelow")
        carrier = _carrier(log, 1, 97.0)
        v = _decide_fermata(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, carrier.to_key())
        self.assertEqual(v.reason, "contains_the_mark")
        self.assertEqual(v.detail["measured_side"], "above")
        self.assertFalse(v.detail["side_agrees"])

    def test_POSITIVE_CONTROL_agreeing_and_disagreeing_decide_the_same_carrier(self):
        a, b = Log(), Log()
        _fermata(a, 0, 100.0, 0.0, "fermataAbove")
        _fermata(b, 0, 100.0, 0.0, "fermataBelow")
        ca = _carrier(a, 1, 97.0)
        cb = _carrier(b, 1, 97.0)
        self.assertEqual(_decide_fermata(a).value, ca.to_key())
        self.assertEqual(_decide_fermata(b).value, cb.to_key())

    def test_a_mark_level_with_its_carrier_records_level(self):
        log = Log()
        _fermata(log, 0, 100.0, 42.0, "fermataAbove")    # y 42..52, inside 40..60
        _carrier(log, 1, 97.0)
        v = _decide_fermata(log)
        self.assertEqual(v.outcome, "decided")           # the owner never reads it
        self.assertEqual(v.detail["measured_side"], "level")
        self.assertFalse(v.detail["side_agrees"])


if __name__ == "__main__":
    unittest.main()
