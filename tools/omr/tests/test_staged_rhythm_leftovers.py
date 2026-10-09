"""Two rhythm leftovers Sean judged EIGHTHS (2026-10-09): 2.65 tile 15 and 2.74
review Litolff 1.

PART A -- two flag boxes on ONE printed flag (`flag8thUp` + `flag16thUp`, the
detector's two readings of the same ink) made the stem's own tip look
`occupied`, so `Q.STEM_TIP_INK` -- and with it the 2.69 hook count that breaks
the vote -- was never filed. A detected flag box hangs off its OWN stem's tip by
construction; it is the thing the hook reader is meant to count UNDER, not ink
some other reader already explains.

PART B -- see the second half of this file.

⚠️ RUN RED FIRST (the commit says so): the tests that call the new keyword
(`own_stem=`) fail on the unrepaired tree with TypeError; the behavioural
controls (a flag of ANOTHER stem, a tie, a beam stroke, a bare stem, the legacy
call) are green before and after so a rule that "unblocks everything" cannot
pass.
"""

from __future__ import annotations

import types
import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q

from tools.omr.tests.test_staged_stem_tip_hooks import (
    FAR_Y, SP, STEM_X0, STEM_X1, TIP_Y, _hook, _paper, _stem)

SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TIP_Y, STEM_X1 - STEM_X0, FAR_Y - TIP_Y)     # x, y, w, h


class _Cell:
    def __init__(self, img):
        self.image_no_staff = img


def _det(name, x, y, w, h):
    return types.SimpleNamespace(
        smufl_name=name, x_canonical=float(x), y_canonical=float(y),
        width_canonical=float(w), height_canonical=float(h))


def _flag_up(name="flag8thUp", dy=0.22):
    """The detector's box over an up-stem's flag, as measured on Brahms p1
    tile 15: its left edge a hair inside the stem, its top ~0.2 spaces under
    the tip, one space wide and three tall."""
    return _det(name, STEM_X0 + 6, TIP_Y + dy * SP, 1.0 * SP, 3.0 * SP)


def _flag_down(name="flag8thDown"):
    """A down-stem's flag: the box hangs UP from the stem's bottom tip."""
    return _det(name, STEM_X0 + 6, FAR_Y - 0.22 * SP - 3.0 * SP, 1.0 * SP,
                3.0 * SP)


class TestAFlagBoxOnItsOwnStemDoesNotOccupyItsOwnTip(unittest.TestCase):
    """`gather._stem_tip_blockers(..., own_stem=)`."""

    def test_the_two_flag_boxes_of_one_flag_are_not_blockers_of_their_stem_RED(
            self):
        out = gather._stem_tip_blockers(
            [], [_flag_up("flag8thUp"), _flag_up("flag16thUp", dy=0.3)], SP,
            own_stem=STEM_BOX)
        self.assertEqual(out, [])

    def test_a_down_stems_flag_box_at_the_bottom_tip_is_its_own_too_RED(self):
        out = gather._stem_tip_blockers([], [_flag_down()], SP,
                                        own_stem=STEM_BOX)
        self.assertEqual(out, [])

    def test_CONTROL_without_own_stem_a_flag_box_still_blocks(self):
        """The legacy call is byte-identical: nothing is unblocked unless the
        caller says whose stem it is."""
        out = gather._stem_tip_blockers([], [_flag_up()], SP)
        self.assertEqual(len(out), 1)

    def test_CONTROL_a_flag_box_of_ANOTHER_stem_still_blocks(self):
        other = _det("flag8thUp", STEM_X1 + 2.0 * SP, TIP_Y + 8, 1.0 * SP,
                     3.0 * SP)
        out = gather._stem_tip_blockers([], [other], SP, own_stem=STEM_BOX)
        self.assertEqual(len(out), 1)

    def test_CONTROL_a_flag_box_far_below_this_stems_tip_is_not_its_own(self):
        """A flag standing mid-stem is another mark's (a neighbour's stem
        crossing this cell): its box does not start at THIS tip."""
        low = _det("flag8thUp", STEM_X0 + 6, TIP_Y + 1.5 * SP, 1.0 * SP,
                   3.0 * SP)
        out = gather._stem_tip_blockers([], [low], SP, own_stem=STEM_BOX)
        self.assertEqual(len(out), 1)

    def test_CONTROL_a_tie_box_over_the_tip_still_blocks_with_own_stem(self):
        tie = _det("tie", STEM_X0 - 10, TIP_Y + 0.5 * SP, 1.5 * SP, 1.0 * SP)
        out = gather._stem_tip_blockers([], [tie], SP, own_stem=STEM_BOX)
        self.assertEqual(len(out), 1)

    def test_CONTROL_a_beam_stroke_still_blocks_with_own_stem(self):
        beam = _det("beam", STEM_X0, TIP_Y, 4 * SP, 0.4 * SP)
        out = gather._stem_tip_blockers([beam], [], SP, own_stem=STEM_BOX)
        self.assertEqual(len(out), 1)

    def test_a_flag_box_and_a_tie_together_leave_exactly_the_tie_RED(self):
        tie = _det("tie", STEM_X0 - 10, TIP_Y + 0.5 * SP, 1.5 * SP, 1.0 * SP)
        out = gather._stem_tip_blockers([], [_flag_up(), tie], SP,
                                        own_stem=STEM_BOX)
        self.assertEqual(len(out), 1)


class TestTheHookIsCountedUnderTheFlagBox(unittest.TestCase):
    """The reader, end to end through `_observe_stem_tip_ink`."""

    def _cell(self, hooks=1):
        img = _paper()
        _stem(img)
        for k in range(hooks):
            _hook(img, TIP_Y + 3 + k * 0.7 * SP)
        return _Cell(img)

    def _top(self, log):
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        return rows.get("top"), abst.get("top")

    def _observe(self, cell, dets, *, own):
        log = Log()
        blockers = gather._stem_tip_blockers(
            [], dets, SP, **({"own_stem": STEM_BOX} if own else {}))
        gather._observe_stem_tip_ink(
            log, SUB, "cell:0", cell, "obs:stem-1", STEM_BOX, blockers, SP,
            heads=[(STEM_X0 - 40, FAR_Y - 10, 60.0, 50.0)])
        return self._top(log)

    def test_CONTROL_today_the_flag_boxes_make_the_tip_occupied(self):
        row, abst = self._observe(self._cell(),
                                  [_flag_up("flag8thUp"),
                                   _flag_up("flag16thUp")], own=False)
        self.assertIsNone(row)
        self.assertEqual(abst.reason, ABSTAIN.OCCUPIED)

    def test_with_the_flag_boxes_set_aside_the_tip_is_read_and_ONE_hook_counted_RED(
            self):
        row, abst = self._observe(self._cell(1),
                                  [_flag_up("flag8thUp"),
                                   _flag_up("flag16thUp")], own=True)
        self.assertIsNone(abst)
        self.assertTrue(row.value)
        self.assertEqual(row.detail["hooks"], 1)

    def test_two_drawn_hooks_are_counted_TWO_under_the_same_boxes_RED(self):
        """A real printed 16th: the ink says two, whatever the boxes say."""
        row, abst = self._observe(self._cell(2),
                                  [_flag_up("flag8thUp"),
                                   _flag_up("flag16thUp")], own=True)
        self.assertIsNone(abst)
        self.assertEqual(row.detail["hooks"], 2)

    def test_a_flag_box_over_a_BARE_stem_files_no_hook_RED(self):
        """⚠️ A box is not ink (rule 8): with nothing drawn at the tip the row
        reads NOT found and counts nothing -- the box never made a hook."""
        img = _paper()
        _stem(img)
        row, abst = self._observe(_Cell(img), [_flag_up()], own=True)
        self.assertIsNone(abst)
        self.assertFalse(row.value)
        self.assertNotIn("hooks", row.detail)


# ─────────────────────────────────────────────────────────────────────────────
# The CALL SITE: `gather_cv_lines` hands each stem its own blockers
# ─────────────────────────────────────────────────────────────────────────────

class TestTheCallSiteGivesEachStemItsOwnFlagBack(unittest.TestCase):
    """A synthetic cell through `gather.gather_cv_lines` itself: an up stem,
    its head, one drawn hook, and the detector's boxes. The wiring is where
    the real fault was (blockers computed once per CELL, never per stem)."""

    def _gather(self, dets):
        import cv2
        from tools.omr.tests.test_vertical_runs import _Cell, _local
        cell = _Cell()
        img = cell.image_no_staff
        img[40:170, 300:304] = 0                      # an up stem, tip y=40
        cv2.ellipse(img, (294, 170), (14, 10), -20, 0, 360, 0, -1)
        pts = np.array([[303, 40], [312, 52], [320, 70], [318, 86]], np.int32)
        cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=6)
        cell.image[:] = img
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        gather.gather_cv_lines(log, [cell], _local(), {sub.to_key(): dets})
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, sub)}
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, sub)}
        return rows.get("top"), abst.get("top"), len(log.rows(Q.STEM, sub))

    HEAD = _det("noteheadBlack", 280, 160, 28, 20)

    def _with_xy(self, d):
        d.x_center = d.x_canonical + d.width_canonical / 2.0
        d.y_center = d.y_canonical + d.height_canonical / 2.0
        return d

    def test_CONTROL_no_detector_boxes_the_hook_is_counted(self):
        row, abst, n = self._gather([self._with_xy(self.HEAD)])
        self.assertEqual(n, 1)
        self.assertEqual(row.detail["hooks"], 1)

    def test_two_flag_boxes_on_the_one_flag_still_leave_the_hook_counted_RED(
            self):
        dets = [self._with_xy(d) for d in (
            self.HEAD, _det("flag8thUp", 302, 44, 24, 60),
            _det("flag16thUp", 302, 46, 24, 58))]
        row, abst, n = self._gather(dets)
        self.assertEqual(n, 1)
        self.assertIsNone(abst)
        self.assertTrue(row.value)
        self.assertEqual(row.detail["hooks"], 1)

    def test_CONTROL_a_tie_box_over_the_tip_still_makes_it_occupied(self):
        dets = [self._with_xy(d) for d in (
            self.HEAD, _det("tie", 290, 50, 40, 30))]
        row, abst, n = self._gather(dets)
        self.assertEqual(n, 1)
        self.assertEqual(abst.reason, ABSTAIN.OCCUPIED)


# ═════════════════════════════════════════════════════════════════════════════
# PART B -- 2.74 review, Litolff 1: a row of heads' own ink is not a beam
# ═════════════════════════════════════════════════════════════════════════════
#
# Sean (2026-10-09, blind, `out/print/2.74-review/litolff_01.png`): printed
# EIGHTH; read 32nd before 2.74 and 16th after. The extra level is NOT a beamlet
# and not a slur: it is the CV opening's stroke over the ROW OF HEADS themselves
# (`glyph/3/0/7/6`, obs:036863, a 350 x 37 px stroke whose box lies 80 % inside
# the heads' boxes -- the second ledger line through them, fused with the heads,
# 1.08 spaces thick). It passes 2.74's three tests (thick, straight, a stem
# found at the heads' end). `_on_stem_side`'s own docstring names the fault and
# disowns it: *"A stroke lying THROUGH the head (the CV opening fuses a row of
# heads into one horizontal run) ... is a beam reader's false positive"*. A
# beam is drawn at the far end of its stems and runs BETWEEN them, never
# through a notehead (CLAUDE.md SS10).

from tools.omr.staged import adjudicate, evaluate                # noqa: E402,F401
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Outcome, READERS             # noqa: E402

from tools.omr.tests.test_staged_beam_two_stems import (         # noqa: E402
    _head_with_stem, _ink)
from tools.omr.tests.test_staged_duration import (               # noqa: E402
    CELL, _beam, _staff_space)


def _three_heads(log):
    """Three stemmed heads side by side, their stems rising to a beam line at
    y=38 -- the Litolff lower voice (heads 20 px wide, a gap of 10)."""
    _staff_space(log)
    return [_head_with_stem(log, gi, x)[0] for gi, x in enumerate((65, 95, 125))]


class TestAStrokeThroughTheHeadsIsNotTheirBeam(unittest.TestCase):

    def _litolff(self, log, *, row_ratio=3.9, row_y=91, row_x=(60, 150)):
        gs = _three_heads(log)
        primary = _beam(log, y=40, x0=60, x1=150)
        row = _beam(log, y=row_y, x0=row_x[0], x1=row_x[1])
        _ink(log, primary, ratio=2.4)
        _ink(log, row, ratio=row_ratio)
        return gs, primary, row

    def test_the_row_of_heads_is_refused_and_the_eighth_reads_eighth_RED(self):
        log = Log()
        gs, _p, _row = self._litolff(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"through_heads": 1})

    def test_it_is_refused_for_EVERY_head_of_the_row_RED(self):
        log = Log()
        gs, _p, _row = self._litolff(log)
        adjudicate.run(log)
        for g in gs:
            self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 0.5)

    def test_CONTROL_a_real_second_level_under_the_primary_stays_a_sixteenth(
            self):
        """A REAL printed 16th (two beams) is not touched: its second beam
        stands between the stems, 1.5 spaces above the heads."""
        log = Log()
        gs = _three_heads(log)
        a = _beam(log, y=40, x0=60, x1=150)
        b = _beam(log, y=54, x0=60, x1=150)
        _ink(log, a, ratio=2.4)
        _ink(log, b, ratio=2.4)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.25)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def test_CONTROL_a_dotted_eighth_and_sixteenth_beamlet_keeps_its_level(
            self):
        """The beamlet rule is untouched: a short secondary stroke on ONE
        stem beside the primary (one stem found at its end) still counts."""
        log = Log()
        gs = _three_heads(log)
        primary = _beam(log, y=40, x0=60, x1=150)
        beamlet = _beam(log, y=54, x0=60, x1=100)
        _ink(log, primary, ratio=2.4)
        _ink(log, beamlet, ratio=2.4, ends=(True, False))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.value["beats"], 0.25)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def test_CONTROL_a_stroke_beside_the_heads_but_not_through_them_stays(self):
        """The refusal is about covering the heads, not about being near
        them: a stroke 10 px above the head tops stays a level."""
        log = Log()
        gs = _three_heads(log)
        primary = _beam(log, y=40, x0=60, x1=150)
        near = _beam(log, y=76, x0=60, x1=150)
        _ink(log, primary, ratio=2.4)
        _ink(log, near, ratio=2.4)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.detail["beams_not_by_ink"], 0)
        self.assertEqual(v.value["beats"], 0.25)

    def test_the_refusal_needs_no_ink_row_the_boxes_are_enough_RED(self):
        """The heads and the stroke are both on the record; a stroke the
        thickness reader never measured is still the heads' ink."""
        log = Log()
        gs = _three_heads(log)
        primary = _beam(log, y=40, x0=60, x1=150)
        _beam(log, y=91, x0=60, x1=150)
        _ink(log, primary, ratio=2.4)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_REAL_beam_under_a_cluster_sized_false_head_box_stays_RED(self):
        """⚠️ Brahms p1 cell 1/0/0/4: the detector drew a `noteheadWholeOnLine`
        box 3.2 spaces wide over a real stem-down beam; the beam lies 0.9
        inside it. A box that is not head-SIZED is never evidence of where a
        head's ink is, so the beam stays and the eighth pair reads eighth."""
        log = Log()
        _staff_space(log)
        gs = []
        for gi, x in enumerate((65, 100)):
            g = R.glyph(0, 0, 0, 0, gi)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, 20, 20, 16),
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            from tools.omr.tests.test_staged_duration import _stem
            _stem(log, x=x, y=30, h=170)              # hangs to the beam at y=196
            gs.append(g)
        beam = _beam(log, y=196, x0=60, x1=120)
        # the false box: 3.2 spaces (51 px at SPACE=16) wide, straddling the beam
        fake = R.glyph(0, 0, 0, 0, 2)
        log.observe(fake, Q.GLYPH_BOX, ("noteheadWholeOnLine", 62, 180, 52, 30),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _ink(log, beam, ratio=3.0)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def test_CONTROL_the_same_box_head_SIZED_would_refuse_it(self):
        """The positive control for the size filter: the box is the only thing
        that changed (32 px = 2 spaces)."""
        log = Log()
        _staff_space(log)
        gs = []
        for gi, x in enumerate((65, 100)):
            g = R.glyph(0, 0, 0, 0, gi)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, 20, 20, 16),
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            from tools.omr.tests.test_staged_duration import _stem
            _stem(log, x=x, y=30, h=170)
            gs.append(g)
        beam = _beam(log, y=196, x0=60, x1=120)
        fake = R.glyph(0, 0, 0, 0, 2)
        log.observe(fake, Q.GLYPH_BOX, ("noteheadBlack", 62, 180, 32, 30),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _ink(log, beam, ratio=3.0)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"through_heads": 1})

    def test_without_a_staff_space_unit_the_rule_does_not_run(self):
        """No unit, no way to say what a head-sized box is: the stroke stays
        (rule 8 -- an unread test never refuses)."""
        log = Log()
        gs = [_head_with_stem(log, gi, x)[0] for gi, x in enumerate((65, 95, 125))]
        primary = _beam(log, y=40, x0=60, x1=150)
        row = _beam(log, y=91, x0=60, x1=150)
        _ink(log, primary, ratio=2.4)
        _ink(log, row, ratio=3.9)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertNotIn("through_heads",
                         (v.detail or {}).get("beams_not_by_ink_why", {}))

    def test_RULE_8_where_the_row_was_the_only_mark_the_head_is_narrowed_not_a_quarter_RED(
            self):
        log = Log()
        gs = _three_heads(log)
        row = _beam(log, y=91, x0=60, x1=150)
        _ink(log, row, ratio=3.9)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, gs[0])
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")


if __name__ == "__main__":
    unittest.main()
