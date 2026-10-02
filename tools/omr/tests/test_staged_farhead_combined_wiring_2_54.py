"""ROADMAP 2.54 (Sean, 2026-10-01, "combine that way") -- the STAGED wiring:
`Q.FARHEAD_COMBINED_POSITION` is always recorded (`gather.
gather_farhead_combined_position`) but only ever changes a pitch when
`consequences.FARHEAD_COMBINED_SHIPS` is `True`. It ships `False`.

RED-first: before this lane, `Q.FARHEAD_COMBINED_POSITION` and
`consequences.FARHEAD_COMBINED_SHIPS` did not exist at all --
`AttributeError`/`ImportError` on collection.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""
from __future__ import annotations

import unittest
import unittest.mock

from tools.omr.staged import record as R
from tools.omr.staged.record import Kind, Log, Outcome, Q, READERS, Verdict
from tools.omr.staged import consequences as CONS
from tools.omr.tests.test_staged_notehead_precision import (
    _cell_geometry, _notehead)

STAFF = R.staff(0, 0, 0)


def _clef(log, staff, name="treble"):
    v = Verdict(id=log._next_id("vrd"), subject=staff, quantity=Q.CLEF,
               outcome=Outcome.DECIDED, value=name, decider="test",
               reason="test", considered=(), basis=())
    return log.record(v)


class TestFarheadCombinedShipsFalse(unittest.TestCase):
    """The default: `FARHEAD_COMBINED_SHIPS` is `False`, so a recorded
    combined row changes NOTHING about the decided pitch."""

    def test_ships_false_by_default(self):
        self.assertFalse(CONS.FARHEAD_COMBINED_SHIPS)

    def test_decided_position_unchanged_while_false(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-6.0)
        # A combined row that DISAGREES with geometry -- if this were ever
        # read while the flag is False, the pitch would change.
        log.observe(g, Q.FARHEAD_COMBINED_POSITION, -8,
                   reader=READERS.FARHEAD_COMBINED, frame="cell:0",
                   geom_pos=-6, rungs_pos=-8, branch="disagree_rungs",
                   max_gap_deviation=0.5, n_rungs=3)
        clef = _clef(log, STAFF)
        out = CONS.restate_pitch(log, STAFF, clef)
        self.assertEqual(len(out), 1)
        verdict = log.verdict(Q.PITCH, g)
        self.assertEqual(verdict.reason, "position_and_clef")
        # treble, pos -6 (two spaces above the top line) -> the SAME name
        # a geometry-only read would give; recomputed independently here
        # rather than hard-coded, so this test cannot pass by coincidence.
        from tools.omr.pitch_resolver import _pitch_from_position
        self.assertEqual(verdict.value, _pitch_from_position(-6, "treble"))
        self.assertNotEqual(verdict.value, _pitch_from_position(-8, "treble"))

    def test_absent_combined_row_is_unaffected(self):
        """A far head with NO combined row at all (e.g. `gather_farhead_
        combined_position` abstained, `NO_MASK`) -- the ordinary geometry
        path is completely untouched either way."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-6.0)
        clef = _clef(log, STAFF)
        CONS.restate_pitch(log, STAFF, clef)
        verdict = log.verdict(Q.PITCH, g)
        self.assertEqual(verdict.reason, "position_and_clef")


class TestFarheadCombinedShipsTrue(unittest.TestCase):
    """Patched True for these tests only -- the flag itself stays `False`
    in the shipped tree (TREMOLO_SLASH_SHIPS's own pattern)."""

    def _patch(self):
        return unittest.mock.patch.object(CONS, "FARHEAD_COMBINED_SHIPS", True)

    def test_combined_row_substitutes_when_true(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-6.0)
        log.observe(g, Q.FARHEAD_COMBINED_POSITION, -8,
                   reader=READERS.FARHEAD_COMBINED, frame="cell:0",
                   geom_pos=-6, rungs_pos=-8, branch="disagree_rungs",
                   max_gap_deviation=0.5, n_rungs=3)
        clef = _clef(log, STAFF)
        with self._patch():
            CONS.restate_pitch(log, STAFF, clef)
        verdict = log.verdict(Q.PITCH, g)
        self.assertEqual(verdict.reason, "position_and_clef_farhead_combined")
        from tools.omr.pitch_resolver import _pitch_from_position
        self.assertEqual(verdict.value, _pitch_from_position(-8, "treble"))

    def test_absent_combined_row_falls_back_to_geometry_when_true(self):
        """Even with the flag True, a head with no combined row (never
        entered the far-head population, or that reader abstained) is
        read exactly as before -- the gate is "is there a row", not "is
        the flag set"."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-6.0)
        clef = _clef(log, STAFF)
        with self._patch():
            CONS.restate_pitch(log, STAFF, clef)
        verdict = log.verdict(Q.PITCH, g)
        self.assertEqual(verdict.reason, "position_and_clef")


if __name__ == "__main__":
    unittest.main()
