"""ROADMAP 2.83 -- an eighth's FLAG at its stem tip is read where Sean's flags actually are.

Sean, 2026-10-10 (DECISIONS): *"There are 8th note flags that are not being seen. We need to make sure the reader box
is big enough. Sometimes the flag stays closer to the stem at the tip but the flag shape is undeniable."*

WHAT WAS WRONG. `Q.STEM_TIP_INK` (2.18c) tested a window 1.0 to 2.5 staff spaces back from the tip, 0.9 wide, at a
density of 0.30: every number CONVENTION ASSUMED / NOT CONFIRMED. Measured on Sean's page (Brahms 317803 pdf 0, his
34 `flag8th*` boxes, `probe/l283_flag_geometry.py`), a flag's ink starts at the tip (its box begins at t = 0.02 median,
-0.19 to 0.43), runs 2.85 to 3.76 spaces back toward the head and stands 0.84 to 1.34 spaces out from the stem's right
edge; its root is a wedge at the tip and its arm a thin stroke 0.6-1.1 spaces out. The old window sat on the thin arm:
on the real erased raster 20 of 21 of his flags read 0.13-0.29 and only one cleared 0.30.

WHAT IS READ NOW. The ink CONNECTED to the stem at its tip (a flag hangs from it), on the right, from the tip itself
back to the stem's own head: found where it starts within `STEM_TIP_ROOT_MAX_SPACES` of the tip, stands out between
`STEM_TIP_OUT_MIN_SPACES` and `STEM_TIP_OUT_MAX_SPACES` and has an arm of `STEM_TIP_ARM_MIN_SPACES`; NOT found
(`False`) only where nothing hangs from the tip; CANNOT TELL (`None`, never "no flag") where ink hangs there that is
not flag-shaped: a beam or slur that runs on, ink on both sides, a bar across the tip (CLAUDE.md rule 8).

RUN RED FIRST against the unrepaired tree: the flag-at-the-tip tests, the head-clip tests and the observer's
cannot-tell tests fail on 2.18c's window; the controls below (a clean tip, a hairpin, a beam, a slur, a ledger line)
pass on both -- a refusal test with no positive control passes by refusing everything.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q

SP = 20.0                         # one staff space, canonical px
STEM_X0, STEM_X1 = 190.0, 194.0   # a 4px-wide stem
TOP_Y, BOTTOM_Y = 100.0, 300.0    # a 10-space stem: the two tips are far apart


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _stem(img, y0=TOP_Y, y1=BOTTOM_Y):
    img[int(y0):int(y1), int(STEM_X0):int(STEM_X1)] = 0


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


def _flag_up_stem(img, thin_arm=True):
    """An up-stem's eighth flag, drawn the way Sean's measure it (spaces from the tip, 20 px each): a wedge ROOT at the
    tip (t 0 .. 0.6, 0 .. 0.7 out) and an ARM (0.6 .. 2.5 back, 0.55 .. 0.8 out) -- a 0.25-space stroke, thinner than the
    old window's 0.30 density would call ink."""
    _draw(img, STEM_X1, TOP_Y, STEM_X1 + 14, TOP_Y + 12)
    _draw(img, STEM_X1 + 11, TOP_Y + 12, STEM_X1 + 16, TOP_Y + 50)


def _flag_down_stem(img):
    """The same flag at a down-stem's bottom tip: mirrored in y."""
    _draw(img, STEM_X1, BOTTOM_Y - 12, STEM_X1 + 14, BOTTOM_Y)
    _draw(img, STEM_X1 + 11, BOTTOM_Y - 50, STEM_X1 + 16, BOTTOM_Y - 12)


class TestTheFlagIsReadWhereItStands(unittest.TestCase):

    def test_a_flag_whose_ink_hugs_the_tip_is_found(self):
        """⚠️ THE FAULT. Sean: the flag 'stays closer to the stem at the tip but the shape is undeniable'. The old window
        (1.0-2.5 back, density >= 0.30) saw only the thin arm: 0.25 here, under the cut -- 20 of his 21 real flags
        read 0.13-0.29 the same way."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertTrue(m["found"], m)

    def test_the_same_flag_at_a_down_stems_bottom_tip(self):
        img = _paper()
        _stem(img)
        _flag_down_stem(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, BOTTOM_Y, -1.0, SP)
        self.assertTrue(m["found"], m)

    def test_POSITIVE_CONTROL_a_clean_tip_is_found_FALSE_not_unread(self):
        """Nothing hangs from this tip: a positive 'no flag', which is what rule 8 lets the bare-stem readers use. It must
        be able to say False, and must not say it for a tip it could not read."""
        img = _paper()
        _stem(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertIs(m["found"], False, m)

    def test_the_far_tip_of_the_same_stem_is_bare(self):
        """The flag is at the TOP tip; the stem's bottom tip reads clean (so the answer follows the end asked)."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, BOTTOM_Y, -1.0, SP)
        self.assertIs(m["found"], False, m)

    def test_a_thin_flag_with_no_arm_is_not_flag_shaped(self):
        """A root wedge alone (an eroded flag, a speck at the tip) is ink hanging there that is not a flag: cannot tell,
        never 'no flag' and never 'a flag'."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X1, TOP_Y, STEM_X1 + 12, TOP_Y + 8)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertIsNone(m["found"], m)


class TestWhatIsNotAFlag(unittest.TestCase):
    """Each control is drawn on the tip of a stem that has a REAL flag elsewhere in the cell reading, so the reader is
    known able to say True; none of these may."""

    def test_a_beam_that_runs_on_from_the_tip_is_not_a_flag(self):
        img = _paper()
        _stem(img)
        _draw(img, STEM_X1, TOP_Y, STEM_X1 + 90, TOP_Y + 12)       # a 4.5-space bar to the next stem
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)
        self.assertIsNone(m["found"], m)

    def test_a_beam_arriving_from_the_left_is_not_a_flag(self):
        img = _paper()
        _stem(img)
        _draw(img, STEM_X0 - 90, TOP_Y, STEM_X1, TOP_Y + 12)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_mark_standing_on_the_LEFT_of_the_tip_makes_it_unreadable(self):
        """ink on BOTH sides of the stem at the tip, thicker than a line: a flag hangs from one side only, so the tip is
        not read as one (here a slur's belly 0.6 spaces thick through the left of a real flag)."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        _draw(img, STEM_X0 - 30, TOP_Y + 4, STEM_X0, TOP_Y + 16)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_thin_slur_end_across_a_BARE_tip_is_not_a_flag(self):
        """The same tail, thin (0.25 spaces: a line's thickness), on a stem with nothing hanging from it: not a flag, and
        the stem reads bare (the line's rows are left out, as a ledger line's are)."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X0 - 30, TOP_Y + 4, STEM_X1 + 26, TOP_Y + 9)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_hairpin_crossing_the_window_is_not_a_flag(self):
        """Two thin lines diverging across the stem at the tip: the right half is long and thin, the left half is the
        same -- ink on both sides, never a flag."""
        img = _paper()
        _stem(img)
        for i in range(0, 60):
            y = TOP_Y + 6 + i // 6
            _draw(img, STEM_X0 - 30 + i, y, STEM_X0 - 28 + i, y + 2)
            _draw(img, STEM_X0 - 30 + i, y + 14 - i // 3, STEM_X0 - 28 + i, y + 16 - i // 3)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_ledger_line_through_the_stem_is_not_a_flag(self):
        """A thin line (0.3 space) through the stem, longer on the head's side: a stub on both sides at one row."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X0 - 8, TOP_Y + 30, STEM_X1 + 26, TOP_Y + 36)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_ledger_line_stub_far_from_the_tip_is_not_hanging_from_it(self):
        """A short thick stub standing out right at 2.9 spaces: ink attached to the stem, but it starts nowhere near the
        tip. Measured on his page: six bare stems read this way (t_first 2.9-3.0) against his flags' 0.4-0.8."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X1, TOP_Y + 58, STEM_X1 + 26, TOP_Y + 66)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertNotEqual(m["found"], True, m)

    def test_a_flag_beside_a_ledger_line_through_the_stem_is_still_a_flag(self):
        """THE CONTROL for the line-row rule: a real flag, and a thin ledger line through the stem lower down. The line's
        rows are left out; the flag is read."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        _draw(img, STEM_X0 - 8, TOP_Y + 40, STEM_X1 + 26, TOP_Y + 46)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertTrue(m["found"], m)

    def test_a_bar_across_the_tip_is_unreadable_not_clean(self):
        """A 0.7-space bar through the stem at the tip, standing out on both sides, is a beam or a smear: cannot tell,
        and in particular never False ('nothing hangs here')."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X0 - 20, TOP_Y + 4, STEM_X1 + 20, TOP_Y + 18)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertIsNone(m["found"], m)


class TestTheStemsOwnHeadIsNotAFlag(unittest.TestCase):

    def _short_stem_with_head(self):
        """A 3.2-space stem whose head (1.3 wide, 1.1 tall, beside the stem's far end) sits at the bottom."""
        img = _paper()
        _stem(img, TOP_Y, TOP_Y + 64)
        _draw(img, STEM_X1, TOP_Y + 44, STEM_X1 + 26, TOP_Y + 66)       # the head, right of a stem-up note's stem? a
        return img                                                      # right-side head: ink attached to the stem

    def test_the_head_is_clipped_where_its_box_begins(self):
        """With the head's near edge handed over (`head_edge`), the window stops short of it and the head's ink is not read;
        without it (the CONTROL) the same raster reads as ink hanging from the stem -- that is what the clip is for."""
        img = self._short_stem_with_head()
        head_edge = TOP_Y + 44.0
        clipped = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP, head_edge=head_edge)
        self.assertIsNot(clipped["found"], True, clipped)
        unclipped = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertIsNot(unclipped["found"], False, unclipped)       # the raster really holds that head's ink

    def test_a_flag_on_a_short_stem_is_still_read_up_to_the_head(self):
        img = _paper()
        _stem(img, TOP_Y, TOP_Y + 64)
        _flag_up_stem(img)
        head_edge = TOP_Y + 50.0                                         # 2.5 spaces: the arm ends just short of it
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP, head_edge=head_edge)
        self.assertTrue(m["found"], m)


# ─────────────────────────────────────────────────────────────────────────────
# the observer: a row per end, True / False / an abstention that SAYS why
# ─────────────────────────────────────────────────────────────────────────────

class FakeCell:
    def __init__(self, img):
        self.image_no_staff = img


SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TOP_Y, STEM_X1 - STEM_X0, BOTTOM_Y - TOP_Y)       # x, y, w, h


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class TestTheObserver(unittest.TestCase):

    def _run(self, img, blockers=(), heads=None):
        log = Log()
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img), "obs:stem-1", STEM_BOX, list(blockers), SP,
                                     heads=heads)
        log.freeze()
        return log

    def test_a_flag_files_a_true_row_for_the_top_end_and_a_false_row_for_the_bottom(self):
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        log = self._run(img)
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertTrue(rows["top"].value)
        self.assertIs(rows["bottom"].value, False)
        # the measured shape is on the row, not only the verdict
        for key in ("out", "arm", "area"):
            self.assertIn(key, rows["top"].detail)

    def test_ink_that_is_not_flag_shaped_is_an_ABSTENTION_with_its_reason_never_a_false_row(self):
        """Rule 8: a tip with a beam's end on it is not 'no flag'."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X1, TOP_Y, STEM_X1 + 90, TOP_Y + 12)
        log = self._run(img)
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertIn("top", abst)
        self.assertEqual(abst["top"].reason, ABSTAIN.AMBIGUOUS)
        self.assertIn("why", abst["top"].detail)
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertNotIn("top", rows)

    def test_a_blocker_over_the_ink_at_the_tip_itself_abstains_occupied(self):
        """The reader now starts at the tip: a beam stroke box standing over the flag's ROOT (0.3 spaces in) blocks it --
        under the old window (1.0 back) the same box did not overlap it at all."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        blocker = (STEM_X1, TOP_Y + 2.0, STEM_X1 + 24.0, TOP_Y + 10.0)       # corners; over the tip
        log = self._run(img, blockers=[blocker])
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertEqual(abst["top"].reason, ABSTAIN.OCCUPIED)

    def test_a_box_standing_NEAR_the_tip_but_not_over_its_ink_does_not_block_RED_against_the_window_rule(self):
        """⚠️ THE REGRESSION THE FIRST ARM FOUND (Brahms pdf 1 `glyph/1/0/3/3/0`): the window a flag needs is 1.5 spaces
        wide, and an accidental standing 1.3 spaces from the stem overlapped it, so a flag the old reader had counted went
        unread. A box can explain only the ink it COVERS: this one covers none of the stem's."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        _draw(img, STEM_X1 + 26, TOP_Y + 20, STEM_X1 + 36, TOP_Y + 40)       # a flat's ink, apart from the flag
        flat = (STEM_X1 + 24.0, TOP_Y + 14.0, STEM_X1 + 38.0, TOP_Y + 46.0)   # its box (corners): 1.2 spaces out
        log = self._run(img, blockers=[flat])
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertTrue(rows["top"].value)

    def test_CONTROL_a_box_over_the_ink_attached_to_the_tip_still_blocks(self):
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        over_arm = (STEM_X1 + 10.0, TOP_Y + 20.0, STEM_X1 + 20.0, TOP_Y + 40.0)   # covers the flag's arm
        log = self._run(img, blockers=[over_arm])
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertEqual(abst["top"].reason, ABSTAIN.OCCUPIED)

    def test_a_ledger_line_box_covering_only_a_thin_crossing_line_does_not_block_the_flag(self):
        """The line's rows are left out of the reading, so a `ledgerLine` box over them covers none of the ink READ."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        _draw(img, STEM_X0 - 8, TOP_Y + 60, STEM_X1 + 26, TOP_Y + 66)
        ledger = (STEM_X0 - 8.0, TOP_Y + 60.0, STEM_X1 + 26.0, TOP_Y + 66.0)
        log = self._run(img, blockers=[ledger])
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertTrue(rows["top"].value)

    def test_the_stems_own_flag_box_does_not_block_its_own_tip(self):
        """2.75 stays: a detected flag box hanging off THIS stem is set aside, so the ink is still read."""
        img = _paper()
        _stem(img)
        _flag_up_stem(img)
        own_flag = _Det("flag8thUp", STEM_X1 - 2, TOP_Y + 2, 24, 55)
        blockers = gather._stem_tip_blockers([], [own_flag], SP, own_stem=STEM_BOX)
        log = self._run(img, blockers=blockers)
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertTrue(rows["top"].value)

    def test_the_end_a_head_stands_at_is_not_read_as_a_flag(self):
        """A head at this end of the stem is the head's own ink, not a hook: abstains occupied, with the reason said."""
        img = _paper()
        _stem(img)
        _draw(img, STEM_X1, TOP_Y - 4, STEM_X1 + 26, TOP_Y + 18)          # a head AT the top end
        head = (STEM_X1, TOP_Y - 4, 26.0, 22.0)                            # x, y, w, h
        log = self._run(img, heads=[head])
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertEqual(abst["top"].reason, ABSTAIN.OCCUPIED)
        self.assertEqual(abst["top"].detail.get("why"), "head_at_this_end")


if __name__ == "__main__":
    unittest.main()
