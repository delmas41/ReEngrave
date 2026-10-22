"""ROADMAP 2.12l — a printed meter change's digits, boxed by the detector as
noteheads, must be REFUSED as noteheads and FILED as a witness that a change
is printed at that bar (value unread unless something reads it).

`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §15b/§16: on Breitkopf
317803 pdf p1, system/1/0 cell 1 prints a 6/8 change on ~13 of 14 staves and
the detector boxes both digits as `noteheadWhole*`/`noteheadBlack*`.
`Q.METER_GLYPH` (`timeSig*` classes only) never fires there, so the change
was read by nothing and the two boxes were written as real notes.

Two layers, matching the two halves of the item:

  1. `notehead_precision.adjudicate_notehead_is_not_a_notehead` — the
     REFUSAL (`TestIsAMeterDigit*`), a per-glyph decision backed by a
     cross-staff quorum (CLAUDE.md's own guard: a real chord that happens
     to repeat must not fire this).
  2. `rhythm._meter_digit_witness_cells` / `_meter_changes` / `_carry_meter`
     — the WITNESS (`TestTheWitnessIsFiled`, `TestTheCarryIsLabelled`),
     reading (1)'s verdict back and never setting a numerator/denominator
     from it alone (CLAUDE.md rule 6/8).

⚠️ RED-BEFORE: every test in `TestIsAMeterDigit*` fails on the unrepaired
tree with `AttributeError` (`notehead_precision.METER_DIGIT_REASON` and
`_is_a_meter_digit` do not exist) or a `Ruling(value=False, reason=
"notehead")` where a refusal is asserted; every test in
`TestTheWitnessIsFiled`/`TestTheCarryIsLabelled` fails with `AttributeError`
(`rhythm_mod.METER_CHANGE_DIGITS_MISREAD`/`_meter_digit_witness_cells` do
not exist) or a mismatched `declined_reason`/abstain `reason`.

⚠️ No test here reads module source text (CLAUDE.md rule 6c).
"""

from __future__ import annotations

import os
import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS

# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — the refusal (`notehead_precision`)
# ─────────────────────────────────────────────────────────────────────────────

SPACING = 100.0                       # one staff space, canonical px
CELL_BOX_PAGE = [500.0, 1000.0, 700.0, 1300.0]


def _cell_geometry(log, staff, cell, *, spacing=SPACING, cell_box=CELL_BOX_PAGE):
    c = R.cell(0, 0, staff, cell)
    log.observe(c, Q.CELL_STAFF_SPACE, spacing,
                reader=READERS.GEOMETRY, frame="cell:%d" % cell)
    log.observe(c, Q.CELL_BOX, list(cell_box),
                reader=READERS.GEOMETRY, frame="cell:%d" % cell)


def _notehead_box(log, staff, cell, gi, *, cls, x_c, y_c, w_c=140.0, h_c=100.0,
                  conf=0.4):
    g = R.glyph(0, 0, staff, cell, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:%d" % cell, score=conf,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
               frame="cell:%d" % cell, score=conf)
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR,
               frame="cell:%d" % cell, score=conf)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
               reader=READERS.GEOMETRY, frame="cell:%d" % cell)
    return g


#: Measured on the Breitkopf fixture (module docstring in
#: `notehead_precision.py`): x-gap 0.00-0.11 spaces, y-centre gap 0.42-0.86
#: spaces, both boxes within 0-2.2 spaces of the cell's own left edge.
PAIR_X_C = 150.0                      # 1.5 spaces from the cell's own edge
PAIR_TOP_Y = 250.0                    # centre = 3.0 spaces
PAIR_BOT_Y = 320.0                    # centre = 3.7 spaces -> gap 0.7 spaces


def _digit_pair(log, staff, cell, *, x_c=PAIR_X_C):
    """The two `notehead*`-classed boxes ONE staff's own meter-change digits
    are boxed as — a tight x, a narrow, specific y-gap."""
    _notehead_box(log, staff, cell, 0, cls="noteheadWholeInSpace",
                 x_c=x_c, y_c=PAIR_TOP_Y)
    _notehead_box(log, staff, cell, 1, cls="noteheadWholeOnLine",
                 x_c=x_c + 2.0, y_c=PAIR_BOT_Y)


def _single_note(log, staff, cell, *, x_c=PAIR_X_C, y_c=PAIR_TOP_Y):
    """One ordinary note near the cell's own left edge — no partner."""
    _notehead_box(log, staff, cell, 0, cls="noteheadWholeInSpace",
                 x_c=x_c, y_c=y_c)


def _wide_chord(log, staff, cell, *, x_c=PAIR_X_C):
    """A real two-note chord at the SAME x — a THIRD apart (2.0 spaces),
    well past the digit pair's own narrow 0.30-1.20 window."""
    _notehead_box(log, staff, cell, 0, cls="noteheadWholeInSpace",
                 x_c=x_c, y_c=200.0)
    _notehead_box(log, staff, cell, 1, cls="noteheadWholeOnLine",
                 x_c=x_c + 2.0, y_c=400.0)


def _staff_count(log, sysj, n_staves):
    log.record(adjudicate.Verdict(
        id=log._next_id("vrd"), subject=sysj,
        quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
        value=n_staves, decider="t", reason="counted"))


def _run_notehead(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


def _v(log, staff, cell, gi):
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, R.glyph(0, 0, staff, cell, gi))


class TestIsAMeterDigitFiresOnlyWithCrossStaffQuorum(unittest.TestCase):
    """10 staves; `_required_meter_digit_quorum(10) == 8` OTHER staves
    (ROADMAP 2.46 raised `METER_DIGIT_QUORUM_COVERAGE` 0.5 -> 0.8 --
    `round(0.8 * 10) == 8`), so 9 of 10 showing the pattern clears it and
    8 of 10 does not."""

    N_STAVES = 10

    def _system(self, log):
        sysj = R.system(0, 0)
        _staff_count(log, sysj, self.N_STAVES)
        for st in range(self.N_STAVES):
            _cell_geometry(log, st, 1)
        return sysj

    def test_RED_the_reason_exists_and_is_registered(self):
        """⚠️ Fails on the unrepaired tree: `METER_DIGIT_REASON` does not
        exist, and `"is_a_meter_digit"` is not a declared reason."""
        self.assertEqual(NP.METER_DIGIT_REASON, "is_a_meter_digit")
        self.assertIn(NP.METER_DIGIT_REASON,
                      adjudicate.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].reasons)

    def test_the_pair_repeated_on_every_staff_is_refused(self):
        log = Log()
        self._system(log)
        for st in range(self.N_STAVES):
            _digit_pair(log, st, 1)
        _run_notehead(log)
        for st in range(self.N_STAVES):
            for gi in (0, 1):
                v = _v(log, st, 1, gi)
                self.assertIs(v.value, True, f"staff {st} glyph {gi}")
                self.assertEqual(v.reason, "is_a_meter_digit")

    def test_the_pair_repeated_on_a_bare_quorum_is_refused(self):
        """9 of 10 staves (this candidate's own + 8 others) — exactly the
        floor `_required_meter_digit_quorum(10)` computes."""
        log = Log()
        self._system(log)
        for st in range(9):
            _digit_pair(log, st, 1)
        _run_notehead(log)
        v = _v(log, 0, 1, 0)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "is_a_meter_digit")

    # ── controls: a real chord must not be caught ──────────────────────────

    def test_CONTROL_a_lone_chord_on_ONE_staff_is_kept(self):
        """A real two-note hollow chord that does NOT repeat across the
        system — the shape/position gates alone are not enough to fire."""
        log = Log()
        self._system(log)
        _digit_pair(log, 0, 1)          # only staff 0 -- no repetition
        _run_notehead(log)
        v = _v(log, 0, 1, 0)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        # the signal was measured and recorded even though the rule did not
        # fire -- the same discipline `unladdered_signal` already keeps.
        self.assertIn("meter_digit_signal", v.detail)

    def test_CONTROL_below_quorum_is_kept(self):
        """8 of 10 staves (this one's own + 7 others) — one short of the
        floor of 8 OTHER staves. This is the EXACT real-world shape ROADMAP
        2.46 measured and print-verified as a false positive: two whole-
        movement Brahms cells showed this pattern on 8 of 14 staves (0.571
        coverage) with no printed meter change at all -- see the block
        comment above `METER_DIGIT_QUORUM_COVERAGE`."""
        log = Log()
        self._system(log)
        for st in range(8):
            _digit_pair(log, st, 1)
        _run_notehead(log)
        v = _v(log, 0, 1, 0)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_CONTROL_tutti_whole_notes_with_no_partner_are_kept(self):
        """A tutti whole-note entrance repeated on every staff — ONE note
        per staff, no stacked partner, so there is no pair to test at all."""
        log = Log()
        self._system(log)
        for st in range(self.N_STAVES):
            _single_note(log, st, 1)
        _run_notehead(log)
        for st in range(self.N_STAVES):
            v = _v(log, st, 1, 0)
            self.assertIs(v.value, False)
            self.assertEqual(v.reason, "notehead")

    def test_CONTROL_a_wide_repeated_chord_is_kept(self):
        """A real chord interval (a third, 2.0 spaces) repeated on every
        staff — the cross-staff repetition alone is not enough either; the
        y-gap must ALSO fall in the digit pair's own narrow window."""
        log = Log()
        self._system(log)
        for st in range(self.N_STAVES):
            _wide_chord(log, st, 1)
        _run_notehead(log)
        for st in range(self.N_STAVES):
            v = _v(log, st, 1, 0)
            self.assertIs(v.value, False)
            self.assertEqual(v.reason, "notehead")

    def test_CONTROL_far_from_the_barline_is_kept(self):
        """The SAME pair shape, but standing 6 spaces from the cell's own
        left edge — nowhere near a barline, so it does not enter the
        candidate population at all."""
        log = Log()
        self._system(log)
        for st in range(self.N_STAVES):
            _digit_pair(log, st, 1, x_c=600.0)
        _run_notehead(log)
        for st in range(self.N_STAVES):
            v = _v(log, st, 1, 0)
            self.assertIs(v.value, False)
            self.assertEqual(v.reason, "notehead")


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — the witness (`rhythm.py`)
# ─────────────────────────────────────────────────────────────────────────────

N_STAVES = 4                          # `_required_corroboration(4) == 2`


def _opening(log, sysj, num, den, *, n_staves=N_STAVES):
    for st in range(n_staves):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE,
                    (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7, raw=f"{num}/{den}")


def _measure_partition(log, sysj, n_staves, n_cells):
    for st in range(n_staves):
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(sysj.page, sysj.system, st),
            quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
            value=n_cells, decider="t", reason="barlines"))


def _bars(log, sysj, n_staves, n_bars, beats, *, first_cell=0):
    for st in range(n_staves):
        for c in range(first_cell, first_cell + n_bars):
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


def _digit_witness_verdicts(log, sysj, cell, staves):
    """The FIRST layer's own output, injected directly — this layer is
    tested against the FACT the refusal leaves on the record, not against
    the refusal's own geometry (that is `TestIsAMeterDigit*`'s job).

    ⚠️ `_meter_digit_witness_cells` finds its CANDIDATES from `Q.GLYPH_BOX`/
    `Q.CELL_STAFF_SPACE` (a cheap, broad-scan-safe pre-filter — see that
    function's own comment) and only THEN confirms the survivors against
    THIS verdict by exact subject. So the fixture must supply a near-
    barline box for the pre-filter to find, or the verdict below — however
    real — is never even asked about."""
    for st in staves:
        g = R.glyph(sysj.page, sysj.system, st, cell, 0)
        c = R.cell(sysj.page, sysj.system, st, cell)
        log.observe(c, Q.CELL_STAFF_SPACE, SPACING, reader=READERS.GEOMETRY,
                    frame="cell:%d" % cell)
        log.observe(g, Q.GLYPH_BOX,
                    ("noteheadWholeInSpace", PAIR_X_C, PAIR_TOP_Y, 140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:%d" % cell,
                    score=0.4, category="notehead")
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=g,
            quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, outcome=Outcome.DECIDED,
            value=True, decider="t", reason=NP.METER_DIGIT_REASON))


def _run(log):
    """Adjudicate METER over every system in document order (the carry has no flag since 2026-10-07) —
    `test_staged_meter_return_not_read.py`'s own discipline."""
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
        adjudicate.adjudicate_one(log, spec, sysj)


def _source(*, witness_staves, src_n_cells=3):
    """SOURCE = system(0, 0): votes `9/4` (the Breitkopf header misread) and
    carries an UNREAD digit-witness change at cell 1 -- `Q.METER_GLYPH`
    never fires there (nothing here builds one; that IS the fixture)."""
    log = Log()
    src = R.system(0, 0)
    _staff_count(log, src, N_STAVES)
    _measure_partition(log, src, N_STAVES, src_n_cells)
    _opening(log, src, 9, 4)
    _digit_witness_verdicts(log, src, 1, witness_staves)
    return log, src


def _destination(log, *, n_cells=3, bar_beats=3.0):
    """DESTINATION = system(1, 0): no vote of its own; its bars from cell 1
    onward (6/8-worth each) contradict the carried `9/4`."""
    dst = R.system(1, 0)
    _staff_count(log, dst, N_STAVES)
    _measure_partition(log, dst, N_STAVES, n_cells)
    _bars(log, dst, N_STAVES, n_cells - 1, bar_beats, first_cell=1)
    return dst


class TestTheWitnessIsFiled(unittest.TestCase):
    """Layer 1's refusal, read back as a fact on the SOURCE's own `Q.METER`
    verdict — never a value, only a place (CLAUDE.md rule 8)."""

    def test_RED_the_reason_and_constant_exist(self):
        self.assertEqual(rhythm_mod.METER_CHANGE_DIGITS_MISREAD,
                         "meter_change_digits_misread")
        self.assertIn(rhythm_mod.METER_CHANGE_DIGITS_MISREAD,
                      adjudicate.REGISTRY[Q.METER].reasons)

    def test_a_quorum_witness_is_filed_declined_with_no_value(self):
        log, src = _source(witness_staves=(0, 1, 2))     # 3 of 4
        _run(log)
        v = log.verdict(Q.METER, src)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")               # the vote itself stands
        declined = v.value.get("declined_changes") or []
        hits = [c for c in declined
               if c.get("declined_reason") == rhythm_mod.METER_CHANGE_DIGITS_MISREAD]
        self.assertEqual(len(hits), 1)
        entry = hits[0]
        self.assertEqual(entry["from_cell"], 1)
        self.assertIsNone(entry["numerator"])              # never a value
        self.assertIsNone(entry["denominator"])
        self.assertEqual(sorted(entry["staves_with_digit_witness"]), [0, 1, 2])
        # ⚠️ the ACCEPTED opening is untouched -- a witness never overwrites
        # `in_force`, only ADJUDICATE's own read of the digits could.
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))

    def test_CONTROL_below_quorum_files_nothing(self):
        log, src = _source(witness_staves=(0,))          # 1 of 4 -- under floor
        _run(log)
        v = log.verdict(Q.METER, src)
        declined = v.value.get("declined_changes") or []
        hits = [c for c in declined
               if c.get("declined_reason") == rhythm_mod.METER_CHANGE_DIGITS_MISREAD]
        self.assertEqual(hits, [])

    def test_CONTROL_a_cell_with_a_real_reading_is_never_overridden(self):
        """A REAL (if uncorroborated) `Q.METER_GLYPH` reading at the SAME
        cell must win the normal path, never be shadowed by the witness."""
        log, src = _source(witness_staves=(0, 1, 2))
        log.observe(R.staff(src.page, src.system, 0), Q.METER_GLYPH,
                    "timeSig6", reader=READERS.DETECTOR, frame="cell:1",
                    score=0.9, cell=1, x=10.0, y_center=10.0, letter=False)
        log.observe(R.staff(src.page, src.system, 0), Q.METER_GLYPH,
                    "timeSig8", reader=READERS.DETECTOR, frame="cell:1",
                    score=0.9, cell=1, x=10.0, y_center=30.0, letter=False)
        _run(log)
        v = log.verdict(Q.METER, src)
        declined = v.value.get("declined_changes") or []
        digit_hits = [c for c in declined if c.get("declined_reason")
                     == rhythm_mod.METER_CHANGE_DIGITS_MISREAD]
        # the real (if lone-staff) reading takes the `not_system_wide` path;
        # the witness-only entry this item adds must not ALSO appear for a
        # cell the main loop already visited.
        self.assertEqual(digit_hits, [])


class TestTheCarryIsLabelled(unittest.TestCase):
    """`_carry_meter` reads `src`'s own recorded witness back and relabels
    the generic refusal -- never a second query, never a value."""

    def test_the_overturned_carry_is_labelled_digits_misread(self):
        log, src = _source(witness_staves=(0, 1, 2))
        dst = _destination(log, bar_beats=3.0)             # 6/8-worth, not 9/4
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, rhythm_mod.METER_CHANGE_DIGITS_MISREAD)
        self.assertEqual(v.detail["digit_misread_at_cell"], 1)

    def test_too_few_bars_to_check_is_the_SAME_label(self):
        log, src = _source(witness_staves=(0, 1, 2))
        dst = R.system(1, 0)
        _staff_count(log, dst, N_STAVES)
        _measure_partition(log, dst, N_STAVES, 3)
        # no `_bars` at all -- nothing assessable
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, rhythm_mod.METER_CHANGE_DIGITS_MISREAD)
        self.assertEqual(v.detail["digit_misread_at_cell"], 1)

    def test_CONTROL_bars_that_FIT_the_carry_are_unlabelled(self):
        """Control: the carried `9/4` is CONFIRMED by the destination's own
        bars (9.0 quarters each) -- no refusal, no label, regardless of the
        witness sitting on the source."""
        log, src = _source(witness_staves=(0, 1, 2))
        dst = _destination(log, bar_beats=9.0)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))

    def test_CONTROL_no_witness_on_the_source_is_the_generic_label(self):
        """Control: the SAME overturned carry, but the source printed no
        digit-witness change at all -- the generic reason must stand."""
        log, src = _source(witness_staves=())              # no witness
        dst = _destination(log, bar_beats=3.0)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_outweighed_by_the_bars")

    def test_CONTROL_below_quorum_witness_is_the_generic_label_too(self):
        log, src = _source(witness_staves=(0,))            # under the floor
        dst = _destination(log, bar_beats=3.0)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_outweighed_by_the_bars")

    # ── ROADMAP 2.46: a source's witness is WEIGHED, never a standing veto ──

    def test_ONE_clean_agreeing_bar_is_no_longer_vetoed_by_a_stale_witness(self):
        """⚠️ RED-BEFORE (`git stash` the `clean_here` gate in
        `rhythm._carry_meter`): a destination with exactly ONE assessable
        bar -- below `METER_CARRY_MIN_BARS` so `_corroborate` returns
        `"too_few_assessable_bars"` -- that bar agrees with the carried 9/4
        1-for-1 (`bars_agree: 1, bars_disagree: 0`), the SAME shape measured
        on the real Brahms record (`system/1/1`, `system/6/0`,
        `benchmarks/omr-meter-digits-2026-09/FINDINGS.md` ROADMAP 2.46) —
        before the fix this was abstained `meter_change_digits_misread`
        citing the SOURCE's own witness regardless; CLAUDE.md §10 says the
        carry is weighed by the bars, not gated, and one clean agreeing bar
        is exactly 2.22b's own `carried_uncontested` case."""
        log, src = _source(witness_staves=(0, 1, 2))       # a real witness
        dst = _destination(log, n_cells=2, bar_beats=9.0)   # ONE bar, 9/4-worth
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, rhythm_mod.METER_CARRIED_UNCONTESTED)
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 4))

    def test_CONTROL_one_bar_that_DISAGREES_still_abstains_digits_misread(self):
        """Control for the same gate: ONE assessable bar that does NOT
        match the carry (`bars_agree: 0, bars_disagree: 1`) is not "clean"
        and must still be labelled by the source's witness — the gate only
        widens the CLEAN case, it never loosens the disagreeing one."""
        log, src = _source(witness_staves=(0, 1, 2))
        dst = _destination(log, n_cells=2, bar_beats=3.0)   # ONE bar, 6/8-worth
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, rhythm_mod.METER_CHANGE_DIGITS_MISREAD)
        self.assertEqual(v.detail["digit_misread_at_cell"], 1)


if __name__ == "__main__":
    unittest.main()
