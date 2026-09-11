"""`stem_direction` and `voices`: the two quantities that were DERIVABLE from
a row already on the record and undeclared.

⚠️ WHY THEY ARE TOGETHER. `Q.STEM` has carried 916 rows on a three-page
fixture since the CV rung was wired, and `gather_coverage` listed
`stem_direction` in `NO_VOCABULARY` — so the divisi guard in
`adjudicate_event` reported `not_implemented`, `export._events`'s
`_directions_conflict` was inert, and `export._paired_spans` was handed an
EMPTY `voice_of` map. Three rules present, none of them able to fire, and an
inert rule is indistinguishable from one that ran and found nothing.

⚠️ THE RULES ARE THE LEGACY ONES AND ARE CALLED RATHER THAN RESTATED —
`transcribe._stem_direction` for the projection test,
`voicing.split_events_into_voices` for the split. Both were paid for by real
regressions, and a second copy is how the staged and legacy paths would come
to disagree about a file's `<backup>` arithmetic.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)


def _head(log, gi, x, y=0, w=20, h=16):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _rest(log, gi, x, y=0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.REST, "restQuarter", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("restQuarter", x, y, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest")
    return g


def _stem(log, x, y, w=3, h=60):
    log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2,
                image="no_staff", staff_lines_erased=True)


def _run(log, *order):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=order or (Q.STEM_DIRECTION, Q.EVENT, Q.VOICES))
    return log


class TestTheRulesAreTheLEGACYONES(unittest.TestCase):
    """⚠️ AN AST CHECK, because a copied rule does not fail a test. Both were
    paid for by a real regression and neither has a constant to import, so
    the only thing that can be pinned is that the function is CALLED."""

    def test_the_projection_test_is_called_not_restated(self):
        import inspect
        from tools.omr.staged.adjudicators import rhythm
        src = inspect.getsource(rhythm.adjudicate_stem_direction)
        self.assertIn("_stem_direction", src)
        self.assertNotIn("above > below", src)

    def test_the_split_is_called_not_restated(self):
        import inspect
        from tools.omr.staged.adjudicators import rhythm
        src = inspect.getsource(rhythm.adjudicate_voices)
        self.assertIn("split_events_into_voices", src)

    def test_neither_is_a_stub(self):
        for q in (Q.STEM_DIRECTION, Q.VOICES):
            self.assertFalse(adjudicate.REGISTRY[q].stub, q)


class TestWhichWayTheStemPoints(unittest.TestCase):

    def test_a_stem_rising_above_its_head_is_UP(self):
        log = Log()
        _head(log, 0, 90)                       # box 90..110, y 0..16
        _stem(log, 88, -60, h=64)               # -60..4
        v = _run(log, Q.STEM_DIRECTION).verdict(Q.STEM_DIRECTION,
                                                R.glyph(0, 0, 0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "up")
        self.assertEqual(v.reason, "stem_projection")

    def test_a_stem_falling_below_its_head_is_DOWN(self):
        """The other side. Without it, inverting the comparison passes."""
        log = Log()
        _head(log, 0, 90)
        _stem(log, 88, 12, h=60)                # 12..72
        v = _run(log, Q.STEM_DIRECTION).verdict(Q.STEM_DIRECTION,
                                                R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.value, "down")

    def test_a_DOUBLE_STOP_gets_ONE_direction_for_BOTH_heads(self):
        """⚠️⚠️ THE REGRESSION THIS RULE WAS PAID FOR. Two heads on ONE
        physical stem: comparing each head's centre against the stem's
        MIDPOINT puts the stem above the lower head and below the upper one
        for any interval wider than the stem is long, the two members
        disagree, the divisi guard refuses to merge them, and one chord
        exports as two voices one note each. Measured on Brahms's Viola,
        where `C4/C5` came out as `C4` then `C5` at the end of the bar.

        ⚠️ THE INTERVAL HAS TO BE WIDE. Thirds were unaffected, which is what
        made the fault look intermittent — so this fixture spans a tenth's
        worth of the cell rather than a comfortable third.
        """
        log = Log()
        _head(log, 0, 90, y=0)                  # upper
        _head(log, 1, 90, y=120)                # lower, far below
        _stem(log, 88, -20, h=150)              # -20..130, touching both
        log = _run(log, Q.STEM_DIRECTION)
        a = log.verdict(Q.STEM_DIRECTION, R.glyph(0, 0, 0, 0, 0))
        b = log.verdict(Q.STEM_DIRECTION, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(a.outcome, Outcome.DECIDED)
        self.assertEqual(a.value, b.value,
                         "the two members of one chord disagreed")
        self.assertEqual(a.detail["heads_on_stem"], 2)

    def test_a_head_with_no_stem_says_no_stem(self):
        """A whole note has none, and on a scan a stem is often simply
        missed. ⚠️ NOT the same silence as `stems_disagree`."""
        log = Log()
        _head(log, 0, 90)
        v = _run(log, Q.STEM_DIRECTION).verdict(Q.STEM_DIRECTION,
                                                R.glyph(0, 0, 0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_stem")

        log2 = Log()                            # positive control
        _head(log2, 0, 90)
        _stem(log2, 88, -60, h=64)
        self.assertIs(_run(log2, Q.STEM_DIRECTION).verdict(
            Q.STEM_DIRECTION, R.glyph(0, 0, 0, 0, 0)).outcome,
            Outcome.DECIDED)

    def test_two_OPPOSING_stems_on_one_head_abstain_rather_than_vote(self):
        log = Log()
        _head(log, 0, 90)
        _stem(log, 92, -60)
        _stem(log, 105, 12)
        v = _run(log, Q.STEM_DIRECTION).verdict(Q.STEM_DIRECTION,
                                                R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.reason, "stems_disagree")
        self.assertEqual(sorted(v.detail["answers"]), ["down", "up"])


class TestTheVoiceSplit(unittest.TestCase):

    def test_one_direction_is_ONE_voice(self):
        log = Log()
        _head(log, 0, 90)
        _head(log, 1, 300)
        _stem(log, 88, -60, h=64)
        _stem(log, 298, -60, h=64)
        v = _run(log).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "one_voice")
        self.assertEqual(v.value["n_voices"], 1)
        self.assertEqual(v.value["rests_in_every_voice"], [])

    def test_both_directions_at_different_x_are_TWO_voices(self):
        log = Log()
        _head(log, 0, 90)
        _head(log, 1, 300)
        _stem(log, 88, -60, h=64)               # up
        _stem(log, 298, 12, h=60)               # down
        v = _run(log).verdict(Q.VOICES, CELL)
        self.assertEqual(v.reason, "two_voices")
        self.assertEqual(v.value["voices"], [[0], [1]])

    def test_a_REST_is_in_EVERY_voice_and_is_NAMED_as_such(self):
        """⚠️ THE ONE PLACE THE VALUE IS A COVER AND NOT A PARTITION. Each
        voice needs its own bar to sum, so `<rest>` is written once per voice
        — and a consumer counting glyphs would report the duplicate as a loss
        unless the verdict says it is deliberate."""
        log = Log()
        _head(log, 0, 90)
        _head(log, 1, 300)
        _rest(log, 2, 500)
        _stem(log, 88, -60, h=64)
        _stem(log, 298, 12, h=60)
        v = _run(log).verdict(Q.VOICES, CELL)
        self.assertEqual(v.value["n_voices"], 2)
        self.assertIn(2, v.value["voices"][0])
        self.assertIn(2, v.value["voices"][1])
        self.assertEqual(v.value["rests_in_every_voice"], [2])

    def test_a_one_voice_bar_names_NO_duplicated_rest(self):
        """The positive control for the field above: with one stream there is
        no duplication to declare, and a field that always listed the rests
        would read as a duplication that never happened."""
        log = Log()
        _head(log, 0, 90)
        _rest(log, 1, 500)
        _stem(log, 88, -60, h=64)
        v = _run(log).verdict(Q.VOICES, CELL)
        self.assertEqual(v.value["n_voices"], 1)
        self.assertEqual(v.value["rests_in_every_voice"], [])

    def test_with_NO_event_verdict_it_abstains_rather_than_inventing_events(self):
        """⚠️ `nothing_to_split` means NOBODY GROUPED THIS BAR, not "there is
        one voice". Building shim events out of glyph boxes here would be a
        second grouping rule nothing forces to agree with `Q.EVENT`."""
        log = Log()
        _head(log, 0, 90)
        _stem(log, 88, -60, h=64)
        log = _run(log, Q.STEM_DIRECTION, Q.VOICES)   # EVENT deliberately off
        v = log.verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "nothing_to_split")

        log2 = Log()                                  # positive control
        _head(log2, 0, 90)
        _stem(log2, 88, -60, h=64)
        self.assertIs(_run(log2).verdict(Q.VOICES, CELL).outcome,
                      Outcome.DECIDED)


class TestTheExporterReadsIt(unittest.TestCase):
    """⚠️ THE THIRD LEG AGAIN. An adjudicator that lands alone is a fresh
    `decided_and_unwritten` row, which is the bucket the arc session emptied."""

    def test_the_exporter_reads_the_voices_verdict(self):
        import inspect
        from tools.omr.staged import export
        self.assertIn("Q.VOICES", inspect.getsource(export._voice_split))

    def test_the_arc_pairing_is_handed_a_REAL_voice_map(self):
        """It was `{}` until 2026-09-10, so `_paired_spans`'s one-voice rule
        was inert."""
        import inspect
        from tools.omr.staged import export
        src = inspect.getsource(export._pair_arcs)
        self.assertIn("voice_of", src)
        self.assertNotIn("breaks, {})", src)

    def test_a_rest_is_NOT_given_a_voice_in_the_arc_map(self):
        """⚠️ That map exists to refuse an arc crossing streams and a rest
        binds no arc; assigning it one would make it look like a member of
        whichever stream was listed last."""
        import inspect
        from tools.omr.staged import export
        self.assertIn("rests_in_every_voice",
                      inspect.getsource(export._voice_of_notehead))


if __name__ == "__main__":
    unittest.main()
