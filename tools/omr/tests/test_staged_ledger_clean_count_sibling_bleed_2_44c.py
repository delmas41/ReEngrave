"""ROADMAP 2.44c -- `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md`
§12e: on the real Litolff p3 raster, reader 1 (`gather.
gather_ledger_clean_count_position` / `_observe_ledger_clean_count_position`)
read the SAME wrong B5 for BOTH heads of a dense three-chord cluster
(`glyph/3/0/0/2/1` and `/2/3`, printed E6/C6), "suggesting its clean-ledger
scan is picking up ink from the adjacent chord rather than this head's own
column" (FINDINGS §12e). The scan hunts for a thin horizontal rung by
sliding OUTWARD from the staff at this head's own x-window -- but that
window is fixed for the whole scan, and nothing excluded a CHORD-MATE's own
notehead sitting in it. The merged ink of a dense cluster (or, as here, any
case where another head's own ink forms a stroke that passes `ledger_rung_
ink`'s own thin/overhang test at some y along the way) is then read as a
found rung belonging to THIS head.

The fix (`gather.py`, `gather_ledger_clean_count_position` /
`_observe_ledger_clean_count_position`): every OTHER regular notehead in the
SAME cell has its own STANDARD head box computed once and passed in as
`sibling_boxes`; a scan candidate y whose tested window (the same `cx`-
centred span `ledger_rung_ink` itself tests) overlaps a sibling's box is
skipped outright -- never counted as a hit, never counted as a miss either,
exactly like a point `ledger_rung_ink` already declines over for the
SUBJECT's own box (`_exclude_head_box`).

These tests build the REAL failing shape: a thin stroke that `ledger_rung_
ink` genuinely finds as a rung in isolation (proven directly, Part 1,
exactly as `test_staged_ledger_rung_ink.py` proves its own positive
controls), placed where a chord-mate's own notehead box would be. RUN RED
FIRST: before this item, `_observe_ledger_clean_count_position` took no
`sibling_boxes` parameter at all, so the fixture call in Part 2's second
test raises `TypeError`; the diagnostic itself (that un-excluded ink finds
a position, Part 2's first test) always passed and stays passing -- it is
the shape of the bug, not of a crash.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


# A 5-line staff, spacing 20 canonical px, top line at 300, bottom at 380
# (4 spaces, `staff_half_steps` = 8). Head A sits 1.5 spaces above the top
# line (`cy=270`, standard box [186, 214] x [259, 281]) -- past the exempt
# first space (`_ledger_expected`), squarely inside the scan range.
LINE_TOP, LINE_BOTTOM = 300.0, 380.0
SPACING = 20.0
STAFF_HALF_STEPS = 8.0


class _D:
    """A fabricated `Detection` -- only the four geometry fields this
    reader reads (`smufl_name` filtering happens one level up, in
    `gather_ledger_clean_count_position`, not inside the function under
    test)."""
    x_canonical = 186.0
    y_canonical = 259.0
    width_canonical = 28.0
    height_canonical = 22.0


class TestTheRealFailingShape(unittest.TestCase):
    """Part 1 -- the ink alone, proved against `ledger_rung_ink` directly
    (unchanged by this item): a thin stroke sitting CLOSER to the staff
    than head A's own centre, and strictly between the chord-mate's own
    position and the staff, reads as a found rung in isolation. This is
    not a contrived density trick; it is the exact shape `test_staged_
    ledger_rung_ink.py`'s own positive control uses, re-centred here at
    head A's own window."""

    def test_isolated_stroke_is_a_found_rung(self):
        img = _paper()
        _draw(img, 172, 277, 228, 283)   # centred y=280, dist 20px from 300
        m = gather.ledger_rung_ink(img, 186.0, 214.0, 280.0, SPACING, None)
        self.assertTrue(m["found"])


class TestSiblingBleedIsExcluded(unittest.TestCase):
    """Part 2 -- the regression. The SAME stroke sits inside a chord-mate's
    own standard head box (centred near the same stroke, spanning
    `y=[272, 288]`, `x=[190, 230]` -- overlapping head A's own tested
    x-window, exactly the "opposite sides of one stem" dyad geometry
    DECISIONS 2026-09-30 describes). Without exclusion the stroke is read
    as head A's OWN rung (`bracket=beyond`, two steps out); with the
    sibling's box passed in, that exact scan point is skipped and -- being
    the only ink on the page -- the head correctly ABSTAINS rather than
    reporting a position borrowed from its neighbour."""

    SIBLING_BOX = (190.0, 230.0, 272.0, 288.0)

    def _img(self):
        img = _paper()
        _draw(img, 172, 277, 228, 283)
        return img

    def test_RED_without_exclusion_the_neighbours_ink_is_read(self):
        """The pre-2.44c shape: no `sibling_boxes` means every candidate y
        is tested, so the chord-mate's own stroke is found and filed as
        THIS head's position. Kept as the documented hazard, not a target
        to preserve -- the next test is what this item fixes."""
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        gather._observe_ledger_clean_count_position(
            log, g, _D(), LINE_TOP, LINE_BOTTOM, SPACING, STAFF_HALF_STEPS,
            self._img(), None, sibling_boxes=())
        rows = log.rows(Q.LEDGER_CLEAN_COUNT_POSITION, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[-1].detail.get("bracket"), "beyond")

    def test_GREEN_with_the_sibling_box_the_head_abstains(self):
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        gather._observe_ledger_clean_count_position(
            log, g, _D(), LINE_TOP, LINE_BOTTOM, SPACING, STAFF_HALF_STEPS,
            self._img(), None, sibling_boxes=[self.SIBLING_BOX])
        rows = log.rows(Q.LEDGER_CLEAN_COUNT_POSITION, g)
        self.assertEqual(rows, ())
        abst = [a for a in log._abs.values() if a.subject == g]
        self.assertEqual(len(abst), 1)
        self.assertEqual(abst[0].reason, "no_ledger_found")

    def test_a_real_rung_OUTSIDE_every_siblings_box_still_reads(self):
        """Positive control (CLAUDE.md §6b): the exclusion must not just
        blind the reader outright. A head further out (`cy=230`, dist
        70px) with a chord-mate box at dist [39, 61] still finds a genuine
        rung drawn well OUTSIDE that box (dist 15px) -- the exclusion only
        ever removes the sibling's own narrow band, never the whole scan."""
        far_d = type("D", (), {"x_canonical": 186.0, "y_canonical": 219.0,
                               "width_canonical": 28.0,
                               "height_canonical": 22.0})()
        far_sibling_box = (190.0, 230.0, 239.0, 261.0)
        img = _paper()
        _draw(img, 172, 282, 228, 288)   # centred y=285, dist 15px from 300
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        gather._observe_ledger_clean_count_position(
            log, g, far_d, LINE_TOP, LINE_BOTTOM, SPACING, STAFF_HALF_STEPS,
            img, None, sibling_boxes=[far_sibling_box])
        rows = log.rows(Q.LEDGER_CLEAN_COUNT_POSITION, g)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
