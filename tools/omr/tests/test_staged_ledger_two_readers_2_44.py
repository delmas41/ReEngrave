"""ROADMAP 2.44 (Sean's option B, DECISIONS 2026-09-30): a notehead OUTSIDE
its staff takes its position from geometry (today's `Q.NOTEHEAD_STAFF_
POSITION` rounding) UNLESS two INDEPENDENT ledger readers -- Sean's own
count-the-clean-ledgers rule (`Q.LEDGER_CLEAN_COUNT_POSITION`) and
`ledger_grid.measure_ledger_rungs` (`Q.LEDGER_RUNG_GRID_POSITION`) -- AGREE
on a different one. Where they disagree, or either abstains, geometry
stands and the case is counted (CLAUDE.md rule 8).

These tests exercise `consequences.restate_pitch` directly against fixture
ROWS (the real GATHER scan machinery is proved separately, against real
Litolff/Breitkopf rasters, by the acceptance re-gather and the print check
in FINDINGS -- CLAUDE.md §6b: initial tests compare GATHER+ADJUDICATE, plus
EVALUATE here because pitch is the point).

Real Litolff p3 numbers (`glyph/3/0/0/2/4`+`/9`, `/1`+`/3`), the raw
`Q.NOTEHEAD_STAFF_POSITION` floats measured on the committed record and
Sean's confirmed print reading (DECISIONS 2026-09-30, "The first chord is D
and F and the second chord is C and E" -- i.e. F6/D6 and E6/C6):

  * chord 1 upper -7.4  (rounds to -7 = F6, ALREADY RIGHT by geometry)
  * chord 1 lower -5.56 (rounds to -6 = E6, WRONG -- print is D6 = -5)
  * chord 2 upper -6.88 (rounds to -7 = F6, WRONG -- print is E6 = -6)
  * chord 2 lower -4.64 (rounds to -5 = D6, WRONG -- print is C6 = -4)

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


def _ledger_rows(log, g, *, clean=None, grid=None):
    """File reader-1 (`clean`) and/or reader-2 (`grid`) rows for `g`, in
    `Q.NOTEHEAD_STAFF_POSITION`'s own top-line-origin half-step units.
    `None` means that reader abstained (no row at all -- `State.DECLINED`,
    not a value)."""
    if clean is not None:
        log.observe(g, Q.LEDGER_CLEAN_COUNT_POSITION, clean,
                    reader=READERS.LEDGER_CLEAN_COUNT, frame="cell:0")
    if grid is not None:
        log.observe(g, Q.LEDGER_RUNG_GRID_POSITION, grid,
                    reader=READERS.LEDGER_RUNG_GRID, frame="cell:0")


class TestLedgerAgreementSetsPitch(unittest.TestCase):
    """Both readers agree on a position geometry rounded differently ->
    their shared position wins, even where geometry was confident."""

    def test_chord_1_f6_over_d6(self):
        """Upper head is ALREADY right by geometry (-7.4 -> F6); only the
        lower head (-5.56 -> raw E6) needs the two readers' agreement on
        -5 (D6). Both readers must still be able to abstain on the upper
        head without disturbing its already-correct geometry answer."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-7.4)
        lower = _notehead(log, 1, cls="noteheadHalfInSpace", pos_float=-5.56)
        _ledger_rows(log, lower, clean=-5, grid=-5)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "F6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "D6")
        self.assertEqual(log.verdict(Q.PITCH, lower).reason,
                         "ledger_reader_agreement")
        # The upper head took the geometry path untouched.
        self.assertEqual(log.verdict(Q.PITCH, upper).reason,
                         "position_and_clef")

    def test_chord_2_e6_over_c6(self):
        """BOTH heads need the ledger readers' agreement: -6.88 (raw F6) ->
        E6 (-6), -4.64 (raw D6) -> C6 (-4)."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        lower = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=-4.64)
        _ledger_rows(log, upper, clean=-6, grid=-6)
        _ledger_rows(log, lower, clean=-4, grid=-4)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "E6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "C6")
        for g in (upper, lower):
            self.assertEqual(log.verdict(Q.PITCH, g).reason,
                             "ledger_reader_agreement")

    def test_head_on_a_ledger_above_the_staff(self):
        """A head whose geometry rounds to the WRONG line, but both ledger
        readers measure it ON the next rung out, takes the ledger
        reading."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlack", pos_float=-8.4)  # rounds -8
        _ledger_rows(log, g, clean=-10, grid=-10)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, g).reason,
                         "ledger_reader_agreement")
        self.assertEqual(log.verdict(Q.PITCH, g).value,
                         self._pitch(-10))

    def test_head_in_the_space_beyond_a_ledger_below_the_staff(self):
        """Below the staff, in the exact same shared top-line-origin unit --
        the whole point of fixing the withdrawn first reader's bottom-line
        origin bug."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlack", pos_float=11.4)  # rounds 11
        _ledger_rows(log, g, clean=13, grid=13)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, g).reason,
                         "ledger_reader_agreement")
        self.assertEqual(log.verdict(Q.PITCH, g).value,
                         self._pitch(13))

    @staticmethod
    def _pitch(pos):
        from tools.omr.pitch_resolver import _pitch_from_position
        return _pitch_from_position(pos, "treble")


class TestLedgerDisagreementControls(unittest.TestCase):
    """CLAUDE.md rule 8 and 2.44's own `bound`: a fallback never converts
    'cannot tell' into an answer, and a control must be able to fail."""

    def test_readers_disagree_geometry_stands_and_is_counted(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        _ledger_rows(log, g, clean=-6, grid=-7)   # disagree
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        v = log.verdict(Q.PITCH, g)
        # geometry's own rounding of -6.88 is -7 -> F6, unchanged
        self.assertEqual(v.value, "F6")
        self.assertEqual(v.reason, "position_and_clef_ledger_conflict")

    def test_one_reader_abstains_geometry_stands_and_is_counted(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        _ledger_rows(log, g, clean=-6, grid=None)   # grid abstained
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        v = log.verdict(Q.PITCH, g)
        self.assertEqual(v.value, "F6")
        self.assertEqual(v.reason, "position_and_clef_ledger_one_sided")

    def test_both_readers_abstain_no_clean_ledgers_found_geometry_stands(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        # neither reader produced a row at all (both abstained upstream)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        v = log.verdict(Q.PITCH, g)
        self.assertEqual(v.value, "F6")
        self.assertEqual(v.reason, "position_and_clef")

    def test_in_staff_head_is_unchanged(self):
        """A head ON the staff never gets ledger rows at all (both GATHER
        readers gate on being outside the staff), so it is untouched by
        2.44, exactly as before."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlack", pos_float=3.0)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        v = log.verdict(Q.PITCH, g)
        self.assertEqual(v.reason, "position_and_clef")


if __name__ == "__main__":
    unittest.main()
