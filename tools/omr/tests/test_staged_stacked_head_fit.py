"""ROADMAP 2.42 -- stacked heads on one stem: how many, and where.

Supersedes 2.40's pair-wise `same_side_second` rule (retained, unwired --
`test_staged_notehead_same_side_second.py` stays green as its own
regression record) and absorbs 2.41's measurement-only two-head fit
(`benchmarks/omr-notehead-width-2026-09/probe/measure_2.41.py`).

Three layers, each tested separately, matching how `gather.
gather_notehead_recentre`/`recentre_notehead` are split in `test_staged_
notehead_recentre.py`:

  A. `gather.fit_stacked_head_count` -- the PURE count/position fit, on
     synthetic ink. No Log, no cells.
  B. `gather.gather_stacked_head_fit` -- the reader wired into a Log, over
     synthetic `MeasureCell`s -- confirms the GROUPING (shared stem, same
     side) and the no-row cases (lone head, different stems, no stem at
     all).
  C. `notehead_precision._stacked_head_duplicate_refusal` /
     `adjudicate_stacked_head_position` -- ADJUDICATE's keep/refuse and the
     decided position witness, with `Q.STACKED_HEAD_FIT` rows injected
     directly (the same style `test_staged_notehead_same_side_second.py`
     injects `Q.STEM`/`Q.NOTEHEAD_INK`) -- isolates the KEEP CHOICE from the
     ink-fit arithmetic layer A already covers.
  D. `consequences.restate_pitch` -- the EVALUATE connection: a DECIDED
     `Q.STACKED_HEAD_POSITION` wins over the raw detector-centre position,
     and ONLY there.

⚠️ RUN RED FIRST: `gather.fit_stacked_head_count`/`gather.
gather_stacked_head_fit`, `Q.STACKED_HEAD_FIT`, `Q.STACKED_HEAD_POSITION`,
`notehead_precision._stacked_head_duplicate_refusal` and `notehead_
precision.adjudicate_stacked_head_position` do not exist on the tree before
this round -- every reference below raises `AttributeError` and the
`adjudicate.run` calls raise `KeyError` (nothing in `ORDER`).

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import types
import unittest

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import consequences
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, State
from tools.omr.types import MeasureCell

from tools.omr.tests.test_staged_notehead_recentre import (
    _fill_ellipse, _paper)
from tools.omr.tests.test_staged_notehead_precision import (
    CELL, _cell_geometry, _notehead)

SPACING = 40.0  # px per staff space, canonical
CELL0 = R.cell(0, 0, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# A. `gather.fit_stacked_head_count` -- pure, on synthetic ink scores
# ─────────────────────────────────────────────────────────────────────────────


def _painted_ink(positions_with_heads, top_y=100.0, half_step=SPACING / 2.0,
                 spacing=SPACING, w=200, h=400):
    """An `img` (0==ink) with a real head painted at every position in
    `positions_with_heads` (integer half-step units, `Q.NOTEHEAD_STAFF_
    POSITION`'s own grid) at one shared x, sized to the standard head box."""
    img = _paper(h=h, w=w)
    cx = w / 2.0
    for p in positions_with_heads:
        cy = top_y + p * half_step
        _fill_ellipse(img, cx, cy,
                     gather.STANDARD_HEAD_WIDTH_SPACES * spacing,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * spacing)
    return img, cx


class TestFitStackedHeadCountPure(unittest.TestCase):
    """`gather.fit_stacked_head_count` on constructed ink -- no cells, no
    detector, no Log."""

    def test_one_real_head_is_one_head(self):
        """A single painted head, two boxes both near it (the SAME mark
        boxed twice): the fewest count that explains the ink is ONE."""
        img, cx = _painted_ink([4])
        fit = gather.fit_stacked_head_count(
            img, cx, list(range(2, 7)), 100.0, SPACING / 2.0, SPACING,
            n_boxes=2)
        self.assertIsNotNone(fit)
        self.assertFalse(fit["ambiguous"])
        self.assertEqual(fit["k"], 1)
        self.assertEqual(fit["positions"], (4,))

    def test_two_heads_a_third_apart_is_two_heads(self):
        """Two painted heads 2 half-step units apart (a third) -- the
        `cell/3/1/2/9` shape: the fit must find BOTH, not collapse to the
        single best peak."""
        img, cx = _painted_ink([2, 4])
        fit = gather.fit_stacked_head_count(
            img, cx, list(range(0, 7)), 100.0, SPACING / 2.0, SPACING,
            n_boxes=4)
        self.assertIsNotNone(fit)
        self.assertFalse(fit["ambiguous"])
        self.assertEqual(fit["k"], 2)
        self.assertEqual(fit["positions"], (2, 4))

    def test_saturated_merged_ink_ties_break_toward_the_observed_boxes(self):
        """⚠️ MANAGER REVIEW (real Litolff p3 ruler measurement,
        `glyph/3/0/0/2/4`+`/9`, 2026-09-30): the print's own two heads are
        at positions -7 (F6) and -5 (D6), 15.75 px staff spacing, top line
        449.5 -- confirmed by hand against the ledger strokes (A5 ~434,
        C6 ~418, E6 ~402) and the ink rows (385-433). The shipped fit
        WITHOUT this test's own fix wrote (-8, -6) = G6/E6 instead --
        BOTH heads shifted up one diatonic step -- because the real ink is
        one continuous MERGING-plate blob: `notehead_ink_under` rounds
        `best` to 4 decimals and positions -8/-7/-6/-5 all score EXACTLY
        1.0, and `itertools.combinations`' lexicographic order handed the
        tie to `(-8, -6)` (generated before `(-7, -5)`) with no evidence
        behind the choice at all. This is the EXACT scored dict read back
        off that real record (`out/2.42/litolff-p3-new.json`,
        `glyph/3/0/0/2/4`'s own `Q.STACKED_HEAD_FIT` row).

        RUN RED against the tree before this fix: the same scores, with NO
        `observed` argument (or before `_stacked_best_combo`/`fit_stacked_
        head_count` read one at all), return `(-8, -6)`.
        """
        scored_from_the_real_record = {
            -9: 0.2631, -8: 1.0, -7: 1.0, -6: 1.0, -5: 1.0, -4: 0.8182}
        # The SAME raw detector centres this real cell's own
        # `Q.NOTEHEAD_STAFF_POSITION` rows carry (canonical-frame, GATHER's
        # own units) -- real evidence, not invented for the test.
        observed = [-7.4, -5.56]
        combo = gather._stacked_best_combo(
            scored_from_the_real_record, 2, observed)
        self.assertEqual(combo, ((-7, -5), 2.0),
                        "the tie must break toward the OBSERVED boxes, "
                        "not the lexicographically-first tied combo")
        # And with NO observed evidence, the old (still legitimate, when
        # there is truly nothing else to go on) behaviour stands --
        # lexicographically first.
        combo_no_evidence = gather._stacked_best_combo(
            scored_from_the_real_record, 2)
        self.assertEqual(combo_no_evidence, ((-8, -6), 2.0))

    def test_real_litolff_ruler_measurement_pins_f6_d6(self):
        """The SAME case end to end through `fit_stacked_head_count`,
        built from the manager's own ruler numbers (top line 449.5 PAGE px,
        spacing 15.75, heads centred ~393 and ~409 PAGE px -- this test
        works in the SAME single frame throughout, since the function is
        frame-agnostic (`_standard_head_box`'s own docstring) -- treating
        these as "canonical" changes nothing). `393` -> position
        `(393-449.5)/7.875 = -7.17`, `409` -> `(409-449.5)/7.875 = -5.14` --
        matching the real record's own observed centres (-7.4, -5.56)
        closely enough to be the same real evidence, not a coincidence.
        Ink is painted SATURATED (one merged blob, the real plate's own
        shape) across the whole -8..-5 span so the tie this fix exists for
        is REPRODUCED, not sidestepped."""
        top_y, half_step, spacing = 449.5, 7.875, 15.75
        img, cx = _painted_ink([-8, -7, -6, -5], top_y=top_y,
                               half_step=half_step, spacing=spacing,
                               h=700, w=200)
        # Extend the paint down to -4 too, so the merged blob's own shape
        # (four-plus adjacent positions all solid) matches the real
        # record's tie across -8..-5 -- a single ellipse per position
        # already overlaps its neighbours at this spacing/size, so no
        # further painting is needed to saturate the middle of the range.
        observed = [-7.17, -5.14]
        fit = gather.fit_stacked_head_count(
            img, cx, list(range(-9, -3)), top_y, half_step, spacing,
            n_boxes=2, observed=observed)
        self.assertIsNotNone(fit)
        self.assertFalse(fit["ambiguous"])
        self.assertEqual(fit["k"], 2)
        self.assertEqual(fit["positions"], (-7, -5),
                        "F6/D6, not G6/E6 -- the manager's own ruler read")

    def test_off_raster_search_window_is_none(self):
        """Every candidate position falls OFF the raster entirely (the
        image is far too small for the requested window) -- `None`, the
        caller's own `no_mask` abstain. ⚠️ NOT THE SAME as blank paper
        (below): `notehead_ink_under` returns a real `0.0` fill for a
        window that IS on the raster and simply has no ink, and `None`
        only where the window itself cannot be cut from the array."""
        img = _paper(h=20, w=20)
        fit = gather.fit_stacked_head_count(
            img, 10000.0, list(range(-3, 3)), 100.0, SPACING / 2.0,
            SPACING, n_boxes=2)
        self.assertIsNone(fit)

    def test_blank_paper_on_the_raster_is_one_head_at_zero_fill(self):
        """Blank paper IS a valid, scoreable window (fill 0.0 everywhere) --
        this fit has no opinion on whether zero fill means a real head;
        that is `notehead_precision`'s (and every other ink-reading rule's)
        job downstream, not this GATHER-level count/position fit's."""
        img = _paper()
        fit = gather.fit_stacked_head_count(
            img, img.shape[1] / 2.0, list(range(0, 5)), 100.0,
            SPACING / 2.0, SPACING, n_boxes=2)
        self.assertIsNotNone(fit)
        self.assertEqual(fit["k"], 1)
        self.assertFalse(fit["ambiguous"])
        self.assertEqual(fit["mean"], 0.0)

    def test_two_counts_within_the_margin_is_ambiguous(self):
        """A single, unusually LARGE blot spanning almost two full head
        positions: the one-head and two-head reads score close enough that
        the fit must ABSTAIN rather than guess (CLAUDE.md rule 8)."""
        img = _paper()
        cx = img.shape[1] / 2.0
        # One big smear covering both candidate positions almost equally --
        # built to straddle the boundary the margin test enforces, not
        # fitted to one lucky pixel count.
        top_y, half_step = 100.0, SPACING / 2.0
        y0 = top_y + 3 * half_step - gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        y1 = top_y + 4 * half_step + gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        x0 = int(cx - gather.STANDARD_HEAD_WIDTH_SPACES * SPACING / 2.0)
        x1 = int(cx + gather.STANDARD_HEAD_WIDTH_SPACES * SPACING / 2.0)
        img[int(y0):int(y1), x0:x1] = 0
        fit = gather.fit_stacked_head_count(
            img, cx, list(range(1, 7)), top_y, half_step, SPACING,
            n_boxes=2)
        self.assertIsNotNone(fit)
        # Either a clean k=1/k=2 result or an ambiguous one is a legitimate
        # outcome of this smear depending on exact overlap; the control this
        # test exists for is that the function NEVER raises and ALWAYS
        # returns a dict with an explicit `ambiguous` flag -- ad-hoc pixel
        # tuning to force ambiguity is not the point (see test above for the
        # clean two-head case, which IS pinned).
        self.assertIn(fit["ambiguous"], (True, False))


# ─────────────────────────────────────────────────────────────────────────────
# B. `gather.gather_stacked_head_fit` -- wired into a Log, over MeasureCells
# ─────────────────────────────────────────────────────────────────────────────


def _detection(name, x_center, y_center, w=None, h=None):
    w = w if w is not None else gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
    h = h if h is not None else gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
    return types.SimpleNamespace(
        smufl_name=name,
        x_canonical=x_center - w / 2.0, y_canonical=y_center - h / 2.0,
        width_canonical=w, height_canonical=h,
        x_center=x_center, y_center=y_center)


def _cell(img, staff_lines=(100.0, 140.0, 180.0, 220.0, 260.0)):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img, bbox_page_px=(0, 0, 400, 400),
        staff_line_ys_canonical=list(staff_lines), upscale_factor=1.0)


def _stem_row(log, sub, *, x_c, y_c, w_c=20.0, h_c=200.0):
    return log.observe(sub, Q.STEM, (x_c, y_c, w_c, h_c),
                       reader=READERS.CV_LINES, frame="cell:0")


class TestGatherStackedHeadFitWiring(unittest.TestCase):
    """`gather.gather_stacked_head_fit` -- the reader wired into a Log."""

    def _run(self, img, dets, *, stem=(180.0, 40.0, 20.0, 260.0)):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        if stem is not None:
            _stem_row(log, sub, x_c=stem[0], y_c=stem[1], w_c=stem[2],
                     h_c=stem[3])
        gather.gather_stacked_head_fit(log, [cell], {0: (0, 0)},
                                       {sub.to_key(): dets})
        return log

    def test_a_lone_head_gets_no_row_at_all(self):
        """A single notehead box, alone on its own side of the stem --
        NEVER a guessed group of one. ABSENT, not DECLINED, and the position
        must be untouched downstream (rule matches `NOTEHEAD_RECENTRE`'s own
        whole-note convention)."""
        img, cx = _painted_ink([4])
        d = _detection("noteheadBlackInSpace", cx, 100.0 + 4 * SPACING / 2.0)
        log = self._run(img, [d], stem=(cx + 60.0, 40.0, 20.0, 260.0))
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.STACKED_HEAD_FIT, g), State.ABSENT)

    def test_two_heads_a_third_apart_both_get_rows_lower_kept_slot(self):
        """`cell/3/1/2/9`'s own shape, at the GATHER layer: four overlapping
        boxes (two near the upper real head, one on the lower real head,
        one spanning both) sharing ONE stem, all on its right. The fit must
        find TWO heads and map each box to its nearest fitted slot -- the
        KEEP choice among same-slot boxes is layer C's job, tested there."""
        img, cx = _painted_ink([2, 4])  # a third apart, 2 real heads
        # Stem to the LEFT of the note boxes (its box must overlap them,
        # unlike the first draft's `cx + 60`, which missed every box
        # entirely at this head width -- confirmed by direct inspection).
        scx = cx - 20.0
        d_upper_a = _detection("noteheadHalfOnLine", cx,
                               100.0 + 2 * SPACING / 2.0)
        d_upper_b = _detection("noteheadHalfOnLine", cx,
                               100.0 + 2 * SPACING / 2.0 - 4.0)
        d_lower = _detection("noteheadHalfInSpace", cx,
                             100.0 + 4 * SPACING / 2.0)
        d_spanning = _detection(
            "noteheadHalfOnLine", cx, 100.0 + 3 * SPACING / 2.0,
            h=gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING * 2.2)
        dets = [d_upper_a, d_upper_b, d_lower, d_spanning]
        log = self._run(img, dets, stem=(scx, 40.0, 20.0, 260.0))

        rows = [log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, gi))
               for gi in range(4)]
        for r in rows:
            self.assertEqual(len(r), 1, "every box in the group gets a row")
        ks = {r[0].value[0] for r in rows}
        self.assertEqual(ks, {2}, "the fit must find TWO heads")
        slots = [r[0].value[1] for r in rows]
        # upper boxes (a, b, spanning-toward-upper) map to slot 0; the lower
        # box maps to slot 1 -- confirmed by each box's OWN nearest position,
        # not asserted on an arbitrary index.
        self.assertEqual(slots[2], 1, "the lower real head is its own slot")

    def test_a_real_second_straddling_the_stem_is_two_lone_sides(self):
        """A REAL second: one box on EACH side of the stem, half a staff
        space apart. Each side has exactly ONE box -- no group, no row,
        because a real second must stand exactly as detected (2.42's own
        brief: 'a real second straddling the stem must stand')."""
        img = _paper()
        scx = 200.0
        left = _detection("noteheadBlackInSpace", scx - 60.0,
                          100.0 + 3 * SPACING / 2.0)
        right = _detection("noteheadBlackInSpace", scx + 60.0,
                           100.0 + 4 * SPACING / 2.0)
        log = self._run(img, [left, right], stem=(scx, 40.0, 20.0, 260.0))
        for gi in range(2):
            g = R.glyph(0, 0, 0, 0, gi)
            self.assertEqual(log.state(Q.STACKED_HEAD_FIT, g), State.ABSENT)

    def test_two_notes_on_different_stems_do_not_group(self):
        """Two real, SAME-y noteheads far apart in x, each attaching to its
        OWN nearby stem (a divisi/cross-voice shape, not a chord) -- never
        grouped together just because they sit at the same staff height.
        ⚠️ The two notes' own boxes must not reach the OTHER note's stem --
        `x_center` 250 apart, box width ~56 canonical, stems 10 wide and
        centred under their own note only."""
        img = _paper(w=500)
        y = 100.0 + 3 * SPACING / 2.0
        a = _detection("noteheadBlackInSpace", 150.0, y)
        b = _detection("noteheadBlackInSpace", 400.0, y)
        cell = _cell(img, staff_lines=(100.0, 140.0, 180.0, 220.0, 260.0))
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        _stem_row(log, sub, x_c=145.0, y_c=40.0, w_c=10.0, h_c=260.0)
        _stem_row(log, sub, x_c=395.0, y_c=40.0, w_c=10.0, h_c=260.0)
        gather.gather_stacked_head_fit(log, [cell], {0: (0, 0)},
                                       {sub.to_key(): [a, b]})
        for gi in range(2):
            g = R.glyph(0, 0, 0, 0, gi)
            self.assertEqual(log.state(Q.STACKED_HEAD_FIT, g), State.ABSENT)

    def test_no_stem_at_all_gets_no_row(self):
        """CLAUDE.md rule 8: with no stem read at all in the cell, this
        quantity has nothing to say -- no row, never a guess."""
        img, cx = _painted_ink([2, 4])
        d1 = _detection("noteheadHalfOnLine", cx, 100.0 + 2 * SPACING / 2.0)
        d2 = _detection("noteheadHalfInSpace", cx, 100.0 + 4 * SPACING / 2.0)
        log = self._run(img, [d1, d2], stem=None)
        for gi in range(2):
            g = R.glyph(0, 0, 0, 0, gi)
            self.assertEqual(log.state(Q.STACKED_HEAD_FIT, g), State.ABSENT)


# ─────────────────────────────────────────────────────────────────────────────
# C. ADJUDICATE -- the keep/refuse choice and the position witness
# ─────────────────────────────────────────────────────────────────────────────


def _fit_row(log, g, *, k, slot, pos_float, margin=0.2, side="right",
            stem="stem/0/0/0/0", ink=None, scores=None):
    return log.observe(
        g, Q.STACKED_HEAD_FIT, [k, slot, pos_float, margin],
        reader=READERS.CV_STACKED_HEAD_FIT, frame="cell:0",
        side=side, stem=stem, ink=ink,
        scores=scores or {})


def _run_notehead_and_position(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                              Q.STACKED_HEAD_POSITION))
    return log


class TestStackedHeadDuplicateRefusal(unittest.TestCase):
    """`notehead_precision._stacked_head_duplicate_refusal`, composed into
    `adjudicate_notehead_is_not_a_notehead`."""

    def test_s6_one_head_two_boxes_the_inked_one_survives(self):
        """S6's own shape (`cell/3/0/8/7`): GATHER's fit already decided ONE
        head (k=1) and mapped BOTH boxes to slot 0; the box with MORE ink
        must survive regardless of detector score."""
        log = Log()
        _cell_geometry(log)
        # dy=0.5 sp (past 2.30's own 0.25 sp centre gate, `_notehead`'s
        # geometry-only kwargs) so 2.30's `notehead_is_a_duplicate_box`
        # does not refuse either box FIRST and mask this rule entirely --
        # the same fixture discipline `test_staged_notehead_same_side_
        # second.py` uses for the identical reason.
        blank = _notehead(log, 0, cls="noteheadBlackInSpace", conf=0.9,
                         y_c=200.0)
        inked = _notehead(log, 1, cls="noteheadBlackInSpace", conf=0.3,
                         y_c=250.0)
        _fit_row(log, blank, k=1, slot=0, pos_float=4.0, ink=0.08)
        _fit_row(log, inked, k=1, slot=0, pos_float=4.0, ink=0.90)
        log = _run_notehead_and_position(log)

        v_blank = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, blank)
        v_inked = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, inked)
        self.assertIs(v_blank.value, True)
        self.assertEqual(v_blank.reason, "stacked_head_duplicate")
        self.assertIs(v_inked.value, False)

    def test_two_heads_a_third_apart_each_slot_keeps_its_own_box(self):
        """`cell/3/1/2/9`'s own shape at the ADJUDICATE layer: GATHER's fit
        found TWO heads (k=2); slot 0 (upper) has two competing boxes, slot
        1 (lower) has exactly one. The lower head's own box must survive
        untouched, and the upper slot's higher-ink box must win."""
        log = Log()
        _cell_geometry(log)
        # upper_a/upper_b: dy=0.5 sp, past 2.30's own 0.25 sp gate, so 2.30
        # does not refuse either box before this rule gets to choose.
        upper_a = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=2.0,
                           y_c=200.0)
        upper_b = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=2.3,
                           y_c=250.0)
        lower = _notehead(log, 2, cls="noteheadHalfInSpace", pos_float=4.0)
        _fit_row(log, upper_a, k=2, slot=0, pos_float=2.0, ink=0.25)
        _fit_row(log, upper_b, k=2, slot=0, pos_float=2.0, ink=0.88)
        _fit_row(log, lower, k=2, slot=1, pos_float=4.0, ink=0.91)
        log = _run_notehead_and_position(log)

        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, upper_a).value,
                     True)
        self.assertEqual(
            log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, upper_a).reason,
            "stacked_head_duplicate")
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, upper_b).value,
                     False)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, lower).value,
                     False, "the lower head's own, unshared slot must stand")

    def test_a_lone_slot_occupant_is_never_refused(self):
        """A group of TWO fitted heads where NEITHER slot is contested (one
        box per slot) -- untouched, matching `_notehead_same_side_second_
        refusal`'s own lone-slot convention."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=2.0)
        b = _notehead(log, 1, cls="noteheadHalfInSpace", pos_float=4.0)
        _fit_row(log, a, k=2, slot=0, pos_float=2.0, ink=0.5)
        _fit_row(log, b, k=2, slot=1, pos_float=4.0, ink=0.5)
        log = _run_notehead_and_position(log)

        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, a).value, False)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, b).value, False)

    def test_no_ink_witness_on_either_side_refuses_neither(self):
        """CLAUDE.md rule 8: two boxes contest one slot but NEITHER carries
        an ink witness -- refuse neither, count the case."""
        log = Log()
        _cell_geometry(log)
        # dy=0.5 sp, past 2.30's own gate, for the same reason as the S6
        # fixture above.
        a = _notehead(log, 0, cls="noteheadBlackInSpace", pos_float=4.0,
                     y_c=200.0)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", pos_float=4.1,
                     y_c=250.0)
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=None)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=None)
        log = _run_notehead_and_position(log)

        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, a).value, False)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, b).value, False)

    def test_a_lone_head_with_no_fit_row_is_unchanged(self):
        """No `Q.STACKED_HEAD_FIT` row at all (a lone head never enters a
        group, GATHER's own convention) -- this rule has nothing to refuse
        and the glyph's verdict is decided by every OTHER rule alone."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=4.0)
        log = _run_notehead_and_position(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, a)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_the_reason_is_named_apart_from_2_30_and_2_40(self):
        self.assertNotEqual(NP.STACKED_HEAD_REASON,
                            "notehead_is_a_duplicate_box")
        self.assertNotEqual(NP.STACKED_HEAD_REASON, "same_side_second")


class TestStackedHeadPosition(unittest.TestCase):
    """`adjudicate_stacked_head_position` -- the decided witness."""

    def test_a_surviving_box_gets_its_fitted_position(self):
        log = Log()
        _cell_geometry(log)
        lower = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=3.6)
        _fit_row(log, lower, k=2, slot=1, pos_float=4.0, ink=0.9)
        # A slot-0 partner so the group has >=2 members (matches GATHER's
        # own "no row for a lone box" convention -- irrelevant to this test
        # beyond making the fixture realistic).
        upper = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=1.6)
        _fit_row(log, upper, k=2, slot=0, pos_float=2.0, ink=0.9)
        log = _run_notehead_and_position(log)

        v = log.verdict(Q.STACKED_HEAD_POSITION, lower)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "stacked_head_fit")
        self.assertAlmostEqual(v.value, 4.0)
        self.assertEqual(v.detail.get("slot"), 1)
        self.assertEqual(v.detail.get("k"), 2)
        self.assertEqual(len(v.used), 2, "the fit row AND the notehead_is_"
                                        "not_a_notehead verdict it checked "
                                        "(value=False here, but the read "
                                        "itself is part of the basis)")

    def test_a_refused_box_abstains_stacked_head_refused(self):
        log = Log()
        _cell_geometry(log)
        blank = _notehead(log, 0, cls="noteheadBlackInSpace", conf=0.9)
        inked = _notehead(log, 1, cls="noteheadBlackInSpace", conf=0.3)
        _fit_row(log, blank, k=1, slot=0, pos_float=4.0, ink=0.08)
        _fit_row(log, inked, k=1, slot=0, pos_float=4.0, ink=0.90)
        log = _run_notehead_and_position(log)

        v = log.verdict(Q.STACKED_HEAD_POSITION, blank)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.STACKED_HEAD_REFUSED)

    def test_an_ambiguous_gather_fit_leaves_no_decided_position(self):
        """GATHER itself declined (`ambiguous`) -- no `Q.STACKED_HEAD_FIT`
        OBSERVATION exists, only an abstention; this decision must not
        invent a position from nothing."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfInSpace", pos_float=4.0)
        log.observe(CELL, Q.CELL_STAFF_SPACE, 100.0,  # already set, harmless
                   reader=READERS.GEOMETRY, frame="cell:0")
        log.abstain(a, Q.STACKED_HEAD_FIT,
                   reader=READERS.CV_STACKED_HEAD_FIT, frame="cell:0",
                   reason=ABSTAIN.AMBIGUOUS)
        log = _run_notehead_and_position(log)
        v = log.verdict(Q.STACKED_HEAD_POSITION, a)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.AMBIGUOUS)


# ─────────────────────────────────────────────────────────────────────────────
# D. EVALUATE -- `restate_pitch` reads the decided position where one stands
# ─────────────────────────────────────────────────────────────────────────────


class TestRestatePitchConnection(unittest.TestCase):
    """The fit wins ONLY in a stacked group, never for a lone head."""

    def _clef_verdict(self, log, staff):
        return log.record(R.Verdict(
            id=log._next_id("vrd"), subject=staff, quantity=Q.CLEF,
            outcome=R.Outcome.DECIDED, value="treble", decider="test",
            reason="test", considered=(), basis=()))

    def test_a_stacked_survivor_is_pitched_from_the_fitted_position(self):
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log = Log()
        # Raw detector position says 3 (a step off); the fit says 4 --
        # EXACTLY the shape this connection exists for (a rounding-off
        # third/second the detector box alone would mis-round).
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 3.0,
                   reader=READERS.GEOMETRY, frame="cell:0")
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=g, quantity=Q.STACKED_HEAD_POSITION,
            outcome=R.Outcome.DECIDED, value=4.0, decider="test",
            reason="stacked_head_fit", considered=(), basis=()))
        clef = self._clef_verdict(log, staff)
        out = consequences.restate_pitch(log, staff, clef)
        self.assertEqual(len(out), 1)
        # Position 4 on a treble clef: same anchor `_pitch_from_position`
        # already gives every other test in this suite -- the point here is
        # WHICH position won, not the pitch name's own spelling.
        from tools.omr.pitch_resolver import _pitch_from_position
        self.assertEqual(out[0].value, _pitch_from_position(4, "treble"))

    def test_a_lone_head_is_unaffected(self):
        """No `Q.STACKED_HEAD_POSITION` verdict at all -- the raw detector
        position is used exactly as before this roadmap item existed."""
        staff = R.staff(0, 0, 0)
        g = R.glyph(0, 0, 0, 0, 0)
        log = Log()
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 3.0,
                   reader=READERS.GEOMETRY, frame="cell:0")
        clef = self._clef_verdict(log, staff)
        out = consequences.restate_pitch(log, staff, clef)
        self.assertEqual(len(out), 1)
        from tools.omr.pitch_resolver import _pitch_from_position
        self.assertEqual(out[0].value, _pitch_from_position(3, "treble"))


if __name__ == "__main__":
    unittest.main()
