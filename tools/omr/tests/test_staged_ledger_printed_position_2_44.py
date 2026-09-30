"""ROADMAP 2.44 — a notehead OUTSIDE the staff takes its position from the
PRINTED ledger lines, not from the staff's own spacing carried past them.

⚠️ WHY THIS FILE EXISTS. Sean, 2026-09-30, on the ruler crop above Litolff
p3 staff/3/0/0: "the ledger lines look like they are not evenly separated" —
measured: top line 449.5, printed ledgers at 431.5 / 418.5 / 398.5 (gaps
18 / 13 / 20 px) against a staff spacing of 15.75 px. Extrapolating the
staff's own spacing past its outer line (`gather_notehead_positions`'s
`pos_float = (y_center - top_y) / half_step`) lands ~4 px — half a step —
off by the THIRD ledger, which is exactly what wrote a D6 as E6 on the
2026-09-30 flute chord Sean confirmed as F6 over D6.

⚠️ RUN RED FIRST: `gather._observe_ledger_printed_position`,
`gather.gather_ledger_printed_position`, `Q.LEDGER_PRINTED_POSITION` and
`ABSTAIN.NO_LEDGER_FOUND`/`LEDGERS_IRREGULAR`/`HEAD_EDGE_UNREADABLE` do not
exist before this round.

All coordinates below are the cell's own CANONICAL frame — the same frame
`gather_notehead_positions` and `gather._observe_ledger_printed_position`
both read (`d.x_canonical`/`d.y_canonical`, `cell.staff_line_ys_canonical`,
`cell.image_no_staff`) — and, for the Litolff scenarios, are Sean's own
measured page pixels, unchanged (canonical == page pixels at upscale 1.0
for a synthetic raster with no cell to convert through).
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from tools.omr.pitch_resolver import _pitch_from_position
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q


def _paper(h=560, w=220):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


def _det(cx, cy, w=1.0, h=1.0):
    return SimpleNamespace(x_canonical=cx - w / 2.0, y_canonical=cy - h / 2.0,
                           width_canonical=w, height_canonical=h)


def _draw_head(img, cx, cy, spacing=None):
    """A solid block the size of a STANDARD notehead (`geometry.
    standard_head_box`), centred at `(cx, cy)` -- so a synthetic test's
    detector position is also where the head's own TRUE ink sits, exactly
    as `_true_head_ink_y_span` now requires (ROADMAP 2.44, manager review
    2026-09-30: the bracket is read off the head's own measured ink, never
    assumed from the box alone)."""
    from tools.omr.staged.geometry import standard_head_box
    sp = spacing if spacing is not None else SPACING
    x0, x1, y0, y1 = standard_head_box(cx, cy, sp)
    _draw(img, x0, y0, x1, y1)


# Sean's own measured Litolff p3 numbers (page pixels; DECISIONS 2026-09-30).
SPACING = 15.75
LINE_TOP = 449.5
LINE_BOTTOM = LINE_TOP + 4 * SPACING     # 512.5, 5 staff lines
LEDGER_1 = 431.5    # A5
LEDGER_2 = 418.5    # C6
LEDGER_3 = 398.5    # E6
THICKNESS = 1.5


def _litolff_raster():
    """The three printed ledgers above staff/3/0/0, unevenly spaced (gaps
    18 / 13 / 20 px against the 15.75 px staff spacing) — drawn wide enough
    to overhang a standard head centred anywhere near x=100, and thin
    enough to clear the density/adjacent guards `ledger_rung_ink` applies."""
    img = _paper()
    for y in (LEDGER_1, LEDGER_2, LEDGER_3):
        _draw(img, 40, y - 3, 160, y + 3)
    return img


class TestSeansChordFromTheRealNumbers(unittest.TestCase):
    """Litolff p3 bar 50, `glyph/3/0/0/2/4`+`/9` (and `/1`+`/3`): Sean
    confirmed F6 over D6 (DECISIONS 2026-09-30). Extrapolating the staff's
    own spacing writes the lower head as E6 -- measured off the ACTUAL
    ledgers it is D6."""

    def test_the_lower_head_between_ledger_2_and_3_reads_D6(self):
        img = _litolff_raster()
        _draw_head(img, 100.0, 413.0)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 4)
        d = _det(100.0, 413.0)     # Sean's own measured ink centre, ~413
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        pos = int(rows[0].value)
        self.assertEqual(pos, -5)
        self.assertEqual(rows[0].detail.get("bracket"), "between")
        self.assertEqual(_pitch_from_position(pos, "treble"), "D6")

    def test_the_upper_head_beyond_ledger_3_reads_F6(self):
        img = _litolff_raster()
        _draw_head(img, 100.0, 391.0)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 9)
        d = _det(100.0, 391.0)    # farther out than the third ledger
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        pos = int(rows[0].value)
        self.assertEqual(pos, -7)
        self.assertEqual(rows[0].detail.get("bracket"), "beyond")
        self.assertEqual(_pitch_from_position(pos, "treble"), "F6")


class TestOnALedger(unittest.TestCase):
    def test_a_head_centred_on_the_second_ledger_reads_C6_on(self):
        img = _litolff_raster()
        _draw_head(img, 100.0, LEDGER_2)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 1)
        d = _det(100.0, LEDGER_2)
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        pos = int(rows[0].value)
        self.assertEqual(pos, -4)
        self.assertEqual(rows[0].detail.get("bracket"), "on")
        self.assertEqual(_pitch_from_position(pos, "treble"), "C6")


class TestASpaceJustBeyondTheLastLedger(unittest.TestCase):
    """A head one further space out than the farthest printed ledger found —
    the same shape as the F6 chord note above, isolated as its own case."""

    def test_reads_the_odd_step_beyond(self):
        img = _paper()
        _draw(img, 40, LEDGER_1 - 3, 160, LEDGER_1 + 3)   # ONE ledger only
        _draw_head(img, 100.0, LEDGER_1 - SPACING * 0.9)
        log = Log()
        g = R.glyph(1, 0, 0, 0, 0)
        d = _det(100.0, LEDGER_1 - SPACING * 0.9)  # the space beyond it
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0].value), -3)     # beyond the 1 found
        self.assertEqual(rows[0].detail.get("bracket"), "beyond")


# ─────────────────────────────────────────────────────────────────────────────
# Controls
# ─────────────────────────────────────────────────────────────────────────────

class TestControls(unittest.TestCase):
    def test_an_in_staff_head_never_changes(self):
        """CLAUDE.md §6a: this reader must never touch a note on the staff —
        `gather_notehead_positions`'s own row is the only reading there."""
        img = _litolff_raster()
        log = Log()
        g = R.glyph(3, 0, 0, 0, 0)
        d = _det(100.0, LINE_TOP + 2 * SPACING)    # the middle line
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        self.assertEqual(log.rows(Q.LEDGER_PRINTED_POSITION, g), ())
        self.assertEqual(log.refusals(Q.LEDGER_PRINTED_POSITION, g), ())

    def test_a_far_head_with_no_ledger_found_abstains_and_changes_nothing(self):
        """CLAUDE.md §10 (Sean, 2026-09-29): 'there is no such thing as a
        far note with no ledger line' — a clean empty scan is a READING
        GAP, never a page fact, so this must ABSTAIN, never write a
        position the staff's own extrapolation would then be silently
        overridden by."""
        img = _paper()      # blank: no ledger drawn anywhere
        log = Log()
        g = R.glyph(1, 0, 0, 0, 0)
        d = _det(100.0, 400.0)
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        self.assertEqual(log.rows(Q.LEDGER_PRINTED_POSITION, g), ())
        refusals = log.refusals(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, ABSTAIN.NO_LEDGER_FOUND)

    def test_a_head_the_staffs_own_spacing_would_round_to_the_wrong_ledger(self):
        """A head at y=403 sits strictly BETWEEN the measured ledgers 2
        (418.5) and 3 (398.5) -- but the staff's own extrapolated spacing
        (`gather_notehead_positions`'s arithmetic, unchanged) rounds it to
        ledger 3's own step (E6), one step off the measured bracket (D6),
        because the THIRD ledger's true gap (20px) is 4px short of the
        47.25px three whole spacings would predict."""
        img = _litolff_raster()
        _draw_head(img, 100.0, 403.0)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 3)
        d = _det(100.0, 403.0)
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        pos = int(rows[0].value)
        self.assertEqual(pos, -5)
        self.assertEqual(rows[0].detail.get("bracket"), "between")
        extrapolated = int(round((403.0 - LINE_TOP) / (SPACING / 2.0)))
        self.assertEqual(extrapolated, -6)
        self.assertNotEqual(extrapolated, pos)

    def test_unevenly_spaced_ledgers_give_the_right_count_where_extrapolation_would_not(self):
        """The THIRD ledger sits at gap 20px (measured) against 3*15.75 =
        47.25px extrapolated (a ~4px / quarter-step error) — this reader's
        own scan, not a fixed step, is what still finds it."""
        img = _litolff_raster()
        _draw_head(img, 100.0, LEDGER_3)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 2)
        d = _det(100.0, LEDGER_3)
        gather._observe_ledger_printed_position(
            log, g, d, LINE_TOP, LINE_BOTTOM, SPACING, img, THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0].value), -6)
        self.assertEqual(rows[0].detail.get("bracket"), "on")


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE: `consequences.restate_pitch` substitutes the measured ledger
# reading for the staff's own extrapolated rounding -- never a second vote,
# and never across a disagreement bigger than its own declared bound.
# ─────────────────────────────────────────────────────────────────────────────

from tools.omr.staged import consequences               # noqa: E402
from tools.omr.staged.record import Outcome, Verdict     # noqa: E402


def _clef_verdict(staff, name="treble"):
    return Verdict(id="v-clef", subject=staff, quantity=Q.CLEF,
                   outcome=Outcome.DECIDED, value=name, decider="test",
                   reason="test")


class TestRestatePitchGeometryFirstLedgerTiebreak(unittest.TestCase):
    """ROADMAP 2.44, Sean's redesign 2026-09-30: geometry stands by
    default; only within `LEDGER_PRINTED_POSITION_BOUNDARY_MARGIN` (0.15)
    of its own rounding boundary does the ledger reading get a say, and
    even then only between the TWO neighbouring slots the boundary sits
    between. Real numbers from the Litolff p3 A/B
    (`benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §10):
    Sean's confirmed D6 (`glyph/3/0/0/2/9`, raw -5.56, boundary distance
    0.06) and the two confirmed C6 heads the first version of this rule
    broke (`/4/8` raw -3.94, `/5/12` raw -4.02, boundary distances
    0.44/0.48)."""

    def test_near_boundary_ledger_reading_is_a_tiebreak(self):
        """/2/9's own numbers: raw -5.56 rounds to -6 (E6); the ledger
        reading -5 is the OTHER neighbour (-6, -5) and wins -> D6."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -5.56,
                   reader="geometry", frame="cell/0")
        log.observe(g, Q.LEDGER_PRINTED_POSITION, -5,
                   reader="cv_ledger", frame="cell/0", bracket="beyond")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "D6")
        self.assertEqual(out[0].reason, "position_and_clef_ledger")

    def test_confident_geometry_never_consults_the_ledger(self):
        """`/4/8`'s own numbers: raw -3.94, boundary distance 0.44 -- far
        outside the margin. Geometry (C6) stands even though a
        (deliberately wrong-looking) ledger row is present and would, if
        consulted, disagree -- it must not even be READ."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -3.94,
                   reader="geometry", frame="cell/0")
        log.observe(g, Q.LEDGER_PRINTED_POSITION, -8,
                   reader="cv_ledger", frame="cell/0", bracket="beyond")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "C6")
        self.assertEqual(out[0].reason, "position_and_clef")

    def test_a_second_confident_geometry_case_also_stands(self):
        """`/5/12`'s own numbers: raw -4.02, boundary distance 0.48."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -4.02,
                   reader="geometry", frame="cell/0")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "C6")
        self.assertEqual(out[0].reason, "position_and_clef")

    def test_near_boundary_but_ledger_names_neither_neighbour_is_counted(self):
        """`/2/4`'s own numbers: raw -7.4 (boundary distance 0.1, inside
        the margin) but the measured ledger reading (-3) is nowhere near
        either neighbouring slot (-8, -7) -- a Litolff merging-plate scan
        artefact. Geometry (F6) stands, COUNTED as a conflict rather than
        dropped."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -7.4,
                   reader="geometry", frame="cell/0")
        log.observe(g, Q.LEDGER_PRINTED_POSITION, -3,
                   reader="cv_ledger", frame="cell/0", bracket="beyond")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "F6")
        self.assertEqual(out[0].reason, "position_and_clef_ledger_conflict")

    def test_near_boundary_with_no_ledger_reading_keeps_geometry(self):
        """A near-boundary head with NO `Q.LEDGER_PRINTED_POSITION` row at
        all (the scan abstained, e.g. `no_ledger_found`) -- geometry
        stands, counted under its own reason rather than silently
        defaulting to the generic case."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -5.56,
                   reader="geometry", frame="cell/0")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "E6")
        self.assertEqual(out[0].reason, "position_and_clef_ledger_absent")


class TestBracketUsesTheHeadsOwnMeasuredInk(unittest.TestCase):
    """MANAGER REVIEW 2026-09-30 (`5f12cd24`): two real Litolff p3 heads
    (`glyph/3/0/0/4/8`, `glyph/3/0/0/5/12`) measured B5 where the print is
    C6, because the bracket was tested against the STANDARD head box
    (centred on the DETECTOR's own box, ~7 px low on these heads) rather
    than the head's own ink. Real numbers: box y 412-427 (detector centre
    419.5); the head's own ink (a hollow ring) runs 402-416 then 420-426,
    a TRUE extent of 402-426 (centre 414), with the C6 ledger (~414.5)
    running through its middle third -- ON, not beyond it. Ledgers beside
    it: ~433.5 (A5), ~414.5 (C6), ~396 (E6); staff top line 449.5."""

    TOP = 449.5

    def _raster(self):
        img = _paper(h=560, w=220)
        for y in (433.5, 414.5, 396.0):          # A5, C6, E6
            _draw(img, 40, y - 3, 160, y + 3)
        # the head's own hollow-ring ink -- excluding the ledger's own rows,
        # a TRUE extent of 402-426 (matches the manager's own measurement)
        _draw(img, 90, 402, 110, 411)             # top rim, clear of C6
        _draw(img, 90, 420, 110, 426)             # bottom rim
        return img

    def test_RED_before_the_fix_this_read_B5_not_C6(self):
        """The buggy shape, pinned: a detector box centred 5.5 px below the
        head's own true centre (419.5 vs 414) used to move the middle-third
        test past the C6 ledger entirely, landing "between A5 and C6" (B5)
        instead of "on C6"."""
        img = self._raster()
        log = Log()
        g = R.glyph(3, 0, 0, 0, 8)
        d = _det(100.0, 419.5)      # the DETECTOR's own (mis-centred) box
        gather._observe_ledger_printed_position(
            log, g, d, self.TOP, self.TOP + 4 * SPACING, SPACING, img,
            THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("bracket"), "on")
        self.assertEqual(int(rows[0].value), -4)
        self.assertEqual(_pitch_from_position(int(rows[0].value), "treble"),
                         "C6")

    def test_a_second_head_with_the_same_shape_also_reads_C6(self):
        """`glyph/3/0/0/5/12`: the same shape, a stacked open chord on the
        C6 and E6 ledgers. Isolated as its own case per the manager's own
        two named subjects."""
        img = self._raster()
        log = Log()
        g = R.glyph(3, 0, 0, 0, 12)
        d = _det(100.0, 419.5)
        gather._observe_ledger_printed_position(
            log, g, d, self.TOP, self.TOP + 4 * SPACING, SPACING, img,
            THICKNESS)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail.get("bracket"), "on")
        self.assertEqual(int(rows[0].value), -4)

    def test_a_merged_stack_too_tall_to_be_one_head_abstains(self):
        """Where the measured ink extent cannot be separated from a
        neighbouring head (a fused Litolff stack), the bracket must
        ABSTAIN rather than guess a position from an extent that is not
        really one head's own ink."""
        img = _paper(h=560, w=220)
        _draw(img, 40, 414.5 - 3, 160, 414.5 + 3)
        # ink far taller than any real head (> 2.2 staff spaces = 34.65 px)
        # but still within the search margin (+-1.3 sp = 20.475 px of cy) --
        # fused ink from a neighbouring head, not readable as one head's own.
        _draw(img, 90, 394, 110, 398)
        _draw(img, 90, 429, 110, 433)
        log = Log()
        g = R.glyph(3, 0, 0, 0, 20)
        d = _det(100.0, 413.0)
        gather._observe_ledger_printed_position(
            log, g, d, self.TOP, self.TOP + 4 * SPACING, SPACING, img,
            THICKNESS)
        self.assertEqual(log.rows(Q.LEDGER_PRINTED_POSITION, g), ())
        refusals = log.refusals(Q.LEDGER_PRINTED_POSITION, g)
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, ABSTAIN.HEAD_EDGE_UNREADABLE)


class TestRestatePitchSubstitutionControls(unittest.TestCase):
    def test_POSITIVE_CONTROL_no_ledger_row_is_unchanged(self):
        """A note on or just outside the staff never gets a
        `Q.LEDGER_PRINTED_POSITION` row at all (`_ledger_expected` refuses
        to gather one) -- `restate_pitch` must behave exactly as it did
        before this rule existed."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 0.0,
                   reader="geometry", frame="cell/0")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "F5")
        self.assertEqual(out[0].reason, "position_and_clef")


if __name__ == "__main__":
    unittest.main()
