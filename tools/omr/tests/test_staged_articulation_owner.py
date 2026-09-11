"""`articulation_owner`: a mark belongs to the notehead it is printed against.

⚠️ THE SIDE TEST IS WHERE THIS CAN GO SILENTLY WRONG, and it reads backwards:
a LARGER canonical y is LOWER on the page, so a mark printed ABOVE its notehead
has the SMALLER y. A test suite that only ever places marks above notes would
pass with the comparison inverted, so both sides are exercised and the inverted
comparison is a mutation arm.

⚠️ THE REFUSALS CARRY THEIR OWN POSITIVE CONTROL. Every test asserting that a
mark is NOT attached sets up a case that differs from an attaching one in ONE
fact, and asserts the attaching version too -- otherwise the whole class passes
the moment the decision starts abstaining on everything.
"""

from __future__ import annotations

import unittest

from tools.omr import transcribe as _legacy
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)


def _head(log, gi, x, y, *, w=20.0, h=20.0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _mark(log, gi, x, y, cls="articStaccatoAbove", *, w=6.0, h=6.0):
    g = R.glyph(0, 0, 0, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    log.observe(g, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=x + w / 2.0, y_center=y + h / 2.0, side=side)
    return g


def _decide(log, mark):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, mark)


class TestItIsNoLongerAStub(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ARTICULATION_OWNER].stub)

    def test_the_constant_is_imported_not_restated(self):
        """⚠️ AN AST CHECK, because a copied number does not fail a test.

        The 0.75 was swept over eight engraved works and sits on a plateau.
        A second copy of it here would drift silently from the legacy pass,
        which is the `LETTER_METERS` lesson.
        """
        import inspect
        from tools.omr.staged.adjudicators import ownership
        src = inspect.getsource(ownership.adjudicate_articulation_owner)
        self.assertIn("_ARTIC_MAX_DX_NOTEHEAD_WIDTHS", src)
        self.assertNotIn("0.75", src)


class TestTheMarkGoesToTheNoteheadUnderIt(unittest.TestCase):

    def test_a_staccato_above_takes_the_note_below_it(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0)            # above: smaller y
        head = _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["articulation"], "staccato")

    def test_a_staccato_BELOW_takes_the_note_above_it(self):
        """⚠️ THE OTHER SIDE. Without this, inverting the y comparison passes."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, cls="articStaccatoBelow")
        head = _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())

    def test_the_NEAREST_in_x_wins(self):
        log = Log()
        # ⚠️ CENTRES, not corners: the mark spans 100-106 so its centre is
        # 103, and a 20px head at x takes centre x+10. The first draft of this
        # test put the "far" head NEARER and read as a code failure.
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 82.0, 40.0)            # centre  92, dx 11
        near = _head(log, 2, 94.0, 40.0)     # centre 104, dx  1
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.value, near.to_key())

    def test_the_kind_travels_with_the_owner(self):
        """A tenuto must not reach the file as a staccato."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, cls="articTenutoBelow")
        _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.detail["articulation"], "tenuto")


class TestTheRefusals(unittest.TestCase):
    """⚠️ Each carries its POSITIVE CONTROL: the same page, one fact changed."""

    def test_a_mark_with_no_notehead_on_its_side_abstains(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0)           # says Above, but sits BELOW
        _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")

        log2 = Log()                          # positive control: move it above
        _mark(log2, 0, 100.0, 0.0)
        _head(log2, 1, 97.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).outcome,
                         "decided")

    def test_a_mark_too_far_in_x_abstains(self):
        """The limit is 0.75 NOTEHEAD WIDTHS -- here 15px of a 20px head."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 130.0, 40.0)           # centre 37px away, over the limit
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")
        self.assertIn("limit_canonical_px", v.detail)

        log2 = Log()                          # positive control: bring it in
        _mark(log2, 0, 100.0, 0.0)
        _head(log2, 1, 98.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).outcome,
                         "decided")

    def test_a_cell_with_no_notehead_at_all_abstains(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")

    def test_a_class_that_names_no_side_abstains_with_its_own_reason(self):
        """⚠️ ZERO REACH ON THE DOCUMENT THIS LANDED WITH, so it is tested here.

        `class_aliases.COARSER_THAN_CANONICAL` records `articulationStaccato`
        as a coarser spelling carrying no side. All 24 marks on Litolff
        `984073` p1-3 name one, so the page cannot exercise this branch.
        """
        log = Log()
        _mark(log, 0, 100.0, 0.0, cls="articulationStaccato")
        _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_side_declared")

        log2 = Log()                          # positive control: name the side
        _mark(log2, 0, 100.0, 0.0, cls="articStaccatoAbove")
        _head(log2, 1, 97.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).reason,
                         "nearest_on_declared_side")

    def test_a_mark_outside_the_five_exported_kinds_abstains(self):
        """`_ARTICULATION_KINDS` is the legacy list and is not widened here."""
        log = Log()
        _mark(log, 0, 100.0, 0.0, cls="articSoftAccentAbove")
        _head(log, 1, 97.0, 40.0)
        self.assertEqual(_decide(log, R.glyph(0, 0, 0, 0, 0)).reason,
                         "no_side_declared")


class TestTheMedianWidthSetsTheLimit(unittest.TestCase):
    def test_one_giant_detection_does_not_widen_the_cell(self):
        """⚠️ MEDIAN, not max -- one merged blob must not set the limit for
        every mark in the bar, which is the same reason the legacy pass takes
        a median."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 130.0, 40.0)                  # too far under a 20px head
        _head(log, 2, 400.0, 40.0, w=400.0)         # a blob, far away
        _head(log, 3, 500.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained",
                         "the blob widened the limit and let a far head win")


if __name__ == "__main__":
    unittest.main()
