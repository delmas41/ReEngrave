"""ROADMAP 2.12d — a mid-staff `timeSig*` box states a meter only where the
system agrees.

Diagnosis, not restated here: `benchmarks/omr-bar-sum-holdout-2026-09/
FINDINGS.md` §13 ("the funnel"), measured on a fresh whole-movement Breitkopf
Brahms 1/i gather (`c19cbca7`). 91.4% of every bar 2.8 holds out is judged
against a `4.0` the plate never prints outside one 9/8 bar at measure 8, and
859 of those bars' OWN readings already sum to the TRUE meter — thrown away
because a lone-staff mid-system `timeSig*` reading was enough, on its own, to
overwrite `in_force` for the rest of its system. `system/1/1` is the named
case: support 3.0 from ONE staff, `bars_contradict: 1` — the bars themselves
disagreeing with the reading — and it still governed the system, because
rule (1) ("a change governs its own system") asked nothing but
`METER_CHANGE_FLOOR`; only rule (2) ("may be carried off it", A-METER-6) was
gated on `METER_CHANGE_MIN_STAVES`.

The fix, in `tools/omr/staged/adjudicators/rhythm.py`: the SAME
`METER_CHANGE_MIN_STAVES` corroboration now gates rule (1) too
(`METER_CHANGE_GATES_OWN_SYSTEM`, that constant's own note has the full
reasoning and the numbers). A candidate that clears `METER_CHANGE_FLOOR` but
not the staff count is DECLINED — filed under `METER_CHANGE_NOT_SYSTEM_WIDE`
in `declined_changes`, never in `segments` — so the meter in force is
unchanged and the reading is not silently dropped.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: CLAUDE.md §10's
"a key change is printed at one bar on every staff of the system" is taken to
hold for a METER change too, exactly as `key_signature_corroboration` already
takes it for keys. It would be FALSIFIED by a genuine printed meter change
this gate declines only because the system's OTHER staves were never
detected at that bar (a coverage failure dressed as a disagreement) — which
is the risk A-METER-6 priced against Litolff p.62 (one staff of seventeen)
and which this item's own tests below reproduce and then reverse, on the
strength of the Brahms evidence. NOT CONFIRMED WITH SEAN; print crops are cut
under `benchmarks/omr-shape-role-2026-09/out/print/m212d-*` for his read.

RED first: every test below fails on the tree before this item (a lone
reading clearing `METER_CHANGE_FLOOR` was, until now, a change). Setting
`rhythm.METER_CHANGE_GATES_OWN_SYSTEM = False` — a plain module constant,
never a new `OMR_*` flag (CLAUDE.md: no new flag without a roadmap item) —
reproduces that tree exactly and is the "base" a pricing arm runs without
touching any other constant.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS


class _MeterSystemFixture(unittest.TestCase):
    """One system, `n_staves` staves, each reading `opening` at its header
    window, with an optional mid-system CHANGE printed on `change_staves`.

    ⚠️ POSITION, NOT CLASS NAME, DISAMBIGUATES NUMERATOR FROM DENOMINATOR:
    `y=10.0` for the printed TOP digit, `y=30.0` for the bottom one,
    regardless of what the two digits ARE (`_meter_from_digits` sorts by
    `y_center` and calls the smaller one the numerator) — a sibling fixture
    in `test_staged_header_rhythm.py` disambiguates by class-name suffix
    instead, which cannot express a `4/4` (two IDENTICAL digit classes), and
    a spurious `4/4` misread is exactly this funnel's dominant shape.

    ⚠️ NO BAR-LENGTH EVIDENCE IS WRITTEN (no `Q.DURATION`/`Q.EVENT` rows),
    matching `TestACautionaryIsNotAChange`'s own default `bar_beats={}` in
    the sibling file: `_bar_run` then examines nothing, so a candidate's
    SUPPORT is exactly its glyph term and nothing here can be confused with
    the bar-math question `TestAChangeIsAgainstTheMeterInFORCE` already
    covers there — these tests isolate the AGREEMENT axis on its own.
    """

    def _log(self, *, n_staves, opening, opening_raw, change=None,
             change_staves=None, change_cell=4, n_cells=None):
        """`change` is `(numerator, denominator)` printed at `change_cell` on
        `change_staves` (default: every staff). `n_cells`, if given, is
        written as `Q.MEASURE_PARTITION` on every staff — the only way a
        change can be read as a CAUTIONARY (A-METER-5); omitted (the
        default), a change is an ordinary mid-system one."""
        log = Log()
        sysj = R.system(0, 0)
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=sysj,
            quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
            value=n_staves, decider="t", reason="counted"))
        for st in range(n_staves):
            log.observe(R.staff(0, 0, st), Q.METER_TEMPLATE, opening,
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw=opening_raw)
            if n_cells is not None:
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=R.staff(0, 0, st),
                    quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
                    value=n_cells, decider="t", reason="barlines"))
            if change is not None and (change_staves is None
                                        or st in change_staves):
                num, den = change
                for digit, y in ((num, 10.0), (den, 30.0)):
                    log.observe(R.staff(0, 0, st), Q.METER_GLYPH,
                                "timeSig%d" % digit, reader=READERS.DETECTOR,
                                frame="cell:%d" % change_cell, score=0.9,
                                cell=change_cell, x=10.0, y_center=y,
                                letter=False)
        return log, sysj

    def _run(self, log, sysj):
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.METER], sysj)
        return log.verdict(Q.METER, sysj)

    def _segments(self, v):
        return [(s.get("from_cell"), s.get("numerator"), s.get("denominator"))
                for s in ((v.value or {}).get("segments") or [])]


class TestAMidStaffChangeNeedsSystemAgreement(_MeterSystemFixture):
    """ROADMAP 2.12d. See module docstring and `rhythm.
    METER_CHANGE_GATES_OWN_SYSTEM`'s own note for the full reasoning."""

    def test_one_staff_of_twelve_reading_4_4_mid_movement_is_declined(self):
        """RED on the tree before 2.12d: there the lone staff's `4/4` alone
        clears `METER_CHANGE_FLOOR` and becomes the system's meter from that
        bar on. GREEN after: the system stays in `6/8`, and the refused
        candidate is recorded, not silently dropped."""
        log, sysj = self._log(
            n_staves=12, opening=(6, 8), opening_raw="6/8",
            change=(4, 4), change_staves={7})
        v = self._run(log, sysj)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(self._segments(v), [(0, 6, 8)])
        # `meter_at` — how a bar's meter is READ — answers `6/8` past the
        # declined bar too: the lone-staff `4/4` never became a segment.
        self.assertEqual(R.meter_at(v.value, 10)["raw"], "6/8")
        declined = (v.value or {}).get("declined_changes") or []
        self.assertEqual(len(declined), 1)
        self.assertEqual(declined[0]["declined_reason"],
                         rhythm_mod.METER_CHANGE_NOT_SYSTEM_WIDE)
        self.assertEqual(declined[0]["staves_reading_it"], [7])
        self.assertEqual(
            (declined[0]["numerator"], declined[0]["denominator"]), (4, 4))
        self.assertIs(declined[0]["corroborated"], False)

    def test_all_staves_of_a_system_reading_3_4_states_the_change(self):
        """The positive control named in the brief: with every staff of the
        system agreeing at the SAME column, the change IS stated — without
        this, the refusal above would pass for a rule that refuses
        everything, which is exactly the failure mode CLAUDE.md §6b warns a
        refusal test must rule out."""
        log, sysj = self._log(
            n_staves=12, opening=(6, 8), opening_raw="6/8",
            change=(3, 4), change_staves=set(range(12)))
        v = self._run(log, sysj)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(self._segments(v), [(0, 6, 8), (4, 3, 4)])
        self.assertEqual(R.meter_at(v.value, 5)["raw"], "3/4")
        self.assertNotIn("declined_changes", v.value or {})

    def test_a_cautionary_meter_past_the_last_barline_governs_no_bar(self):
        """A-METER-5, asserted here too as the brief's own regression guard
        alongside the new rule: a courtesy signature after the system's OWN
        last barline states the NEXT system's meter, not this one's — even
        when EVERY staff prints it, which rules out 2.12d's new gate as the
        reason it does not become a segment."""
        log, sysj = self._log(
            n_staves=12, opening=(6, 8), opening_raw="6/8",
            change=(9, 8), change_staves=set(range(12)),
            change_cell=6, n_cells=7)      # cell 6 is every staff's LAST
        v = self._run(log, sysj)
        self.assertEqual(self._segments(v), [(0, 6, 8)])
        cautionary = (v.value or {}).get("cautionary")
        self.assertIsNotNone(cautionary)
        self.assertEqual(
            (cautionary["numerator"], cautionary["denominator"]), (9, 8))
        self.assertTrue(cautionary["cautionary"])
        self.assertNotIn("declined_changes", v.value or {})

    def test_the_movement_start_meter_is_read_as_before(self):
        """The positive control: 2.12d only touches a MID-system change; the
        OPENING — cell 0, the template reader's own vote — is a different
        code path (`adjudicate_meter`'s `voted` branch, above
        `_meter_changes` entirely) and this item does not touch it."""
        log, sysj = self._log(
            n_staves=12, opening=(6, 8), opening_raw="6/8")
        v = self._run(log, sysj)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual(
            (v.value["numerator"], v.value["denominator"]), (6, 8))
        self.assertEqual(self._segments(v), [(0, 6, 8)])


if __name__ == "__main__":
    unittest.main()
