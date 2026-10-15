"""ROADMAP 2.126 -- the real beam / flag cases split out of 2.121 (Brahms 317803 pdf 0, Sean's hand truth).

Four mechanisms, each behind its own flag, default OFF. Every one is a GATHER reader repair: the reading was lost where the staff-line ERASE
(or a neighbouring stroke) cut a mark that is one stroke on the page.

  * `OMR_BEAM_JOIN_LINE_BRIDGE` (q86/q93, `beam_certain_not_joined`): a stem that crosses a staff line is one stroke; the erase wiped its pixels
    in the line band and thinned the stem on both flanks, so the join walk saw a 46 px blank run against a 21.7 px tolerance. With the band's rows
    set aside each flank is measured alone.
  * `OMR_HOOKS_LINE_BRIDGE` (q1009, `flag_ink_unread`): a ledger or staff line that crosses the hook band is a SECOND "run", counted as a second
    hook (support 0.367 against the 0.12 glitch cut). A run that is nothing but line rows is not a hook.
  * `OMR_STEM_FINDER=thin_run_stack` (q110/q118, no stem found): the stem fused with a stacked-head column protrudes 75 px (0.75 space) beyond
    the heads' columns; the shipped cut is 80.
  * `OMR_STEM_FINDER=pair_flag_curve` (Brahms p6 sys0 staff11 cell5, bar 102): the stem was condemned as the "second stroke of an accidental"
    by the flag's own curve, a vertical stroke wholly inside the detector's flag box.

RED FIRST: every positive test below fails on main (the function or keyword does not exist, or the shipped reader returns the unrepaired
result); every refusal has a positive control in the same class (CLAUDE.md 6b).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import cv2
import numpy as np

from tools.omr.line_detection import detect_stems
from tools.omr.staged import gather
from tools.omr.types import MeasureCell

SP = 100.0
LINE_YS = [100, 200, 300, 400, 500]
TOL = 21.7                     # the cell's measured line thickness: the join's gap tolerance (px)


def _paper(h=900, w=900):
    return np.full((h, w), 255, dtype=np.uint8)


def _rect(img, x0, y0, x1, y1):
    img[int(y0):int(y1), int(x0):int(x1)] = 0


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 1. beam join through a staff line (q86 / q93)
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
STEM_X0, STEM_X1 = 300.0, 308.0
TIP_Y = 480.0
BEAM = dict(stroke_x0=200.0, stroke_x1=500.0, stroke_y0=620.0, stroke_y1=660.0)


def _stem_through_a_line(gap_above=20, gap_below=20, line=(500, 511)):
    """The ERASED image: the stem ends at TIP_Y, is blank across `gap_above` rows, the erased line band, `gap_below` rows, then runs on to
    the beam. The RAW image: the staff line fills the whole row across the band; the stem's flanks carry the same breaks."""
    erased, raw = _paper(), _paper()
    top_blank = line[0] - gap_above
    bot_blank = line[1] + gap_below
    _rect(erased, STEM_X0, 300, STEM_X1, top_blank)          # stem above its first break
    _rect(erased, STEM_X0, bot_blank, STEM_X1, 620)           # stem below its second break, to the beam
    _rect(erased, BEAM["stroke_x0"], 620, BEAM["stroke_x1"], 660)
    _rect(raw, STEM_X0, 300, STEM_X1, top_blank)
    _rect(raw, STEM_X0, bot_blank, STEM_X1, 620)
    _rect(raw, BEAM["stroke_x0"], 620, BEAM["stroke_x1"], 660)
    _rect(raw, 100, line[0], 800, line[1])                    # the staff line, wall to wall
    return erased, raw


def _join(erased, raw=None, tip_y=None, **kw):
    tip = TIP_Y if tip_y is None else tip_y
    args = (erased, STEM_X0, STEM_X1, tip, "bottom", BEAM["stroke_x0"], BEAM["stroke_x1"], BEAM["stroke_y0"], BEAM["stroke_y1"], TOL)
    if raw is None:
        return gather.beam_stem_join_ink(*args)
    rows = gather.line_rows_across_stem(raw < 128, STEM_X0, STEM_X1, SP, 300, 620)
    return gather.beam_stem_join_ink(*args, line_rows=rows, **kw)


class TestBeamJoinThroughAStaffLine(unittest.TestCase):

    def test_the_shipped_reader_calls_a_stem_cut_by_the_erase_NOT_joined(self):
        erased, _ = _stem_through_a_line()
        m = _join(erased)
        self.assertFalse(m["found"])
        self.assertGreater(m["max_blank_run_px"], TOL)          # 51 rows of blank against 21.7

    def test_RED_with_the_line_rows_set_aside_each_flank_is_measured_alone_and_the_stem_is_joined(self):
        erased, raw = _stem_through_a_line()
        m = _join(erased, raw)
        self.assertTrue(m["found"])
        self.assertLessEqual(m["line_bridge"]["max_blank_off_line_px"], TOL)
        self.assertGreaterEqual(m["line_bridge"]["rows_set_aside"], 10)

    def test_CONTROL_a_flank_break_wider_than_the_tolerance_is_still_NOT_joined(self):
        erased, raw = _stem_through_a_line(gap_above=20, gap_below=40)
        self.assertFalse(_join(erased, raw)["found"])

    def test_CONTROL_a_real_gap_with_no_staff_line_in_it_is_still_NOT_joined(self):
        erased, raw = _stem_through_a_line()
        # the same blank run, but the raw page holds NO line there: nothing to set aside
        raw2 = raw.copy()
        raw2[500:511, 100:800] = 255
        self.assertFalse(_join(erased, raw2)["found"])

    def test_the_off_path_returns_the_same_keys_as_before(self):
        erased, _ = _stem_through_a_line()
        self.assertNotIn("line_bridge", _join(erased))

    def test_the_flag_is_off_by_default_and_a_typo_leaves_it_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(gather.BEAM_JOIN_LINE_BRIDGE_ENV, None)
            self.assertFalse(gather.beam_join_line_bridge_enabled())
        for typo in ("", "yess", "ON!", "2"):
            with mock.patch.dict(os.environ, {gather.BEAM_JOIN_LINE_BRIDGE_ENV: typo}):
                self.assertFalse(gather.beam_join_line_bridge_enabled(), typo)
        with mock.patch.dict(os.environ, {gather.BEAM_JOIN_LINE_BRIDGE_ENV: "1"}):
            self.assertTrue(gather.beam_join_line_bridge_enabled())


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2. the hook count past a ledger / staff line (q1009)
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
H_SP = 40.0
H_X0, H_X1 = 300.0, 306.0
H_TIP_UP, H_FAR = 400.0, 100.0      # a DOWN stem: tip at the bottom (y=400), head far above


def _one_hook_and_a_ledger():
    """The CV image (what the counter reads) holds a thick line piece attached to the stem's RIGHT only -- the shape the shipped
    `_tip_line_rows` does not set aside (real q1009: 28 rows of ledger line, 5 of them classed `on_line`); the RAW page shows the same line
    crossing the stem on BOTH sides, which is what `line_rows_across_stem` reads."""
    img = _paper(500, 600)
    _rect(img, H_X0, H_FAR, H_X1, H_TIP_UP)                                    # the stem
    pts = np.array([[H_X1 - 2, H_TIP_UP - 3], [H_X1 + 0.5 * H_SP, H_TIP_UP - 0.5 * H_SP],
                    [H_X1 + 0.85 * H_SP, H_TIP_UP - 1.5 * H_SP], [H_X1 + 0.8 * H_SP, H_TIP_UP - 2.1 * H_SP]], np.int32)
    cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=int(round(0.4 * H_SP)))
    raw = img.copy()
    _rect(img, 306, 255, 340, 275)                                              # the line piece the counter sees: right of the stem only
    _rect(raw, 250, 255, 420, 275)                                              # the raw page: the line runs through, far past any flag
    return img, raw


def _count(img, raw=None):
    kw = {}
    if raw is not None:
        kw["line_rows"] = gather.line_rows_past_flag(raw < 128, H_X1, H_SP, 0, img.shape[0])
    return gather.stem_tip_hooks(img, H_X0, H_X1, H_TIP_UP, -1.0, H_SP, **kw)


class TestAHookBesideALine(unittest.TestCase):

    def test_the_shipped_counter_cannot_tell_one_hook_from_two_when_a_ledger_line_crosses_the_band(self):
        img, _ = _one_hook_and_a_ledger()
        r = _count(img)
        self.assertIsNone(r["hooks"])
        self.assertEqual((r["hooks_min"], r["hooks_max"]), (1, 2))

    def test_RED_a_run_that_is_only_line_rows_is_not_a_hook_and_the_count_is_one(self):
        img, raw = _one_hook_and_a_ledger()
        r = _count(img, raw)
        self.assertEqual(r["hooks"], 1)

    def test_CONTROL_two_real_hooks_are_still_two_with_the_line_set_aside(self):
        img = _paper(500, 600)
        _rect(img, H_X0, H_FAR, H_X1, H_TIP_UP)
        for dy in (3.0, 0.6 * H_SP + 3.0):
            pts = np.array([[H_X1 - 2, H_TIP_UP - dy], [H_X1 + 0.5 * H_SP, H_TIP_UP - dy - 0.5 * H_SP],
                            [H_X1 + 0.85 * H_SP, H_TIP_UP - dy - 1.0 * H_SP]], np.int32)
            cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=int(round(0.25 * H_SP)))
        r_off = _count(img)
        r_on = _count(img, img)
        self.assertEqual(r_on["hooks"], r_off["hooks"])

    def test_CONTROL_a_hook_with_no_ledger_line_is_counted_the_same_with_or_without_the_line_rows(self):
        img, raw = _one_hook_and_a_ledger()
        img2 = img.copy(); raw2 = raw.copy()
        img2[255:271, 250:360] = 255; raw2[255:271, 250:360] = 255
        self.assertEqual(_count(img2)["hooks"], _count(img2, raw2)["hooks"])
        self.assertEqual(_count(img2)["hooks"], 1)

    def test_the_hooks_flag_is_off_by_default_and_a_typo_leaves_it_off(self):
        os.environ.pop(gather.HOOKS_LINE_BRIDGE_ENV, None)
        self.assertFalse(gather.hooks_line_bridge_enabled())
        for typo in ("", "yess", "ON!"):
            with mock.patch.dict(os.environ, {gather.HOOKS_LINE_BRIDGE_ENV: typo}):
                self.assertFalse(gather.hooks_line_bridge_enabled(), typo)


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 3. thin_run_stack: a stem fused with a stack of heads that protrudes just under the shipped cut (q110 / q118)
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _cell(paint, width=900) -> MeasureCell:
    img = _paper(900, width)
    paint(img)
    return MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0, image=img, image_no_staff=img.copy(),
                       bbox_page_px=(0, 0, width, 900), staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0)


def _stack_with_a_short_protrusion(protrude=75, heads=True):
    def paint(img):
        if heads:
            _rect(img, 320, 600, 450, 800)                    # two stacked heads: 200 tall
        _rect(img, 442, 600 - protrude, 450, 800)              # a down... up stem protruding `protrude` px beyond the heads
    return paint


STACK = frozenset({"thin_run", "thin_run_stack"})


class TestAStackWhoseStemProtrudesJustUnderTheCut(unittest.TestCase):

    def test_the_shipped_cut_finds_no_stem_at_75_px(self):
        self.assertEqual(detect_stems(_cell(_stack_with_a_short_protrusion()), stem_finder=frozenset({"thin_run"})), [])

    def test_RED_thin_run_stack_finds_the_stem_at_75_px(self):
        out = detect_stems(_cell(_stack_with_a_short_protrusion()), stem_finder=STACK)
        self.assertEqual(len(out), 1)
        d = out[0]
        self.assertLessEqual(d.width_canonical, 12)
        self.assertGreaterEqual(d.height_canonical, 250)

    def test_CONTROL_a_protrusion_under_the_new_cut_is_still_no_stem(self):
        self.assertEqual(detect_stems(_cell(_stack_with_a_short_protrusion(protrude=40)), stem_finder=STACK), [])

    def test_CONTROL_heads_without_a_stem_are_still_no_stem(self):
        def paint(img):
            _rect(img, 320, 600, 450, 800)
        self.assertEqual(detect_stems(_cell(paint), stem_finder=STACK), [])

    def test_CONTROL_a_stem_the_shipped_cut_already_finds_is_found_identically(self):
        cell = _cell(_stack_with_a_short_protrusion(protrude=400))
        a = detect_stems(cell, stem_finder=frozenset({"thin_run"}))
        b = detect_stems(cell, stem_finder=STACK)
        self.assertEqual([(d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical) for d in a],
                         [(d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical) for d in b])


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 4. pair_flag_curve: the stem condemned by the flag's own curve (Brahms p6, bar 102)
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _stem_and_a_flag_curve(img):
    _rect(img, 300, 200, 308, 600)                 # the real stem, 4 spaces
    _rect(img, 380, 300, 387, 520)                 # the flag's curve: a vertical stroke 79 px to its right, 2.2 spaces


FLAG_BOX = ("flag", (375.0, 250.0, 100.0, 300.0))        # wholly around the curve; the stem stands outside it
BASE = frozenset({"pair_evidence"})
FLAGGED = frozenset({"pair_evidence", "pair_flag_curve"})


class TestAStemPairedWithTheFlagsCurve(unittest.TestCase):

    def test_the_shipped_pair_rule_drops_both_strokes(self):
        self.assertEqual(detect_stems(_cell(_stem_and_a_flag_curve), stem_finder=BASE, marks=[FLAG_BOX]), [])

    def test_RED_pair_flag_curve_keeps_the_stem_and_drops_the_curve(self):
        out = detect_stems(_cell(_stem_and_a_flag_curve), stem_finder=FLAGGED, marks=[FLAG_BOX])
        self.assertEqual([(d.x_canonical, d.width_canonical) for d in out], [(300, 8)])

    def test_CONTROL_with_no_flag_box_over_the_partner_both_are_still_dropped(self):
        self.assertEqual(detect_stems(_cell(_stem_and_a_flag_curve), stem_finder=FLAGGED, marks=[]), [])

    def test_CONTROL_when_both_strokes_lie_in_the_flag_box_the_rule_does_not_fire(self):
        wide = ("flag", (280.0, 150.0, 220.0, 500.0))
        self.assertEqual(detect_stems(_cell(_stem_and_a_flag_curve), stem_finder=FLAGGED, marks=[wide]), [])

    def test_CONTROL_an_accidental_box_over_the_partner_is_the_old_pair_evidence_rule(self):
        acc = ("accidental", (375.0, 250.0, 100.0, 300.0))
        out = detect_stems(_cell(_stem_and_a_flag_curve), stem_finder=FLAGGED, marks=[acc])
        self.assertEqual([(d.x_canonical) for d in out], [300])


if __name__ == "__main__":
    unittest.main()
