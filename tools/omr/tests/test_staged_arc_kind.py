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
from tools.omr.staged.record import Log, Q, READERS


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
