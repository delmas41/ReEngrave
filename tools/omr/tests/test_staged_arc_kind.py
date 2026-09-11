"""`arc_kind`: the reading decides, the grammar records.

⚠️ THE POINT OF THESE TESTS IS THE REFUSAL AS MUCH AS THE DECISION.
`OMR_ARC_RECLASS` measured the position-grammar veto at +130 scan edits, ALL
in the tie->slur half, and is default-off. This adjudicator must record the
grammar and never act on it — so the tests that matter most are the ones
asserting a DISAGREEING grammar changes nothing.
"""

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _log_with(arc_class, heads, *, arc_x=(100.0, 300.0), arc_y=(40.0, 60.0)):
    """One cell: an arc plus `heads` = [(x_center, rounded_step)]."""
    log = Log()
    cell = R.cell(0, 0, 0, 0)
    arc = R.glyph(0, 0, 0, 0, 0)
    log.observe(arc, Q.ARC_BOX, arc_class, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=arc_x[0], x1=arc_x[1], y0=arc_y[0], y1=arc_y[1],
                x_center=(arc_x[0] + arc_x[1]) / 2, y_center=50.0)
    for i, (xc, step) in enumerate(heads, start=1):
        g = R.glyph(0, 0, 0, 0, i)
        log.observe(g, Q.GLYPH_BOX,
                    ("noteheadBlackOnLine", xc - 10.0, 80.0, 20.0, 20.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(step),
                    reader=READERS.GEOMETRY, frame="cell:0",
                    residual=0.0, rounded=int(step))
    return log, cell


def _decide(log, glyph=None):
    """Run the REAL harness, then read the arc's verdict."""
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARC_KIND, glyph or R.glyph(0, 0, 0, 0, 0))


class TestItIsNoLongerAStub(unittest.TestCase):

    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ARC_KIND].stub,
                         "arc_kind was filled on 2026-09-09")


class TestTheReadingDecides(unittest.TestCase):
    """The DETECTOR'S class is the answer. The grammar never overturns it."""

    def _kind(self, arc_class, heads):
        log, _cell = _log_with(arc_class, heads)
        v = _decide(log)
        self.assertIsNotNone(v, "arc_kind produced no verdict at all")
        # ⚠️ ASSERT THE OUTCOME EXPLICITLY, NOT ONLY THE VALUE. Added because
        # `health --check` went RED on `arc_kind: no test asserts it DECIDES`
        # the moment this decision landed on main.
        #
        # ⚠️⚠️ AND MY FIRST RATIONALE FOR THIS LINE WAS FALSE, kept here
        # because the correction is the point. I wrote that `Ruling.narrow`
        # also carries a value, so a decision that started narrowing would
        # have passed the value-only assertions. **It does not**:
        # `Ruling.narrow` sets `value=None` unconditionally
        # (`adjudicate.py`), so on this API a non-DECIDED verdict NEVER
        # carries a value — and a mutation making this decision narrow was
        # caught by the OLD assertion, not the new one. I asserted a mechanism
        # instead of checking it, in a test comment, on the day this repo
        # catalogued eight instances of exactly that.
        #
        # So what this line actually buys is LEGIBILITY, not power: the old
        # test did establish deciding, but only through an API invariant the
        # reader has to already know. Stating it makes the claim machine-
        # readable — which is what the textual classifier needs — and removes
        # the dependence on that invariant, so this test survives a `narrow`
        # that ever starts carrying a value.
        self.assertEqual(v.outcome, Outcome.DECIDED)
        return v

    def test_a_tie_class_decides_tie(self):
        v = self._kind("tie", [(150.0, 3), (250.0, 3)])
        self.assertEqual(v.value, "tie")
        self.assertEqual(v.reason, "tie")

    def test_a_slur_class_decides_slur(self):
        v = self._kind("slur", [(150.0, 3), (250.0, 5)])
        self.assertEqual(v.value, "slur")

    def test_the_grammar_AGREEING_is_recorded(self):
        v = self._kind("tie", [(150.0, 3), (250.0, 3)])
        g = v.detail["grammar"]
        self.assertEqual(g["says"], "tie")
        self.assertTrue(g["agrees_with_reading"])

    def test_a_DISAGREEING_grammar_changes_NOTHING(self):
        """⚠️⚠️ THE LOAD-BEARING TEST. A tie whose flanked heads sit on
        DIFFERENT steps is what `OMR_ARC_RECLASS`'s tie->slur half would
        overturn — measured at +130 scan edits, all of them in that half. It
        must be recorded and not acted on."""
        v = self._kind("tie", [(150.0, 3), (250.0, 7)])
        self.assertEqual(v.value, "tie", "the grammar must NOT overturn")
        g = v.detail["grammar"]
        self.assertEqual(g["says"], "slur")
        self.assertFalse(g["agrees_with_reading"])

    def test_the_other_direction_is_also_only_RECORDED(self):
        """slur->tie is the half that measured edit-free, and it is still not
        applied here: enabling half a refused flag on the path with the least
        measurement behind it is not a default anyone chose."""
        v = self._kind("slur", [(150.0, 4), (250.0, 4)])
        self.assertEqual(v.value, "slur")
        self.assertEqual(v.detail["grammar"]["says"], "tie")
        self.assertFalse(v.detail["grammar"]["agrees_with_reading"])


class TestTheGrammarAbstainsRatherThanGuessing(unittest.TestCase):

    def test_one_flanked_head_gives_NO_grammar(self):
        log, _ = _log_with("slur", [(150.0, 3)])
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "slur", "the reading still decides")
        self.assertIsNone(v.detail["grammar"]["says"])
        self.assertIn("fewer than two", v.detail["grammar"]["why"])

    def test_heads_OUTSIDE_the_span_are_not_flanked(self):
        log, _ = _log_with("tie", [(900.0, 3), (950.0, 9)])
        v = _decide(log)
        self.assertEqual(v.detail["grammar"]["flanked_heads"], 0)

    def test_the_span_is_PADDED_because_an_arc_is_narrower_than_its_run(self):
        """⚠️ An arc is drawn BETWEEN its outer noteheads, so its ink stops
        inside both outer centres. Unpadded, the Contrabass read `n1 -> n4` in
        every bar whose truth is `n0 -> n5`."""
        # heads sit just OUTSIDE the raw span, inside the pad (arc height 20)
        log, _ = _log_with("tie", [(95.0, 3), (305.0, 3)],
                           arc_x=(100.0, 300.0), arc_y=(40.0, 60.0))
        v = _decide(log)
        self.assertEqual(v.detail["grammar"]["flanked_heads"], 2)


class TestItComparesSTEPSNotPitches(unittest.TestCase):
    """⚠️ The far head of a cross-barline tie does not restate its accidental
    and the resolver spells it plain, so a spelled-pitch key breaks
    truth-matched ties: +21 engraved edits, every loss a same-step
    `F#4 -> F4` pair. The input is the clef-free measured STEP."""

    def test_the_input_quantity_is_the_staff_position_not_the_pitch(self):
        spec = adjudicate.REGISTRY[Q.ARC_KIND]
        self.assertIn(Q.NOTEHEAD_STAFF_POSITION, spec.wants)
        self.assertNotIn(Q.PITCH, spec.wants)


class TestAHeadIsReachableAtItsStem(unittest.TestCase):
    """⚠️⚠️ THE EXPORTER AND THIS DECISION ASK THE SAME QUESTION.

    *Which heads does this arc bind?* `_noteheads_under` was repaired on
    2026-09-11 -- an arc over stemmed notes is drawn from STEM TOP to STEM
    TOP, and a stem stands at the SIDE of its notehead, so the ink stops about
    half a head width inside both outer CENTRES (median 0.52 notehead widths,
    measured). Until that repair reached here too, the two readers of one
    question disagreed BY CONSTRUCTION -- the *two rules nothing forces to
    agree* shape this project has already paid for twice.

    Measured on Litolff Beethoven 5 p1-4: the grammar's availability goes
    345 -> 371 of 779 arcs and NO verdict value moves.
    """

    def _log(self, arc_class, heads, stems, *, arc_x=(100.0, 300.0)):
        log, cell = _log_with(arc_class, heads, arc_x=arc_x)
        for x, y, w, h in stems:
            log.observe(cell, Q.STEM, [x, y, w, h], reader=READERS.CV_LINES,
                        frame="cell:0")
        return log

    def test_a_head_OUTSIDE_the_span_is_reached_at_its_stem(self):
        """The head centre sits past the padded span; its stem does not.

        ⚠️ THE FIXTURE IS THE POINT AND ITS NUMBERS ARE THE REAL GEOMETRY.
        Arc 100..350, padded by its own height (20) to 80..370. The head's
        centre is 375 -- OUTSIDE -- and its box runs 365..385, so the stem
        standing at the head's left side (360..370, centre 365) is INSIDE.
        That half-a-head-width offset is the whole mechanism: measured on this
        document at a median 0.52 notehead widths.
        """
        log = self._log("slur", [(150.0, 3), (375.0, 5)],
                        [(360.0, 60.0, 10.0, 60.0)], arc_x=(100.0, 350.0))
        v = _decide(log)
        self.assertEqual(v.detail["grammar"]["flanked_heads"], 2)
        self.assertEqual(v.detail["grammar"]["reached_only_at_a_stem"], 1)
        self.assertEqual(v.detail["grammar"]["says"], "slur")

    def test_WITHOUT_the_stem_that_head_is_not_reached(self):
        """The positive control's other half: same fixture, no stem row."""
        log = self._log("slur", [(150.0, 3), (375.0, 5)], [],
                        arc_x=(100.0, 350.0))
        v = _decide(log)
        self.assertEqual(v.detail["grammar"]["flanked_heads"], 1)
        self.assertIsNone(v.detail["grammar"]["says"])

    def test_a_stem_that_does_not_MEET_the_head_reaches_nothing(self):
        """⚠️ The attachment rule is `_stem_joined`'s -- BOX OVERLAP, not
        proximity. A stem elsewhere in the bar is not this head's stem."""
        log = self._log("slur", [(150.0, 3), (375.0, 5)],
                        [(200.0, 400.0, 10.0, 60.0)],
                        arc_x=(100.0, 350.0))
        v = _decide(log)
        self.assertEqual(v.detail["grammar"]["flanked_heads"], 1)

    def test_it_is_ADDITIVE_and_cannot_REMOVE_a_flanked_head(self):
        """A cell whose stems the CV never read behaves exactly as before."""
        heads = [(150.0, 3), (250.0, 3)]
        bare = _decide(_log_with("tie", heads)[0])
        with_stems = _decide(self._log("tie", heads,
                                       [(145.0, 60.0, 10.0, 60.0)]))
        self.assertEqual(bare.detail["grammar"]["says"],
                         with_stems.detail["grammar"]["says"])
        self.assertEqual(bare.value, with_stems.value)

    def test_the_span_endpoints_stay_the_head_CENTRES(self):
        """⚠️ A stem says a head is REACHABLE; it never widens what the arc is
        taken to cover. The recorded steps are the heads', not the stems'."""
        log = self._log("tie", [(150.0, 3), (375.0, 3)],
                        [(360.0, 60.0, 10.0, 60.0)], arc_x=(100.0, 350.0))
        v = _decide(log)
        g = v.detail["grammar"]
        self.assertEqual((g["first_step"], g["last_step"]), (3, 3))

    def test_Q_STEM_is_DECLARED_or_the_read_would_be_refused(self):
        """`Evidence` refuses a quantity the decision did not declare, which
        is what makes `missing` and `declined` mean something."""
        spec = adjudicate.REGISTRY[Q.ARC_KIND]
        self.assertIn(Q.STEM, spec.wants)
        self.assertIn(Q.STEM, spec.composed_from)
