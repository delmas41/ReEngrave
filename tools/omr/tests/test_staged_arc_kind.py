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


# ─────────────────────────────────────────────────────────────────────────────
# Sean's S4 and S6 — RECORDED, never acted on (2026-09-15)
# ─────────────────────────────────────────────────────────────────────────────


def _log_with_stems(arc_class, heads, stems, *, arc_x=(100.0, 300.0),
                    arc_y=(40.0, 60.0), second_arc=None):
    """`_log_with`, plus CV stems on the cell and optionally a second arc.

    ⚠️ THE FIXTURE'S NUMBERS ARE THE REAL GEOMETRY and are worked here rather
    than round because a frame error looks exactly like a result. Heads sit at
    y 80..100, so a head centre is **90**. A stem drawn UP from a head spans
    20..82 in canonical (y-DOWN) coordinates, so its HEAD end is 82 and its
    FAR end is 20 — and `t`, the fraction along the stem, is
    `(arc_near_edge - 82) / (20 - 82)`.
    """
    log, cell = _log_with(arc_class, heads, arc_x=arc_x, arc_y=arc_y)
    for box in stems:
        log.observe(cell, Q.STEM, list(box), reader=READERS.CV_LINES,
                    frame="cell:0", x0=box[0], x1=box[0] + box[2],
                    y_center=box[1] + box[3] / 2.0)
    if second_arc is not None:
        cls, (bx0, bx1), (by0, by1) = second_arc
        log.observe(R.glyph(0, 0, 0, 0, 99), Q.ARC_BOX, cls,
                    reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                    x0=bx0, x1=bx1, y0=by0, y1=by1,
                    x_center=(bx0 + bx1) / 2, y_center=(by0 + by1) / 2)
    return log, cell


#: A stem drawn UP from the fixture's head: x 158..162 (overlapping the head's
#: 140..160), y 20..82 (meeting the head's 80..100).
_STEM_UP = (158.0, 20.0, 4.0, 62.0)
_HEADS = [(150.0, 3), (250.0, 3)]
#: The same stem under the SECOND head at x_center 250 (box 240..260).
_STEM_UP_2 = (258.0, 20.0, 4.0, 62.0)


class TestS4IsRecordedAndNeverActedOn(unittest.TestCase):
    """Sean, 2026-09-11: *"if it is connected to the stems edge away from the
    notehead then it is a slur."*

    ⚠️⚠️ IT READS GEOMETRY AND NEVER A RESOLVED PITCH, which is the whole
    reason it is admissible where `OMR_ARC_RECLASS`'s pitch half is refused
    (+149 scan edits, *a scan's resolved pitch at an arc's ends is downstream
    of exactly what scans get wrong*). `test_it_reads_no_pitch` pins that.
    """

    def _g(self, **kw):
        log, _ = _log_with_stems("tie", _HEADS, [_STEM_UP, _STEM_UP_2], **kw)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        return v

    def test_an_arc_at_the_HEAD_end_of_the_stem_reads_t_near_zero(self):
        """near edge 82 = the stem's head end ⇒ t = 0.0, to the unit."""
        v = self._g(arc_y=(62.0, 82.0))
        s4 = v.detail["grammar"]["s4_stem_position"]
        self.assertAlmostEqual(s4["t_median"], 0.0, places=3)
        self.assertTrue(s4["any_endpoint_on_a_stem"])

    def test_an_arc_at_the_FAR_edge_of_the_stem_reads_t_near_one(self):
        """near edge 20 = the stem's tip ⇒ t = 1.0. This is S4's own case."""
        v = self._g(arc_y=(0.0, 20.0))
        s4 = v.detail["grammar"]["s4_stem_position"]
        self.assertAlmostEqual(s4["t_median"], 1.0, places=3)

    def test_t_is_the_FRACTION_along_the_stem_and_not_a_pixel_count(self):
        """⚠️ NO CONSTANT BY CONSTRUCTION. near edge 51 sits halfway between
        82 and 20, so `t` is 0.5 whatever the stem's length in pixels."""
        v = self._g(arc_y=(31.0, 51.0))
        self.assertAlmostEqual(
            v.detail["grammar"]["s4_stem_position"]["t_median"], 0.5, places=2)

    def test_an_arc_on_the_OTHER_side_of_the_head_is_NOT_on_the_stem(self):
        """⚠️ THE TEST SEAN'S WORDS ACTUALLY NAME. A tie drawn under heads
        whose stems point UP touches no stem, and his rule is silent about it.
        Recording it as `same_side: false` is what keeps a later consumer from
        reading a meaningless `t` as evidence."""
        v = self._g(arc_y=(100.0, 120.0))
        s4 = v.detail["grammar"]["s4_stem_position"]
        self.assertFalse(any(e["same_side"] for e in s4["endpoints"]))
        self.assertFalse(s4["any_endpoint_on_a_stem"])
        self.assertFalse(s4["arc_above_heads"])

    def test_a_stem_that_does_not_MEET_the_head_records_nothing(self):
        """The attachment rule is `_boxes_overlap`, IMPORTED — a stem
        elsewhere in the bar is not this head's stem."""
        log, _ = _log_with_stems("tie", _HEADS, [(400.0, 20.0, 4.0, 62.0)])
        v = _decide(log)
        self.assertNotIn("s4_stem_position", v.detail["grammar"])

    def test_no_stems_at_all_records_nothing(self):
        log, _ = _log_with_stems("tie", _HEADS, [])
        v = _decide(log)
        self.assertNotIn("s4_stem_position", v.detail["grammar"])

    def test_it_changes_NO_verdict(self):
        """⚠️⚠️ THE LOAD-BEARING ONE. S4 at the far edge says SLUR; this arc
        reads `tie`. Recording must not overturn it — promoting the geometry
        to a gate would enable half a refused flag by the back door, on the
        path with the least measurement behind it."""
        bare = _decide(_log_with("tie", _HEADS, arc_y=(0.0, 20.0))[0])
        with_s4 = self._g(arc_y=(0.0, 20.0))
        self.assertEqual(with_s4.value, "tie")
        self.assertEqual(with_s4.value, bare.value)
        self.assertEqual(with_s4.reason, bare.reason)
        self.assertEqual(with_s4.detail["grammar"]["says"],
                         bare.detail["grammar"]["says"])
        self.assertAlmostEqual(
            with_s4.detail["grammar"]["s4_stem_position"]["t_median"], 1.0,
            places=3)

    def test_it_reads_no_pitch(self):
        """⚠️ THE ADMISSIBILITY CONDITION, asserted on the SOURCE. If this
        ever reads a resolved pitch it has become `OMR_ARC_RECLASS`'s refused
        half."""
        import inspect
        from tools.omr.staged.adjudicators import ownership
        body = inspect.getsource(ownership._s4_stem_view).split('"""')[-1]
        self.assertNotIn("pitch", body, "S4 must read no pitch")


class TestS6IsRecordedAndNeverActedOn(unittest.TestCase):
    """Sean, 2026-09-11: *"If there are 2 arcs on top of each other then the
    lower is a tie and the upper is a slur."*

    ⚠️ THE PAIR'S OWN GEOMETRY IS RECORDED AND NOTHING IS THRESHOLDED, because
    this document is recorded as full of DUPLICATES — 48 pairs in one cell at
    IoU >= 0.7 — and a stack and a duplicate must be separable downstream by
    measurement rather than assumed apart here.
    """

    def _pair(self, upper_cls="slur", lower_cls="tie"):
        # upper arc y 40..60, lower arc y 150..170 → a 90-unit gap.
        log, _ = _log_with_stems(upper_cls, _HEADS, [],
                                 arc_y=(40.0, 60.0),
                                 second_arc=(lower_cls, (110.0, 290.0),
                                             (150.0, 170.0)))
        return _decide(log)

    def test_a_stacked_sibling_is_recorded_with_its_geometry(self):
        v = self._pair()
        rows = v.detail["grammar"]["s6_stacked_with"]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertTrue(r["this_is_upper"])
        self.assertAlmostEqual(r["y_gap"], 90.0, places=2)
        self.assertAlmostEqual(r["x_overlap_frac"], 1.0, places=2)
        self.assertEqual(r["iou"], 0.0)

    def test_the_LOWER_arc_records_the_pair_from_its_own_side(self):
        """⚠️ `this_is_upper` is stated about THIS arc so a row reads without
        its sibling's row — the two are written independently and a consumer
        that saw only one must still be able to order the pair."""
        v = self._pair()
        log, _ = _log_with_stems("slur", _HEADS, [], arc_y=(40.0, 60.0),
                                 second_arc=("tie", (110.0, 290.0),
                                             (150.0, 170.0)))
        log.freeze()
        adjudicate.run(log)
        lower = log.verdict(Q.ARC_KIND, R.glyph(0, 0, 0, 0, 99))
        self.assertFalse(lower.detail["grammar"]["s6_stacked_with"][0]
                         ["this_is_upper"])
        self.assertTrue(v.detail["grammar"]["s6_stacked_with"][0]
                        ["this_is_upper"])

    def test_an_arc_that_does_NOT_overlap_in_x_is_not_a_stack(self):
        log, _ = _log_with_stems("slur", _HEADS, [], arc_y=(40.0, 60.0),
                                 second_arc=("tie", (900.0, 1100.0),
                                             (150.0, 170.0)))
        v = _decide(log)
        self.assertNotIn("s6_stacked_with", v.detail["grammar"])

    def test_a_DUPLICATE_is_recorded_too_with_a_NEGATIVE_gap(self):
        """⚠️ NOT FILTERED OUT HERE. `_place_arcs` has no dedupe and several
        such pairs disagree about their own kind; a rule that silently dropped
        them would hide the population rather than let it be measured."""
        log, _ = _log_with_stems("slur", _HEADS, [], arc_y=(40.0, 60.0),
                                 second_arc=("tie", (100.0, 300.0),
                                             (42.0, 62.0)))
        v = _decide(log)
        r = v.detail["grammar"]["s6_stacked_with"][0]
        self.assertLess(r["y_gap"], 0.0, "an overlapping pair is NOT a stack")
        self.assertGreater(r["iou"], 0.7, "it is a duplicate, and says so")

    def test_a_LONE_arc_records_nothing(self):
        log, _ = _log_with_stems("tie", _HEADS, [])
        v = _decide(log)
        self.assertNotIn("s6_stacked_with", v.detail["grammar"])

    def test_it_changes_NO_verdict(self):
        """S6 says the upper of this pair is a slur; this arc reads `tie`."""
        bare = _decide(_log_with("tie", _HEADS)[0])
        log, _ = _log_with_stems("tie", _HEADS, [], arc_y=(40.0, 60.0),
                                 second_arc=("slur", (110.0, 290.0),
                                             (150.0, 170.0)))
        v = _decide(log)
        self.assertEqual(v.value, "tie")
        self.assertEqual(v.value, bare.value)
        self.assertEqual(v.reason, bare.reason)
        self.assertTrue(v.detail["grammar"]["s6_stacked_with"][0]
                        ["this_is_upper"])

    def test_it_reads_no_pitch(self):
        import inspect
        from tools.omr.staged.adjudicators import ownership
        body = inspect.getsource(ownership._s6_stack_view).split('"""')[-1]
        self.assertNotIn("pitch", body)
