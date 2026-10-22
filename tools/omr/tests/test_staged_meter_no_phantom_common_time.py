"""ROADMAP 2.12j — Brahms 1/i's residual 4/4: 3,234 of 4,494 held-out bars on
the 2026-09-28 whole-movement batch re-decision (2.12d + 2.12h already
applied) were STILL judged against a `4.0` the plate never prints outside one
9/8 bar at measure 8 (CLAUDE.md §10: "a meter is printed at a movement's
start and nowhere else").

Traced on the amended record (`.claude/worktrees/redecide-92b6ab04/
out-redecide/brahms/amended.record.json`, read once via
`record_io.load_record`; see `benchmarks/omr-shape-role-2026-09/FINDINGS.md`
PART 8 for the full table): the file's own `<time>` stays in force, per
part, until the next `<time>` it writes (`export._part_xml`'s own documented
design, ROADMAP 2.8 -- correct and UNCHANGED by this item). What poisons it
is upstream: ELEVEN systems (page/local `(2,0) (2,1) (3,0) (3,1) (9,1) (10,0)
(11,0) (12,0) (13,0) (15,0) (16,0)`) each carry a mid-system `Q.METER`
`change_only` segment reading `4/4`, DECIDED and CORROBORATED under
`METER_CHANGE_MIN_STAVES = 2` alone -- by just 2-4 of that system's 13-14
staves (7.7%-35.7% coverage) -- and EVERY ONE has `bars_fit: 0` on its own
bar math (several also have `bars_contradict` 1-2, i.e. the bars actively
DISAGREE). The staff-count corroboration and the bar-math confirmation are
TWO tests, and only the first one was actually load-bearing: `support` never
needs `bars_fit` to clear `METER_CHANGE_FLOOR` once 2 staves agree
(`2 * W_CHANGE_GLYPH_PAIR = 6.0 > 3.0`), so a candidate whose own bars
CONTRADICT it can still be decided -- a control that can never fail
(CLAUDE.md rule 7). 2.12d's own session flagged exactly this ("a
fraction-of-the-system threshold is visible... and is NOT this item's to
fix — flagged, not chased") and the legacy pipeline's own sibling guard,
`tools/omr/rhythm.py:631` `drop_uncorroborated_meter_changes`, already uses
`max(2, round(0.5 * n_staves))` -- cited as prior art, not imported (LEGACY
is frozen, CLAUDE.md §3).

The fix, in `tools/omr/staged/adjudicators/rhythm.py`
(`_required_corroboration`, `METER_CHANGE_COVERAGE_FLOOR = 0.5`): the SAME
`corroborated` flag `_meter_changes` already computed now requires
`max(METER_CHANGE_MIN_STAVES, round(0.5 * total_staves))` staves reading the
SAME meter, not the bare absolute floor of 2 -- `total_staves=None` (staff
count undecided) falls back to the unchanged absolute floor. This is
ADJUDICATE-only (no GATHER change, no re-gather needed) and touches nothing
export-side: `export._bar_quarters` already refuses to judge a bar against a
`4.0` fallback for an unknown meter (ROADMAP 2.8, shipped before this item —
test (c) below is a NEGATIVE-finding regression guard, not a fix).

RED first: (a) below fails on the tree before this item exactly as it would
on the real Brahms shape -- 2 of 14 staves clears `METER_CHANGE_MIN_STAVES`
alone and the phantom `4/4` stands, governing the system and everything a
carry hands it afterward.
"""

from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as export_mod
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests.test_staged_meter_system_agreement import (
    _MeterSystemFixture,
)


class TestAMinorityCorroboratedChangeOnALargeSystemIsDeclined(
        _MeterSystemFixture):
    """(a) The exact Brahms shape: a 13-14-staff system, a mid-system change
    only 2-4 staves read. `METER_CHANGE_MIN_STAVES = 2` alone treats this as
    "corroborated"; the proportional floor (2.12j) does not."""

    def test_the_fix_is_reachable_RED_without_it(self):
        """RED, verified by monkeypatching `_required_corroboration` back to
        the bare absolute floor it replaces -- exactly what
        `_meter_changes` computed at every call site before this item. Two
        of fourteen staves then clears `METER_CHANGE_MIN_STAVES` alone (this
        module's own `test_one_staff_of_twelve_reading_4_4_mid_movement_is_
        declined` already shows ONE staff is refused; TWO is exactly the
        floor 2.12d's own gate could not tell from real corroboration) and
        the phantom `4/4` stands as a segment."""
        log, sysj = self._log(
            n_staves=14, opening=(6, 8), opening_raw="6/8",
            change=(4, 4), change_staves={6, 8})
        with mock.patch.object(
                rhythm_mod, "_required_corroboration",
                side_effect=lambda total: rhythm_mod.METER_CHANGE_MIN_STAVES):
            v = self._run(log, sysj)
        self.assertEqual(self._segments(v), [(0, 6, 8), (4, 4, 4)])

    def test_two_of_fourteen_staves_no_longer_states_the_change(self):
        """GREEN: the same log, the fix live. `required = max(2, round(0.5 *
        14)) = 7`; 2 staves is 14.3% coverage, far under it, so the change is
        DECLINED -- never a segment, never able to overwrite `in_force`, and
        never a source a later carry could hand a phantom `4/4` onward from."""
        log, sysj = self._log(
            n_staves=14, opening=(6, 8), opening_raw="6/8",
            change=(4, 4), change_staves={6, 8})
        v = self._run(log, sysj)
        self.assertEqual(self._segments(v), [(0, 6, 8)])
        declined = (v.value or {}).get("declined_changes") or []
        self.assertEqual(len(declined), 1)
        self.assertEqual(declined[0]["declined_reason"],
                         rhythm_mod.METER_CHANGE_NOT_SYSTEM_WIDE)
        self.assertIs(declined[0]["corroborated"], False)
        self.assertEqual(declined[0]["staves_reading_it"], [6, 8])

    @staticmethod
    def _write_bars(log, page, system, cells, beats, n_staves):
        """Real bar-length evidence (`Q.EVENT` + `Q.DURATION`), the same
        shape `TestAnUncorroboratedChangeIsNotCarriedOffItsSystem._bars` uses
        in the sibling file -- `_MeterSystemFixture` itself deliberately
        writes none (its own docstring), so a test that needs the bars to
        speak adds them directly."""
        for st in range(n_staves):
            for c in cells:
                cell = R.cell(page, system, st, c)
                g = R.glyph(page, system, st, c, 0)
                log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.observe(g, Q.GLYPH_BOX,
                           ("noteheadBlack", 400, 0, 600, 16),
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

    def test_bars_that_actively_contradict_the_minority_reading_still_decline(
            self):
        """The Brahms shape more exactly: several of the eleven flagged
        systems have `bars_contradict` 1-2 on their own bar math, and the OLD
        rule accepted them anyway because `support` never had to clear the
        floor on bar evidence alone. This system's own bars (3 bars of 3.0
        quarters each, the `6/8` length, at and after the change's own cell)
        actively DISAGREE with the minority's `4/4` (4.0 quarters expected);
        the fix still declines on staff coverage, not on the bars racing to
        the rescue -- CLAUDE.md rule 7: a control that only ever happens to
        agree with a correct answer is not the control doing the work."""
        log, sysj = self._log(
            n_staves=14, opening=(6, 8), opening_raw="6/8",
            change=(4, 4), change_staves={6, 8})
        self._write_bars(log, sysj.page, sysj.system, (4, 5, 6), 3.0, 14)
        v = self._run(log, sysj)
        self.assertEqual(self._segments(v), [(0, 6, 8)])


class TestACorroboratedChangeOnALargeSystemStillGoverns(_MeterSystemFixture):
    """(b) The positive control the brief asks for: a mid-system change every
    staff of a large (14-staff) system reads still states the change --
    without this, (a)'s refusal would pass for a rule that refuses
    everything (CLAUDE.md §6b)."""

    def test_all_fourteen_staves_reading_3_4_states_the_change(self):
        log, sysj = self._log(
            n_staves=14, opening=(6, 8), opening_raw="6/8",
            change=(3, 4), change_staves=set(range(14)))
        v = self._run(log, sysj)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(self._segments(v), [(0, 6, 8), (4, 3, 4)])
        self.assertNotIn("declined_changes", v.value or {})

    def test_a_clear_majority_above_the_proportional_floor_also_governs(self):
        """Not unanimity -- `required = max(2, round(0.5 * 14)) = 7`; 8 of 14
        (57.1%) clears it, proving the fix asks for a majority-scale witness,
        not every last staff on the page (a bound this item's own module
        docstring names as the thing that would risk deleting real, lower-
        recall changes -- CLAUDE.md rule 3's own CONVENTION ASSUMED note on
        `METER_CHANGE_MIN_STAVES` applies here too and is NOT CONFIRMED WITH
        SEAN)."""
        log, sysj = self._log(
            n_staves=14, opening=(6, 8), opening_raw="6/8",
            change=(3, 4), change_staves=set(range(8)))
        v = self._run(log, sysj)
        self.assertEqual(self._segments(v), [(0, 6, 8), (4, 3, 4)])
        self.assertNotIn("declined_changes", v.value or {})

    def test_the_movement_start_meter_on_a_large_system_is_unaffected(self):
        """A second positive control: the OPENING vote (cell 0, the template
        reader) is a different code path entirely (`adjudicate_meter`'s
        `voted` branch, above `_meter_changes`) and this item's staff-count
        arithmetic does not touch it."""
        log, sysj = self._log(n_staves=14, opening=(6, 8), opening_raw="6/8")
        v = self._run(log, sysj)
        self.assertEqual(v.reason, "voted")
        self.assertEqual(
            (v.value["numerator"], v.value["denominator"]), (6, 8))


class TestExportNeverJudgesAnUnknownBarAgainstFour4(unittest.TestCase):
    """(c) The brief's third hypothesis -- an EXPORT-side `4.0` fallback
    judging a bar in place of an unread meter -- did NOT hold up. This is a
    NEGATIVE finding: `export._bar_quarters` already refuses the `4.0`
    fallback for a `None`/incomplete meter (ROADMAP 2.8, shipped before this
    item; see that function's own docstring: "AND ITS 4.0 FALLBACK IS
    REFUSED HERE"). These are regression guards for that already-correct
    behaviour, not a fix -- both pass unmodified on the tree before this
    item too, and are added here because the brief asked this exact question
    and the answer belongs on the record beside the real cause (a) fixes."""

    def test_bar_quarters_refuses_the_4_0_fallback_for_an_unknown_meter(self):
        self.assertIsNone(export_mod._bar_quarters(None))
        self.assertIsNone(export_mod._bar_quarters({}))
        self.assertIsNone(
            export_mod._bar_quarters({"numerator": None, "denominator": 4}))

    def test_bar_holds_out_never_judges_against_four_four_with_no_meter(self):
        """A bar of events that would FAIL a `4/4` judgement (3 quarters
        written, one voice) is UNASSESSABLE, not held out, when no meter has
        ever been declared -- `_bar_holds_out` returns `None` (rule 8: no
        meter, no verdict), never a `want_quarters: 4.0` refusal manufactured
        from nothing."""
        events = [{"kind": "chord",
                  "noteheads": [{"duration_beats": 3.0}]}]
        held = export_mod._bar_holds_out(events, None, divisions=4,
                                         meter=None)
        self.assertIsNone(held)
        # Positive control: the SAME bar, WITH a meter, correctly holds out
        # (proving the fixture is realistic and `_bar_holds_out` would have
        # caught this bar had a meter been known).
        held_with_meter = export_mod._bar_holds_out(
            events, None, divisions=4,
            meter={"numerator": 4, "denominator": 4})
        self.assertIsNotNone(held_with_meter)
        self.assertEqual(held_with_meter["want_quarters"], 4.0)


if __name__ == "__main__":
    unittest.main()
