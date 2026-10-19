"""ROADMAP 2.162 -- a bar holding an undecided (NARROWED) note has no known length: `OMR_NARROWED_BAR_LENGTH_UNKNOWN`,
default OFF (Sean 2026-10-17, DECISIONS). STAGED ADJUDICATE (the meter's bar witness) + EVALUATE.

Every consumer that SUMS a bar holding a narrowing at its first candidate (derived by
`benchmarks/omr-bar-sum-holdout-2026-09/probe/consumers_2_162.py`) is tested here, each beside a flag-off control that shows
the old behaviour, so removing the guard turns the flag-on test red:

* `rhythm._bar_lengths_for` -> `_score_bars` (the carry, `_corroborate`): a range CONFIRMS a carried meter it contains, and
  a range that excludes it is silent, never a vote against.
* `rhythm._bar_run` (a printed change's bar run) and `rhythm._bars_opinion` (the meter the bars name): a range never names a
  length and never counts as a miss.
* `consequences.reconcile_duration`: a bar over (or short) under EVERY candidate still moves its one decided note (2.153b tiles
  8/15/5/11); a bar that may already fit moves nothing.
* `consequences._bar_total_excluding` (`reinstate_rest_between_staves`): a narrowed bar is not summed at all.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, bar_length, consequences
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Candidate
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_narrowed_bar_2_97 import CELL, _EvalBar, _dv, _v

ENV = consequences.NARROWED_BAR_LENGTH_UNKNOWN_ENV
CONFIRM = consequences.BAR_SUM_CONFIRM_ONLY_ENV


def _env(on, confirm="narrowed"):
    return mock.patch.dict(os.environ, {ENV: "1" if on else "0", CONFIRM: confirm}, clear=False)


class TestTheWord(unittest.TestCase):

    def test_default_on_and_only_off_words_disable(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV, None)
            self.assertTrue(consequences.narrowed_bar_length_unknown())
        for word, want in (("1", True), ("on", True), ("yes", True), ("true", True), ("0", False), ("off", False), ("no", False),
                           ("false", False)):
            with mock.patch.dict(os.environ, {ENV: word}, clear=False):
                self.assertEqual(consequences.narrowed_bar_length_unknown(), want, word)


class TestTheOneHelper(unittest.TestCase):
    """`staged.bar_length` -- the helper every consumer above calls (2.165 imports it)."""

    def _bar(self):
        b = _EvalBar(2, 4)
        n = b.narrowed()                      # {0.5, 1.0}
        b.decided(1.0)
        log, _m = b.build()
        notes = consequences._standing(log, CELL, Q.DURATION)
        return log, notes

    def test_CONTROL_off_a_narrowing_counts_at_its_first_candidate(self):
        log, notes = self._bar()
        with _env(False):
            got = bar_length.bar_length(log, CELL, notes)
        self.assertTrue(got.known)
        self.assertEqual(got.value, 1.5)

    def test_on_a_narrowing_makes_a_range_RED(self):
        log, notes = self._bar()
        with _env(True):
            got = bar_length.bar_length(log, CELL, notes)
        self.assertFalse(got.known)
        self.assertIsNone(got.value)
        self.assertEqual((got.lo, got.hi), (1.5, 2.0))
        self.assertTrue(got.contains(2.0) and not got.contains(2.5))

    def test_all_decided_is_known_either_way(self):
        b = _EvalBar(2, 4)
        b.decided(1.0)
        b.decided(1.0)
        log, _m = b.build()
        notes = consequences._standing(log, CELL, Q.DURATION)
        for on in (False, True):
            with _env(on):
                self.assertEqual(bar_length.bar_length(log, CELL, notes).value, 2.0)

    def test_no_decided_grouping_is_unknown(self):
        log = Log()
        self.assertTrue(bar_length.bar_length(log, CELL, []).unknown)


# ── the meter: carry corroborated by the bars ─────────────────────────────────────────────────────────────────────────

N_STAVES = 3


def _opening(log, sysj, num, den):
    for st in range(N_STAVES):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE, (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7, raw=f"{num}/{den}")


def _structure(log, sysj, n_cells):
    log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=sysj, quantity=Q.SYSTEM_STAFF_COUNT,
                                  outcome=Outcome.DECIDED, value=N_STAVES, decider="t", reason="counted"))
    for st in range(N_STAVES):
        log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=R.staff(sysj.page, sysj.system, st),
                                      quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED, value=n_cells,
                                      decider="t", reason="barlines"))


def _bar(log, sysj, cell, beats=None, cands=None):
    """One bar on every staff: one head, DECIDED at `beats`, or NARROWED over `cands` (first candidate first)."""
    for st in range(N_STAVES):
        c = R.cell(sysj.page, sysj.system, st, cell)
        g = R.glyph(sysj.page, sysj.system, st, cell, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:%d" % cell, score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 400, 0, 600, 16), reader=READERS.DETECTOR,
                    frame="cell:%d" % cell, score=0.9)
        if cands is None:
            log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                                          outcome=Outcome.DECIDED, value=_dv(beats), decider="t",
                                          reason="head_and_marks"))
        else:
            log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                                          outcome=Outcome.NARROWED, value=None, decider="t",
                                          reason="beams_ambiguous",
                                          candidates=tuple(Candidate(_dv(b), support=1.0) for b in cands)))
        log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=c, quantity=Q.EVENT, outcome=Outcome.DECIDED,
                                      value={"events": [{"glyphs": [0], "x": 500.0, "kind": "chord"}]},
                                      decider="t", reason="x_clustered"))


def _carry_case(narrowed_cands):
    """system(0,0) prints 6/8 (3 beats) and its bars fit; system(1,0) prints nothing, its bars: two of 3.0 beats and two
    that hold a NARROWED head on every staff, `narrowed_cands` first candidate first."""
    log = Log()
    src, dst = R.system(0, 0), R.system(1, 0)
    _structure(log, src, 4)
    _opening(log, src, 6, 8)
    for c in range(4):
        _bar(log, src, c, 3.0)
    _structure(log, dst, 4)
    _bar(log, dst, 0, 3.0)
    _bar(log, dst, 1, 3.0)
    _bar(log, dst, 2, cands=narrowed_cands)
    _bar(log, dst, 3, cands=narrowed_cands)
    return log, dst


def _meter_of(log, sysj, on):
    with _env(on):
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.METER]
        for s in sorted(log.subjects(R.Kind.SYSTEM)):
            adjudicate.adjudicate_one(log, spec, s)
        return log.verdict(Q.METER, sysj)


class TestTheCarry(unittest.TestCase):

    def test_CONTROL_off_a_narrowing_at_its_first_candidate_outweighs_the_carry(self):
        log, dst = _carry_case((4.0, 3.0))
        v = _meter_of(log, dst, on=False)
        self.assertNotEqual(v.outcome, Outcome.DECIDED)

    def test_on_a_range_holding_the_meter_confirms_the_carry_RED(self):
        log, dst = _carry_case((4.0, 3.0))
        v = _meter_of(log, dst, on=True)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual((v.value or {}).get("numerator"), 6)

    def test_on_a_range_excluding_the_meter_is_silent_not_a_vote_against_RED(self):
        # {4.0, 5.0}: the bar is not 3 beats under any candidate -- but its length is unknown, so it may not refute.
        log, dst = _carry_case((4.0, 5.0))
        off = _meter_of(log, dst, on=False)
        self.assertNotEqual(off.outcome, Outcome.DECIDED)             # CONTROL: two bars voted 4.0 against 3.0
        log, dst = _carry_case((4.0, 5.0))
        v = _meter_of(log, dst, on=True)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual((v.value or {}).get("numerator"), 6)


class TestAChangeAndTheBarsOwnVote(unittest.TestCase):

    def test_bar_run_a_range_fits_or_is_silent_never_a_miss_RED(self):
        bars = {1: [3.0, 3.0, 3.0], 2: [(2.5, 3.5)] * 3, 3: [(4.0, 5.0)] * 3}
        with _env(True):
            self.assertEqual(rhythm._bar_run(bars, 0, 3.0), (2, 0))

    def test_CONTROL_bar_run_exact_lengths_unchanged(self):
        bars = {1: [3.0, 3.0, 3.0], 2: [4.0, 4.0, 4.0]}
        self.assertEqual(rhythm._bar_run(bars, 0, 3.0), (1, 1))

    def test_bars_opinion_a_range_names_no_length_RED(self):
        bars = {c: [(1.0, 4.0)] * 3 for c in range(6)}
        with mock.patch.object(rhythm, "_bar_lengths_for", return_value=bars):
            got = rhythm._bars_opinion(None)
        self.assertEqual(got["state"], "no_assessable_bars")

    def test_bars_opinion_ranges_confirm_the_length_the_exact_bars_name(self):
        bars = {0: [3.0] * 3, 1: [3.0] * 3, 2: [3.0] * 3, 3: [(2.0, 3.5)] * 3, 4: [(4.0, 5.0)] * 3}
        with mock.patch.object(rhythm, "_bar_lengths_for", return_value=bars):
            got = rhythm._bars_opinion(None)
        self.assertEqual(got["state"], "named")
        self.assertEqual(got["length"], 3.0)
        self.assertEqual((got["bars_agree"], got["bars_disagree"]), (4, 0))


# ── EVALUATE: reconcile_duration ─────────────────────────────────────────────────────────────────────────────────────

def _fire(b, on, confirm="narrowed"):
    with _env(on, confirm):
        return b.fire()


def _over_bar():
    """2/4: a narrowed {8, 4} head, a decided quarter, a decided quarter rest. Over by an eighth or a quarter under every
    candidate ([2.5, 3.0]); the one decided move that brings 2.0 into range is the quarter -> an eighth (2.153b tile 8)."""
    b = _EvalBar(2, 4)
    n = b.narrowed()
    d = b.decided(1.0)
    b.decided(1.0, rest=True)
    return b, n, d


class TestReconcileDuration(unittest.TestCase):
    """Sean 2026-10-17, "Spilt it": under the flag a bar holding a narrowing gets NO move (the range-gated move was refused
    on his tiles, 2 of 7). RED if a move is wired back in, under 2.154 arm a or with 2.154 off."""

    def test_on_a_bar_over_under_every_candidate_still_moves_nothing_RED(self):
        b, n, d = _over_bar()
        log, out = _fire(b, on=True)
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 1.0)
        self.assertEqual(log.verdict(Q.DURATION, n).outcome, Outcome.NARROWED)

    def test_on_with_2_154_off_a_narrowed_bar_moves_nothing_RED(self):
        b, n, d = _over_bar()
        log, out = _fire(b, on=False, confirm="off")
        self.assertTrue(out)                        # CONTROL: 2.154 off and 2.162 off, the old pick/move fires
        b, n, d = _over_bar()
        log, out = _fire(b, on=True, confirm="off")
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 1.0)

    def _decided_bar(self):
        b = _EvalBar(2, 4)
        d = b.decided(1.0)
        b.decided(0.5, levels=1)
        b.decided(1.0, rest=True)
        return b, d

    def test_CONTROL_off_a_decided_note_in_a_bar_that_does_not_fit_is_moved(self):
        b, d = self._decided_bar()
        log, out = _fire(b, on=False)
        self.assertTrue(out)                        # flag OFF: the old bar-moves-a-decided-note behaviour (2.165's job)

    def test_on_the_bar_never_moves_a_DECIDED_note_RED(self):
        """Sean 2026-10-18 "2. Block" (CLAUDE section 4): a decided note in a restored-meter bar is not moved."""
        b, d = self._decided_bar()
        log, out = _fire(b, on=True)
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 1.0)


# ── EVALUATE: reinstate_rest_between_staves' bar total ───────────────────────────────────────────────────────────────

class TestTheRestReinstatementTotal(unittest.TestCase):

    def _bar(self):
        b = _EvalBar(2, 4)
        b.narrowed()
        b.decided(1.0)
        log, _meter = b.build()
        return log

    def test_CONTROL_off_the_narrowing_is_summed_at_its_first_candidate(self):
        with _env(False):
            self.assertEqual(consequences._bar_total_excluding(self._bar(), CELL, frozenset()), 1.5)

    def test_on_a_narrowed_bar_has_no_total_RED(self):
        with _env(True):
            self.assertIsNone(consequences._bar_total_excluding(self._bar(), CELL, frozenset()))


if __name__ == "__main__":
    unittest.main()
