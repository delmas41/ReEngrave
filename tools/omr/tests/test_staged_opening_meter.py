"""ROADMAP 2.12h — a system's OPENING meter is not the vote alone.

Brahms 1 / Breitkopf, whole-movement (`benchmarks/omr-shape-role-2026-09/
FINDINGS.md` §"2.12h"): `system/1/0` VOTES its opening unanimously (10 of 10
staves that spoke) at `9/4`, while the immediately preceding system's own
last cell corroborates a courtesy `9/8` at support 26.5 on 9 of 14 staves —
and a print crop of the header shows `9/8` engraved, not `9/4`. A-METER-5
already reads and records the cautionary (`value["cautionary"]`) with the
comment that consuming it "belongs with the carry"; nothing consumed it
until this item.

This reproduces the shape synthetically at fixture scale: a SOURCE system
whose own opening is read cleanly and whose last cell corroborates a
cautionary naming a DIFFERENT meter, followed immediately by a DESTINATION
system whose own vote disagrees with that cautionary. The fix reroutes the
disagreeing vote through the existing fallback ladder rather than asserting
it, so `_carry_meter` can weigh the cautionary against the destination's OWN
bars exactly as any other carry candidate — never a blind swap.

⚠️ RED-BEFORE: verified by monkeypatching `rhythm_mod._adjacent_corroborated_
cautionary` to always return `None` (the pre-2.12h shape, in which nothing
ever asked the question) — `test_the_fix_is_reachable_RED_without_it` below
does this directly, so the class does not depend on `git stash` or a second
checkout to prove the direction.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS

PAGE = 0


def _opening(log, sysj, num, den, raw=None, staves=None, n_staves=3):
    """Every staff of `sysj` (or just `staves`) votes `(num, den)` cleanly."""
    for st in (staves if staves is not None else range(n_staves)):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE,
                    (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7,
                    raw=raw or f"{num}/{den}")


def _cautionary_glyphs(log, sysj, staff_index, cell, num, den):
    """A complete stacked meter -- numerator over denominator -- on ONE
    staff, at `cell` (the system's own LAST cell, to read as a cautionary
    rather than a change; see `TestACautionaryIsNotAChange`)."""
    for digit, y in ((num, 10.0), (den, 30.0)):
        log.observe(R.staff(sysj.page, sysj.system, staff_index),
                    Q.METER_GLYPH, "timeSig%d" % digit,
                    reader=READERS.DETECTOR, frame="cell:%d" % cell,
                    score=0.9, cell=cell, x=10.0, y_center=y, letter=False)


def _staff_count(log, sysj, n_staves):
    log.record(adjudicate.Verdict(
        id=log._next_id("vrd"), subject=sysj,
        quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
        value=n_staves, decider="t", reason="counted"))


def _measure_partition(log, sysj, n_staves, n_cells):
    for st in range(n_staves):
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(sysj.page, sysj.system, st),
            quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
            value=n_cells, decider="t", reason="barlines"))


def _bars(log, sysj, n_staves, n_bars, beats):
    """`n_bars` bars, each with `n_staves` staves reading `beats` quarters --
    the shape `_bar_lengths_for` / `_corroborate` read (Q.EVENT grouping one
    glyph per cell, Q.DURATION on that glyph)."""
    for st in range(n_staves):
        for c in range(n_bars):
            cell = R.cell(sysj.page, sysj.system, st, c)
            g = R.glyph(sysj.page, sysj.system, st, c, 0)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 400, 0, 600, 16),
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                outcome=Outcome.DECIDED,
                value={"beats": beats, "written": beats,
                       "duration_type": "quarter", "dots": 0},
                decider="t", reason="head_and_marks"))
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                outcome=Outcome.DECIDED,
                value={"events": [{"glyphs": [0], "x": 500.0,
                                   "kind": "chord"}]},
                decider="t", reason="x_clustered"))


def _run(log):
    """Adjudicate METER over every system in document order, carry and the
    bars-derive-a-length rung (neither has a flag since 2026-10-07) -- isolating the carry/cautionary
    mechanism under test, the same discipline
    `TestAnUncorroboratedChangeIsNotCarriedOffItsSystem._run` already uses."""
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
        adjudicate.adjudicate_one(log, spec, sysj)


class TestAnOpeningThatDisagreesWithACorroboratedCautionaryIsRechecked(
        unittest.TestCase):
    """The Brahms shape: SOURCE reads `6/8` and corroborates a `9/8`
    cautionary at its last cell; DESTINATION (the very next system) votes
    `9/4` unanimously. Only the destination's OWN bars decide what happens
    next -- the cautionary is a CANDIDATE, never an answer handed down."""

    N_STAVES = 3

    def _sources(self, *, cautionary_staves=(0, 1), src_n_cells=7):
        """SOURCE = system/0/0, opens `6/8`, corroborates a `9/8` cautionary
        on `cautionary_staves` at its last cell (index `src_n_cells - 1`)."""
        log = Log()
        src = R.system(0, 0)
        _staff_count(log, src, self.N_STAVES)
        _measure_partition(log, src, self.N_STAVES, src_n_cells)
        _opening(log, src, 6, 8, n_staves=self.N_STAVES)
        for st in cautionary_staves:
            _cautionary_glyphs(log, src, st, src_n_cells - 1, 9, 8)
        return log, src

    def _destination(self, log, *, dst_num=9, dst_den=4, n_bars=0,
                     bar_beats=None):
        dst = R.system(1, 0)
        _staff_count(log, dst, self.N_STAVES)
        _opening(log, dst, dst_num, dst_den, n_staves=self.N_STAVES)
        if n_bars:
            _bars(log, dst, self.N_STAVES, n_bars, bar_beats)
        return dst

    # ── RED -> GREEN ─────────────────────────────────────────────────────

    def test_the_fix_is_reachable_RED_without_it(self):
        """⚠️ RED-BEFORE, proven without a second checkout: with the helper
        that finds the adjacent cautionary forced to answer `None` — exactly
        what every call site saw before this item — the destination simply
        asserts its own vote, `9/4`, unmoved by the cautionary. This is the
        bug this item fixes, reproduced as a live regression guard for the
        function this item adds rather than merely described in a docstring.
        """
        log, _src = self._sources()
        dst = self._destination(log, n_bars=2, bar_beats=4.5)
        with mock.patch.object(rhythm_mod, "_adjacent_corroborated_cautionary",
                               return_value=None):
            _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))

    def test_the_bars_confirm_the_cautionary_and_it_is_carried(self):
        """GREEN: the destination's own bars (2 bars of 4.5 quarters, three
        staves each) fit `9/8` and refuse `9/4`'s own would-be length (9.0),
        so the reroute lands on `carried`, not on an assertion of either
        witness by fiat."""
        log, _src = self._sources()
        dst = self._destination(log, n_bars=2, bar_beats=4.5)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 8))
        self.assertTrue((v.detail or {}).get("carried_via_cautionary"))

    def test_the_bars_can_still_REFUSE_the_cautionary(self):
        """⚠️ Rule 8: a fallback never converts "cannot tell" into an answer.
        The destination's own bars measure 2.0 quarters twice — neither the
        vote's `9/4` (9.0) nor the cautionary's `9/8` (4.5) — so the system
        ABSTAINS rather than asserting the courtesy signature on its own
        say-so. This is the control the fix must be able to FAIL: a
        mechanism that always adopts the cautionary would pass every other
        test here and this one only."""
        log, _src = self._sources()
        dst = self._destination(log, n_bars=2, bar_beats=2.0)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertNotEqual(v.reason, "voted")

    # ── controls: when the mechanism must NOT fire ──────────────────────

    def test_a_clean_opening_with_no_adjacent_cautionary_is_unaffected(self):
        """Positive control: no system precedes the destination at all, so
        there is nothing to be rechecked against — a plain, unanimous
        opening reads exactly as it always has."""
        log = Log()
        only = R.system(0, 0)
        _staff_count(log, only, self.N_STAVES)
        _opening(log, only, 4, 4, n_staves=self.N_STAVES)
        _run(log)
        v = log.verdict(Q.METER, only)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (4, 4))

    def test_an_opening_that_AGREES_with_the_cautionary_is_unaffected(self):
        """No disagreement, no reroute: the vote stands on its own terms even
        though a corroborated cautionary precedes it."""
        log, _src = self._sources()
        dst = self._destination(log, dst_num=9, dst_den=8)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 8))

    def test_an_UNCORROBORATED_cautionary_does_not_override_the_vote(self):
        """A courtesy signature only ONE staff read is not corroborated
        (`METER_CHANGE_MIN_STAVES = 2`, A-METER-6) and must not unsettle a
        vote it cannot itself stand behind."""
        log, _src = self._sources(cautionary_staves=(0,))
        dst = self._destination(log, n_bars=2, bar_beats=4.5)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))

    def test_a_cautionary_two_systems_back_does_not_apply(self):
        """⚠️ ADJACENCY, NOT "nearest system with a decided meter". A courtesy
        signature names the system directly after it and nothing farther.
        `middle` IS that system, so it AGREES with `src`'s cautionary (a
        second positive control, folded in: agreement means no reroute, so
        it decides by a plain vote too) and prints none of its own — so the
        system after `middle` must not be rechecked against a cautionary
        that was never printed for it."""
        log, src = self._sources()
        middle = R.system(0, 1)
        _staff_count(log, middle, self.N_STAVES)
        _opening(log, middle, 9, 8, n_staves=self.N_STAVES)
        dst = R.system(0, 2)
        _staff_count(log, dst, self.N_STAVES)
        _opening(log, dst, 9, 4, n_staves=self.N_STAVES)
        _run(log)
        mv = log.verdict(Q.METER, middle)
        self.assertIs(mv.outcome, Outcome.DECIDED)
        self.assertEqual(mv.reason, "voted")
        self.assertEqual((mv.value["numerator"], mv.value["denominator"]),
                         (9, 8))
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))


if __name__ == "__main__":
    unittest.main()
