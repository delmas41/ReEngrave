"""ROADMAP 2.153 (STAGED ADJUDICATE `rhythm.adjudicate_duration` / `rhythm._beam_levels`), flag
`OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM`, default OFF.

Sean 2026-10-16: notehead first, stem second, beam or flag third -- "a later step never overturns an earlier one". A beam level
belongs to a STEM: the strokes that count at a head are the ones its stem reaches. Today a stroke whose box merely covers the
head's centre column counts as a CERTAIN level whether or not any stem reaches it (`_beam_levels`: `x0 <= x_center <= x1`),
so a slur end or a neighbour's secondary beam that happens to span the column writes an eighth, a sixteenth or a 32nd PLAIN
(Sean's 2.151 tiles 7 and 28: a dotted eighth read as a dotted 32nd, a dotted quarter read as a dotted eighth).

The rule: a stroke that no stem box reaches and that the ink-join reader did not read JOINED is POSSIBLE, never CERTAIN -- so
the note narrows over the levels it leaves open (`beams_ambiguous`, equal support: one witness, a box overlap, orders nothing)
instead of deciding one. A joined stroke, or one the join reader reads JOINED, stays certain (the positive controls); a stroke
the join reader reads NOT joined keeps its existing 2.38b path (`beam_certain_not_joined`). The bar sum is not read.

Every test with the flag ON has a control beside it that differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_beam_stem_join import _beam, _beam_stem_join, _stem

FLAG = rhythm.BEAM_LEVEL_NEEDS_A_JOINED_STEM_ENV


def _head(log):
    """Head box x=135-155 (centre 145), y=90-106 -- the 2.38 fixtures' own head."""
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _run(log, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)


def _beats(v):
    return sorted(c.value["beats"] for c in v.candidates)


class TestAStrokeNoStemReachesIsNotACertainLevel(unittest.TestCase):

    def _unjoined(self, n_strokes=1):
        """One head, NO stem read, `n_strokes` strokes whose boxes cover its centre column (x 100-200 holds x=145)."""
        log = Log()
        for i in range(n_strokes):
            _beam(log, y=40 + 12 * i, x0=100, x1=200)
        return log, _head(log)

    def test_flag_off_the_column_stroke_still_decides_an_eighth(self):
        """Control 1 (the baseline this lane moves): today the same evidence DECIDES one level."""
        log, g = self._unjoined()
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_column_stroke_with_no_stem_narrows(self):
        log, g = self._unjoined()
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(_beats(v), [0.5, 1.0])               # the eighth AND the quarter stay open
        self.assertEqual(len({c.support for c in v.candidates}), 1)   # one box-overlap witness orders nothing
        self.assertEqual(v.detail["levels_certain"], 0)
        self.assertEqual(v.detail["levels_possible"], 1)

    def test_two_column_strokes_with_no_stem_narrow_over_every_level(self):
        log, g = self._unjoined(2)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(_beats(v), [0.25, 0.5, 1.0])

    def test_control_a_stem_that_reaches_the_stroke_still_decides(self):
        """Same stroke, plus ONE stem box that overlaps it: only the stem differs from the case above."""
        log = Log()
        _beam(log, y=40, x0=100, x1=200)
        g = _head(log)
        _stem(log, x=135, y=38, h=60)                         # 38..98 meets the stroke at y=40
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_by_stem"], 1)

    def test_a_joined_level_stays_certain_and_unjoined_ones_beside_it_only_widen(self):
        """Sean's 2.151 tile 7: one beam the stem reaches (a dotted eighth) and two more strokes over its column that no stem
        reaches (a neighbour's secondary beams / a slur). The first is certain, the other two are possible."""
        log = Log()
        _beam(log, y=40, x0=60, x1=140)                       # the stem's own beam (x1 < centre; reached by the stem)
        _beam(log, y=52, x0=141, x1=300)                      # spans the centre, clear of the stem's x
        _beam(log, y=64, x0=141, x1=300)
        g = _head(log)
        _stem(log, x=135, y=38, h=60)
        _run(log, on=False)
        off = log.verdict(Q.DURATION, g)
        self.assertEqual(off.value["beats"], 0.125)           # today: three levels, decided
        log2 = Log()
        _beam(log2, y=40, x0=60, x1=140)
        _beam(log2, y=52, x0=141, x1=300)
        _beam(log2, y=64, x0=141, x1=300)
        g2 = _head(log2)
        _stem(log2, x=135, y=38, h=60)
        _run(log2)
        v = log2.verdict(Q.DURATION, g2)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["levels_certain"], 1)
        self.assertEqual(v.detail["levels_possible"], 3)
        self.assertEqual(_beats(v), [0.125, 0.25, 0.5])       # the true eighth is among them; the quarter is not offered


class TestTheSecondWitnessKeepsItsWord(unittest.TestCase):
    """A stem exists but stops short of the stroke (no box overlap); the ink-join reader speaks."""

    def _short_stem(self, found):
        log = Log()
        beam = _beam(log, y=40, x0=100, x1=200)
        g = _head(log)
        stem = _stem(log, x=135, y=70, h=30)                  # tip at y=70, 26 px under the stroke: no box overlap
        if found is not None:
            _beam_stem_join(log, stem_row_id=stem.id, beam_row_id=beam.id, end="top", found=found)
        return log, g

    def test_ink_reads_it_joined_so_it_stays_certain(self):
        log, g = self._short_stem(True)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)

    def test_the_join_reader_unread_so_it_narrows(self):
        log, g = self._short_stem(None)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(_beats(v), [0.5, 1.0])

    def test_ink_reads_it_not_joined_keeps_the_2_38b_path(self):
        """Neither flag state changes what 2.38b does with a stroke the ink reads NOT joined."""
        for on in (False, True):
            log, g = self._short_stem(False)
            _run(log, on=on)
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.NARROWED)
            self.assertEqual(v.reason, "beam_certain_not_joined")


class TestTheOldPaddedRangeIsNotTouched(unittest.TestCase):
    """The 2.38 baseline (a stroke 5 px short of the centre: padded, possible, never certain) keeps its ordering under the flag:
    only strokes the flag itself demoted lose the 'certain outranks' claim."""

    def test_padded_only_stroke_still_ranks_the_quarter_first(self):
        for on in (False, True):
            log = Log()
            _beam(log, y=40, x0=60, x1=140)
            g = _head(log)
            _stem(log, x=135, y=70, h=30)                      # tip 26 px under the stroke: no box overlap, no join row
            _run(log, on=on)
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.NARROWED)
            self.assertEqual(v.reason, "beams_ambiguous")
            self.assertEqual(v.candidates[0].value["beats"], 1.0)
            self.assertGreater(v.candidates[0].support, v.candidates[1].support)


class TestBeamLevelsDirect(unittest.TestCase):
    class _Row:
        def __init__(self, id_, x0, x1):
            self.id = id_
            self.detail = {"x0": x0, "x1": x1}

    def test_default_is_unchanged(self):
        b = self._Row("b1", 100, 200)
        self.assertEqual(rhythm._beam_levels([b], 150, 20, ()), (1, 1, ()))

    def test_unjoined_column_stroke_is_possible_only(self):
        b = self._Row("b1", 100, 200)
        self.assertEqual(rhythm._beam_levels([b], 150, 20, (), unjoined_possible=True), (0, 1, ()))

    def test_joined_stroke_is_certain_either_way(self):
        b = self._Row("b1", 100, 200)
        self.assertEqual(rhythm._beam_levels([b], 150, 20, (b,), unjoined_possible=True), (1, 1, ()))

    def test_a_joined_witness_makes_it_certain(self):
        b = self._Row("b1", 100, 200)
        self.assertEqual(rhythm._beam_levels([b], 150, 20, (), {"b1": True}, unjoined_possible=True), (1, 1, ()))

    def test_a_not_joined_witness_keeps_the_conflict_path(self):
        b = self._Row("b1", 100, 200)
        self.assertEqual(rhythm._beam_levels([b], 150, 20, (), {"b1": False}, unjoined_possible=True), (1, 1, ("b1",)))


class TestTheFlag(unittest.TestCase):

    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.beam_level_needs_a_joined_stem_enabled())

    def test_only_an_on_word_enables(self):
        for w in ("1", "true", "yes", "on", "ON"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertTrue(rhythm.beam_level_needs_a_joined_stem_enabled(), w)
        for w in ("", "0", "false", "no", "off", "2", "enabled"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.beam_level_needs_a_joined_stem_enabled(), w)


if __name__ == "__main__":
    unittest.main()
