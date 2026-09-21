"""`Q.KEYSIG_MARKER` — declared in `wants` AND `composed_from`, read by
nothing, and `no_evidence` was wrong on roughly half the staves it named.

⚠️ THE FAULT. `adjudicate_key_signature` abstains `no_evidence` when the CV
header reader produced no run. Measured on the two shared staged records,
**7 of 17** (Litolff) and **9 of 20** (Breitkopf) of those staves carry
DETECTED key accidentals. The detector saw ink; the fitter could not use it.
Reporting that as *no evidence* is the ABSENT/DECLINED collapse this record
exists to prevent, and it sends the next person to the wrong module — *nothing
was printed* wants a reader, *we could not fit what was printed* wants a
fitter.

⚠️⚠️ THE STATED REASON FOR LEAVING THE QUANTITY UNREAD WAS FALSE, which is why
it survived two gap lists. Both excused it as *"the decision reads
`keysig_clef_fit`, which the markers already feed in GATHER"*. They do not:
`Q.KEYSIG_CLEF_FIT` comes from `locate_key_signature` on the header CROP, and
the only place detections enter that call is `_occupied_boxes` — which filters
to NOTEHEADS. A gap list holds reasons a gap EXISTS; this one held a reason
that was not true.

⚠️ AND THE REPAIR IS A REASON, NEVER A VALUE. Counting key markers is a rule
this project has already built and condemned — seven spurious key flips on the
legacy path — and the staged record agrees from its own side: the marker count
equals the settled `|fifths|` on only 39% and 51% of decided staves.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

SUB = R.staff(0, 0, 0)


def _with_clef(log, clef="treble", sub=SUB):
    log.observe(sub, Q.CLEF_GLYPH, {"treble": "clefG", "bass": "clefF"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)


def _markers(log, *classes, sub=SUB):
    for i, c in enumerate(classes):
        log.observe(sub, Q.KEYSIG_MARKER, c, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.4, x=float(i), y_center=0.0)


def _decide(log):
    adjudicate.run(log)
    return log.verdict(Q.KEY_SIGNATURE, SUB)


class TestTheSplit(unittest.TestCase):

    def test_ink_with_no_run_is_NOT_called_no_evidence(self):
        log = Log()
        _with_clef(log)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "markers_without_a_run")
        self.assertEqual(v.detail["keysig_marker_ink"], 3)

    def test_no_ink_and_no_run_really_is_no_evidence(self):
        """The positive control for the test above: without it, a rule that
        renamed EVERY abstention would pass."""
        log = Log()
        _with_clef(log)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")
        self.assertEqual(v.detail["keysig_marker_ink"], 0)

    def test_the_marker_CLASSES_are_recorded(self):
        log = Log()
        _with_clef(log)
        _markers(log, "keyFlat", "keySharp")
        v = _decide(log)
        self.assertEqual(v.detail["keysig_marker_classes"],
                         ["keyFlat", "keySharp"])


class TestItIsNeverAVALUE(unittest.TestCase):
    """⚠️⚠️ THE LOAD-BEARING TESTS. The legacy path's count-the-markers
    fallback cost seven spurious key flips; nothing here may re-introduce it."""

    def test_markers_alone_NEVER_decide_a_key(self):
        log = Log()
        _with_clef(log)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")   # would "spell" -3
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertIsNone(v.value)

    def test_markers_do_not_overturn_a_fitted_reading(self):
        """Three markers beside a one-flat fit must leave the fit alone."""
        log = Log()
        _with_clef(log)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        _markers(log, "keyFlat", "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted")

    def test_markers_do_not_overturn_a_TEMPLATE_reading(self):
        log = Log()
        _with_clef(log)
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, accidental="b", fifths=-3)
        _markers(log, "keyFlat")
        v = _decide(log)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "fitted_by_template")

    def test_the_detail_says_out_loud_that_the_count_is_not_a_reading(self):
        """⚠️ A consumer that meets `keysig_marker_ink: 3` and reaches for it
        as three flats is the exact rule this project measured at seven
        spurious flips. The row says so in its own key name."""
        log = Log()
        _with_clef(log)
        _markers(log, "keyFlat", "keyFlat")
        v = _decide(log)
        self.assertTrue(v.detail["keysig_marker_count_is_not_a_reading"])


class TestTheDeclarations(unittest.TestCase):

    def test_the_reason_is_declared(self):
        """⚠️ A reason word with no branch is one documented anti-pattern here;
        a branch returning an UNDECLARED reason is its mirror."""
        from tools.omr.staged.adjudicate import REGISTRY, _ensure_decisions
        _ensure_decisions()
        self.assertIn("markers_without_a_run",
                      REGISTRY[Q.KEY_SIGNATURE].reasons)

    def test_the_quantity_is_actually_read_now(self):
        from tools.omr.staged.adjudicate import REGISTRY, _ensure_decisions
        import inspect
        from tools.omr.staged.adjudicators import header
        _ensure_decisions()
        self.assertIn(Q.KEYSIG_MARKER, REGISTRY[Q.KEY_SIGNATURE].wants)
        src = (inspect.getsource(header.adjudicate_key_signature)
               + inspect.getsource(header._marker_ink))
        self.assertIn("Q.KEYSIG_MARKER", src)


class TestTheStatedReasonWasFalse(unittest.TestCase):
    """⚠️⚠️ The claim both gap lists carried, checked rather than inherited:
    *"the markers already feed `keysig_clef_fit` in GATHER"*. They do not.

    This is asserted at SOURCE level because the consequence is invisible in
    behaviour — a decision reading a quantity that was never going to reach it
    produces the same answers as one that does not read it at all."""

    def test_the_marker_gatherer_RETURNS_NOTHING_to_feed_a_fit_with(self):
        """`_gather_keysig_markers` only LOGS. It hands its caller no value at
        all, so there is no route by which a marker could reach
        `locate_key_signature` — which is the call `Q.KEYSIG_CLEF_FIT` is
        filed from."""
        import inspect
        from tools.omr.staged import gather as g
        src = inspect.getsource(g._gather_keysig_markers)
        self.assertNotIn("return ", src.replace("return\n", ""),
                         "it returns a value; the excuse might have been true")
        fit_src = inspect.getsource(g.gather_key_signature)
        self.assertIn("locate_key_signature(crop", fit_src)

    def test_the_only_detections_reaching_the_fit_are_NOTEHEADS(self):
        import inspect
        from tools.omr.staged import gather as g
        src = inspect.getsource(g._occupied_boxes)
        self.assertIn("_NOTEHEAD_PREFIX", src)
        for cls in ("keySharp", "keyFlat", "keyNatural"):
            self.assertNotIn(cls, src)


if __name__ == "__main__":
    unittest.main()
