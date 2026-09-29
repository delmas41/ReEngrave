"""`stem_direction` and `voices`: the two quantities that were DERIVABLE from
a row already on the record and undeclared.

⚠️ WHY THEY ARE TOGETHER. `Q.STEM` has carried 916 rows on a three-page
fixture since the CV rung was wired, and `gather_coverage` listed
`stem_direction` in `NO_VOCABULARY` — so the divisi guard in
`adjudicate_event` reported `not_implemented`, `export._events`'s
`_directions_conflict` was inert, and `export._paired_spans` was handed an
EMPTY `voice_of` map. Three rules present, none of them able to fire, and an
inert rule is indistinguishable from one that ran and found nothing.

⚠️ THE SPLIT IS THE LEGACY ONE AND IS CALLED RATHER THAN RESTATED —
`transcribe._stem_direction` for the projection test,
`voicing.split_events_into_voices` for the candidate split. Both were paid
for by real regressions, and a second copy is how the staged and legacy
paths would come to disagree about a file's `<backup>` arithmetic.

⚠️⚠️ ROADMAP 2.21b, `TestTheVoiceSplit`: Sean's convention (`docs/
DECISIONS.md` 2026-09-29, answering `benchmarks/omr-voice-split-2026-09/
QUESTION.md`) gates that candidate on THREE rules, in order -- same-beat
opposite stems decide two voices outright; else a single merged line
summing to the METER IN FORCE is one voice; else two streams that EACH sum
to the meter AND sit in separate, vertically non-overlapping bands are two
voices; else this ABSTAINS. The fixtures below inject `Q.STEM_DIRECTION`,
`Q.DURATION`, `Q.METER` and `Q.NOTEHEAD_STAFF_POSITION` directly as already-
DECIDED verdicts/observations (CLAUDE.md 2026-09-29: microscopic tests, not
pricing runs) rather than driving the real geometric readers, so each test
isolates `adjudicate_voices`'s OWN gate.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)
SYSTEM = R.system(0, 0)


def _head(log, gi, x, y=0, w=20, h=16):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _head_pf(log, gi, x, y, page_x, page_y=0.0, w=20, h=16):
    """`_head`, plus a PAGE-frame box -- what rule (1)'s same-beat test
    reads. `page_x` is independent of the canonical `x` so a fixture can
    hold two heads apart canonically (which is what makes `Q.EVENT` treat
    them as separate events at all) while controlling, separately, whether
    they sound together on the page."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead",
                bbox_page_px=[page_x, page_y, page_x + w, page_y + h])
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


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _direction(log, glyph, direction):
    """Injects an already-DECIDED `Q.STEM_DIRECTION`, bypassing the real
    stem-projection geometry (covered on its own in
    `TestWhichWayTheStemPoints` below)."""
    _v(log, glyph, Q.STEM_DIRECTION, Outcome.DECIDED, direction,
       reason="test_direction")


def _duration(log, glyph, beats):
    _v(log, glyph, Q.DURATION, Outcome.DECIDED,
       {"beats": beats, "written": beats, "dots": 0}, reason="test_duration")


def _meter(log, num=4, den=4):
    return _v(log, SYSTEM, Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _spacing(log, staff=STAFF, px=10.0):
    log.observe(staff, Q.STAFF_SPACING, px, reader=READERS.GEOMETRY,
                frame="page")


def _position(log, glyph, pos):
    log.observe(glyph, Q.NOTEHEAD_STAFF_POSITION, pos, reader=READERS.GEOMETRY,
                frame="cell:0")


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
    """ROADMAP 2.21b. Every fixture here injects `Q.STEM_DIRECTION` directly
    and runs only `(Q.EVENT, Q.VOICES)` -- `Q.ONSET_COLUMN` is deliberately
    never decided, so rule (1)'s same-beat test always takes the `raw_page_x`
    fallback off this staff's own page frame, never the cross-staff
    `onset_column` path (covered on a real record in `benchmarks/
    omr-voice-split-2026-09/FINDINGS.md`, not re-proven here)."""

    def test_one_direction_is_ONE_voice(self):
        """No candidate at all -- rule 8's question never arises."""
        log = Log()
        _head(log, 0, 90)
        _head(log, 1, 300)
        _direction(log, R.glyph(0, 0, 0, 0, 0), "up")
        _direction(log, R.glyph(0, 0, 0, 0, 1), "up")
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "one_voice")
        self.assertEqual(v.value["n_voices"], 1)
        self.assertEqual(v.value["rests_in_every_voice"], [])

    def test_RULE_3_a_flipping_line_that_sums_to_the_bar_is_ONE_voice(self):
        """Sean's crop shape, `docs/DECISIONS.md` 2026-09-29: *"those crops
        would obviously be 1 voice because the measure math adds up to 1
        measure."* Four quarters (4/4 -> 4.0), up/down stems alternating,
        no two heads sharing a page x (rule 1 does not fire)."""
        log = Log()
        _spacing(log)
        _meter(log, 4, 4)
        xs = [90, 300, 500, 700]
        dirs = ["up", "down", "up", "down"]
        for gi, (x, d) in enumerate(zip(xs, dirs)):
            g = _head_pf(log, gi, x, 0, page_x=x)
            _direction(log, g, d)
            _duration(log, g, 1.0)
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "one_voice_sums")
        self.assertEqual(v.value["n_voices"], 1)
        self.assertEqual(v.detail["merged_quarters"], 4.0)

    def test_RULE_1_SAME_BEAT_opposite_stems_are_TWO_voices_no_meter_needed(self):
        """Rule (1) decides OUTRIGHT: no `Q.METER` is injected at all, and
        the two heads' own durations (0.5 + 0.5) do not sum to anything --
        rule 1 must not need either fact to fire."""
        log = Log()
        _spacing(log)
        g0 = _head_pf(log, 0, 90, 0, page_x=200)
        g1 = _head_pf(log, 1, 300, 0, page_x=200)   # SAME page x -- overlap
        _direction(log, g0, "up")
        _direction(log, g1, "down")
        _duration(log, g0, 0.5)
        _duration(log, g1, 0.5)
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "two_voices_same_beat")
        self.assertEqual(v.value["voices"], [[0], [1]])
        self.assertEqual(v.detail["rule_1_same_beat"]["source"], "raw_page_x")

    def test_RULE_2_two_offset_full_streams_UPPER_ABOVE_LOWER_are_TWO_voices(self):
        """Two lines NOT lined up (no shared page x, rule 1 does not fire),
        each its own 4/4 bar (4 x 1.0), sitting in separate staff bands --
        upper stream's positions [0.8, 1.2], lower's [4.8, 5.2], no overlap."""
        log = Log()
        _spacing(log)
        _meter(log, 4, 4)
        up_x = [90, 300, 500, 700]
        up_pos = [1.0, 0.8, 1.2, 1.0]
        down_x = [150, 350, 550, 750]
        down_pos = [5.0, 4.8, 5.2, 5.0]
        for gi, (x, p) in enumerate(zip(up_x, up_pos)):
            g = _head_pf(log, gi, x, 0, page_x=x)
            _direction(log, g, "up")
            _duration(log, g, 1.0)
            _position(log, g, p)
        for gi, (x, p) in enumerate(zip(down_x, down_pos), start=4):
            g = _head_pf(log, gi, x, 200, page_x=x, page_y=200)
            _direction(log, g, "down")
            _duration(log, g, 1.0)
            _position(log, g, p)
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "two_voices_separated_and_full")
        self.assertEqual(v.value["n_voices"], 2)
        self.assertEqual(v.detail["stream_quarters"], [4.0, 4.0])
        sep = v.detail["separation"]
        self.assertEqual(sep["a_range"], [0.8, 1.2])
        self.assertEqual(sep["b_range"], [4.8, 5.2])

    def test_RULE_2_CONTROL_two_full_streams_INTERLEAVED_IN_HEIGHT_ABSTAINS(self):
        """Sean's own positive control: both sides are a full 4/4 bar (rule
        (2)'s FIRST test passes) but the two streams' staff positions
        INTERLEAVE ([1,3] and [2,4] overlap) rather than sitting apart, so a
        human would NOT recognise two voices here -- ABSTAIN, not a guess."""
        log = Log()
        _spacing(log)
        _meter(log, 4, 4)
        up_x = [90, 300, 500, 700]
        up_pos = [1.0, 3.0, 1.0, 3.0]
        down_x = [150, 350, 550, 750]
        down_pos = [2.0, 4.0, 2.0, 4.0]
        for gi, (x, p) in enumerate(zip(up_x, up_pos)):
            g = _head_pf(log, gi, x, 0, page_x=x)
            _direction(log, g, "up")
            _duration(log, g, 1.0)
            _position(log, g, p)
        for gi, (x, p) in enumerate(zip(down_x, down_pos), start=4):
            g = _head_pf(log, gi, x, 200, page_x=x, page_y=200)
            _direction(log, g, "down")
            _duration(log, g, 1.0)
            _position(log, g, p)
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_voice_convention_fits")
        self.assertEqual(v.detail["stream_quarters"], [4.0, 4.0])
        self.assertEqual(v.detail["separation"]["a_range"], [1.0, 3.0])
        self.assertEqual(v.detail["separation"]["b_range"], [2.0, 4.0])

    def test_NEITHER_SUMS_ABSTAINS(self):
        """No shared beat, the merged line falls short of the bar, and the
        naive two-stream split ALSO falls short on each side -- none of the
        three rules fits."""
        log = Log()
        _spacing(log)
        _meter(log, 4, 4)
        g0 = _head_pf(log, 0, 90, 0, page_x=90)
        g1 = _head_pf(log, 1, 300, 0, page_x=300)
        _direction(log, g0, "up")
        _direction(log, g1, "down")
        _duration(log, g0, 1.0)
        _duration(log, g1, 1.0)                 # merged 2.0 != 4.0
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_voice_convention_fits")
        self.assertEqual(v.detail["merged_quarters"], 2.0)
        self.assertEqual(v.detail["target_quarters"], 4.0)

    def test_NO_METER_ABSTAINS_before_rules_2_and_3_are_even_tried(self):
        """Sean, 2026-09-29: *"no meter -> abstain"*. Rule (1) does not fire
        (no shared beat) and no `Q.METER` was ever decided for this system,
        so rules (2)/(3) have nothing to sum against."""
        log = Log()
        _spacing(log)
        g0 = _head_pf(log, 0, 90, 0, page_x=90)
        g1 = _head_pf(log, 1, 300, 0, page_x=300)
        _direction(log, g0, "up")
        _direction(log, g1, "down")
        _duration(log, g0, 1.0)
        _duration(log, g1, 1.0)
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_voice_convention_fits")
        self.assertEqual(v.detail["why"], "no_meter")

    def test_a_REST_is_in_EVERY_voice_and_is_NAMED_as_such(self):
        """⚠️ THE ONE PLACE THE VALUE IS A COVER AND NOT A PARTITION. Each
        voice needs its own bar to sum, so `<rest>` is written once per voice
        — and a consumer counting glyphs would report the duplicate as a loss
        unless the verdict says it is deliberate. Built on rule (1) (same
        beat), which needs no meter or duration at all."""
        log = Log()
        _spacing(log)
        g0 = _head_pf(log, 0, 90, 0, page_x=200)
        g1 = _head_pf(log, 1, 300, 0, page_x=200)
        r = _rest(log, 2, 500)
        _direction(log, g0, "up")
        _direction(log, g1, "down")
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertEqual(v.reason, "two_voices_same_beat")
        self.assertEqual(v.value["n_voices"], 2)
        self.assertIn(2, v.value["voices"][0])
        self.assertIn(2, v.value["voices"][1])
        self.assertEqual(v.value["rests_in_every_voice"], [2])

    def test_a_one_voice_bar_names_NO_duplicated_rest(self):
        """The positive control for the field above: with one stream there is
        no duplication to declare, and a field that always listed the rests
        would read as a duplication that never happened."""
        log = Log()
        g0 = _head(log, 0, 90)
        _rest(log, 1, 500)
        _direction(log, g0, "up")
        v = _run(log, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertEqual(v.value["n_voices"], 1)
        self.assertEqual(v.value["rests_in_every_voice"], [])

    def test_with_NO_event_verdict_it_abstains_rather_than_inventing_events(self):
        """⚠️ `nothing_to_split` means NOBODY GROUPED THIS BAR, not "there is
        one voice". Building shim events out of glyph boxes here would be a
        second grouping rule nothing forces to agree with `Q.EVENT`."""
        log = Log()
        g0 = _head(log, 0, 90)
        _direction(log, g0, "up")
        log = _run(log, Q.VOICES)                     # EVENT deliberately off
        v = log.verdict(Q.VOICES, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "nothing_to_split")

        log2 = Log()                                   # positive control
        g0b = _head(log2, 0, 90)
        _direction(log2, g0b, "up")
        self.assertIs(_run(log2, Q.EVENT, Q.VOICES).verdict(
            Q.VOICES, CELL).outcome, Outcome.DECIDED)


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
