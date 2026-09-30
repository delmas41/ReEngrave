"""ROADMAP 2.44 (not built here) -- positions above/below the staff need to
be read from the PRINTED LEDGER LINES, not extrapolated from the staff's own
spacing.

Sean confirmed (relay, 2026-09-30) both Litolff p3 flute chords
(`glyph/3/0/0/2/4`+`/9` and `/1`+`/3`) print as **F6 over D6**. Manager
review measured WHY the pipeline does not reliably produce that: printed
ledger lines are not evenly spaced (Litolff p3 staff/3/0/0's own ledgers sit
431.5/418.5/398.5 page px apart -- gaps 18/13/20 -- against a 15.75 px staff
spacing; extrapolating the staff's own spacing is ~4 px off by the third
ledger). ROADMAP 2.42 tried two fixes (a whole-group ink fit, then a
same-side-second rounding-residual rule) and BOTH were withdrawn -- neither
addresses the real cause. 2.44 will read positions from the ledgers
themselves; until then these are pinned XFAIL so 2.44 can flip them, not
silently left unasserted.

⚠️ `/1`+`/3`'s own raw rounded positions already happen to land 2 apart (a
third) under plain `Q.NOTEHEAD_STAFF_POSITION` rounding, so THIS test may
already pass by coincidence on some records -- it is marked `xfail` anyway,
per instruction, because the mechanism that would GUARANTEE it (reading the
real ledgers) does not exist yet; `/2/4`+`/9` is the pair KNOWN to fail
(raw rounding gives F6/E6, a second).

⚠️ ROADMAP 2.44 LANDED 2026-09-30 (`gather.gather_ledger_printed_position`,
`Q.LEDGER_PRINTED_POSITION`, `consequences.restate_pitch`'s substitution).
The first test below is FLIPPED to a real, non-xfail assertion: a real
one-page A/B (`--through evaluate --weights auto` against the real Litolff
PDF) measured this reader's OWN actual `Q.LEDGER_PRINTED_POSITION` reading
for these exact two subjects (-3 for `/2/4`, -5 for `/2/9`), reproduced here
as the fixture rather than hand-picked, and the final decided pitches are
F6/D6 exactly as Sean confirmed -- `/2/9`'s own reading is a genuine
measured substitution (within the rule's one-step bound); `/2/4`'s own
ledger reading (-3) disagrees with the staff's extrapolated rounding (-7) by
FOUR steps, so the substitution declines (CLAUDE.md rule 8) and the
correct F6 stands from the extrapolated reading, unom-touched -- the
disagreement guard, not a correct ledger measurement, is what keeps `/2/4`
right, untouched (see
`benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §10).

The second test stays XFAIL: the real gather ALSO measured this reader's
own ledger reading for `/2/1` and `/2/3` as -3 for both (the same Litolff
merging-plate scan limitation as `/2/4` above -- a chord sharing fused ink
with a neighbour on this MERGING plate, CLAUDE.md §10), which disagrees
with both subjects' own extrapolated roundings by more than one step. The
final pitches are STILL correct (protected by the same conflict guard), but
that is exactly the "passes by coincidence, not by a genuine ledger
reading" shape this test was written to refuse to certify -- so it is
pinned XFAIL for the same reason as before, now for a MEASURED reason
rather than an anticipated one.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import record as R
from tools.omr.staged.record import Kind, Log, Outcome, Q, READERS, Verdict
from tools.omr.staged import consequences
from tools.omr.tests.test_staged_notehead_precision import (
    _cell_geometry, _notehead)

STAFF = R.staff(0, 0, 0)


def _clef(log, staff, name="treble"):
    v = Verdict(id=log._next_id("vrd"), subject=staff, quantity=Q.CLEF,
               outcome=Outcome.DECIDED, value=name, decider="test",
               reason="test", considered=(), basis=())
    return log.record(v)


def _ledger_row(log, g, value, bracket):
    """The real `Q.LEDGER_PRINTED_POSITION` reading this reader measured
    for this exact subject on the real Litolff p3 A/B, reproduced as a
    fixture rather than re-run against the PDF here (CLAUDE.md 2026-09-29:
    microscopic tests, not pricing runs)."""
    log.observe(g, Q.LEDGER_PRINTED_POSITION, value,
               reader=READERS.CV_LEDGER, frame="cell:0", bracket=bracket)


class TestLedgerPositionBuilt(unittest.TestCase):
    """Pinned to Sean's confirmed print reading. ROADMAP 2.44's own reader
    is now real data here, not a hand-picked value -- see the module
    docstring for the exact one-page A/B this was measured on."""

    def test_glyph_3_0_0_2_4_and_9_are_f6_over_d6(self):
        """Real Litolff p3 positions (-7.4, -5.56): raw rounding gives
        F6/E6 (a second) -- the confirmed print is F6/D6 (a third). The
        lower head (`/2/9`) is fixed by a genuine ledger substitution
        (measured -5, agrees with -6 within the 1-step bound -> D6); the
        upper head (`/2/4`) keeps its ALREADY-correct extrapolated F6
        because its own ledger reading (-3) disagrees by 4 steps and the
        substitution declines, per the conflict guard."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-7.4)
        lower = _notehead(log, 1, cls="noteheadHalfInSpace", pos_float=-5.56)
        _ledger_row(log, upper, -3, "beyond")
        _ledger_row(log, lower, -5, "beyond")
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "F6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "D6")
        self.assertEqual(log.verdict(Q.PITCH, lower).reason,
                        "position_and_clef_ledger")
        self.assertEqual(log.verdict(Q.PITCH, upper).reason,
                        "position_and_clef_ledger_conflict")

    @unittest.expectedFailure
    def test_glyph_3_0_0_2_1_and_3_are_f6_over_d6(self):
        """Real Litolff p3 positions (-6.88, -4.64) -- ALSO confirmed F6/D6.
        MEASURED on the real A/B: this reader's own ledger reading for BOTH
        subjects is -3 (the same Litolff merging-plate scan limitation as
        `/2/4` above), which disagrees with both extrapolated roundings by
        more than one step -- so BOTH substitutions decline and the final
        pitches are correct only via the pre-existing coincidence of plain
        rounding, protected by the conflict guard, never a genuine ledger
        reading here. Pinned XFAIL for exactly that reason, same as before
        2.44 existed -- now a MEASURED limitation, not an anticipated one."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        lower = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=-4.64)
        _ledger_row(log, upper, -3, "beyond")
        _ledger_row(log, lower, -3, "beyond")
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "F6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "D6")
        self.assertEqual(log.verdict(Q.PITCH, upper).reason,
                        "position_and_clef_ledger_conflict")
        self.assertEqual(log.verdict(Q.PITCH, lower).reason,
                        "position_and_clef_ledger_conflict")
        # Force the xfail regardless of the coincidental rounding above --
        # the GUARANTEE this pins (a genuine ledger reading, not a
        # conflict-guard coincidence) does not exist for THIS chord.
        raise AssertionError(
            "passes by coincidence of rounding + the conflict guard only -- "
            "this reader's own ledger measurement here is wrong")


if __name__ == "__main__":
    unittest.main()
