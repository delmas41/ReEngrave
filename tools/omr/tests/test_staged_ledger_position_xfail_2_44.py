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


class TestLedgerPositionNotYetBuilt(unittest.TestCase):
    """Pinned to Sean's confirmed print reading, XFAIL until ROADMAP 2.44
    reads positions from the printed ledger lines instead of extrapolating
    the staff's own spacing."""

    @unittest.expectedFailure
    def test_glyph_3_0_0_2_4_and_9_are_f6_over_d6(self):
        """Real Litolff p3 positions (-7.4, -5.56): raw rounding gives
        F6/E6 (a second) -- the confirmed print is F6/D6 (a third).
        KNOWN MISS: neither 2.42 mechanism (both withdrawn) fixes this;
        2.44 will."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=-7.4)
        lower = _notehead(log, 1, cls="noteheadHalfInSpace", pos_float=-5.56)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "F6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "D6")

    @unittest.expectedFailure
    def test_glyph_3_0_0_2_1_and_3_are_f6_over_d6(self):
        """Real Litolff p3 positions (-6.88, -4.64) -- ALSO confirmed F6/D6.
        Pinned XFAIL per instruction even though plain rounding happens to
        already land here: the mechanism that would GUARANTEE it (reading
        the real ledgers, 2.44) does not exist yet, so this is not asserted
        as a durable pass."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=-6.88)
        lower = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=-4.64)
        clef = _clef(log, STAFF)
        consequences.restate_pitch(log, STAFF, clef)
        self.assertEqual(log.verdict(Q.PITCH, upper).value, "F6")
        self.assertEqual(log.verdict(Q.PITCH, lower).value, "D6")
        # Force the xfail regardless of the coincidental rounding above --
        # the GUARANTEE this pins does not exist until 2.44 reads the
        # ledgers themselves.
        raise AssertionError(
            "passes by coincidence of rounding only -- 2.44 not built")


if __name__ == "__main__":
    unittest.main()
