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


class TestRestatePitchSubstitutesTheLedgerReading(unittest.TestCase):
    def test_a_close_ledger_reading_is_substituted(self):
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -6.0,
                   reader="geometry", frame="cell/0")
        log.observe(g, Q.LEDGER_PRINTED_POSITION, -5,
                   reader="cv_ledger", frame="cell/0", bracket="between")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "D6")
        self.assertEqual(out[0].reason, "position_and_clef_ledger")

    def test_a_large_disagreement_abstains_from_the_substitution(self):
        """CLAUDE.md rule 8: the two readings disagree by more than the
        rule's own declared bound (1 step) -- a sign one of them misread
        the page, never averaged or guessed between. The staff's own
        extrapolated position stands, UNCHANGED, and the conflict is
        counted in the reason rather than dropped."""
        log = Log()
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -6.0,
                   reader="geometry", frame="cell/0")
        log.observe(g, Q.LEDGER_PRINTED_POSITION, -3,
                   reader="cv_ledger", frame="cell/0", bracket="between")
        out = consequences.restate_pitch(log, staff, _clef_verdict(staff))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, "E6")     # the extrapolated reading
        self.assertEqual(out[0].reason, "position_and_clef_ledger_conflict")

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
