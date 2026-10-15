"""ROADMAP 2.132 -- a HOLLOW second head a third apart, kept only where two witnesses from two sources agree.

Sean's 2.129 tile 9 (Brahms 317803, pdf 21, `glyph/21/1/3/7/6`): two hollow half notes a third apart on one stem, a
real second head, refused `stacked_head_duplicate` because 2.129's blob test is for filled heads. 19 such chords
stand refused on Brahms. The reading that would keep them, two white interiors inside inked rings, ALSO passes the
"8" of a printed 9/8 (`glyph/0/0/11/7/1`, no head in Sean's truth; the 2.129 FINDINGS called it a bass clef, a crop
shows the numeral). The feature that tells them apart is the STEM: a chord's stem runs 2.2-4.0 spaces past the pair;
the numeral's "stem" row is the numeral's own height (0.15 past).

Layers: A `gather.fit_hollow_stacked_pair` (pure); B the REAL page rasters (`fixtures/stacked_hollow_2_132.npz`, cropped
from Brahms pdf 21 / 0 / 18 / 12 at 600 dpi, the real boxes and the real `Q.STEM` boxes) through
`gather.gather_stacked_head_fit` behind `OMR_STACKED_HOLLOW_PAIR` (default OFF).

NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Q, READERS, Log
from tools.omr.types import MeasureCell
from tools.omr.tests.test_staged_stacked_head_fit import _stem_row

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "stacked_hollow_2_132.npz")


def _load(name):
    z = np.load(FIX)
    return {k.split("__", 1)[1]: z[k] for k in z.files if k.startswith(name + "__")}


# ─────────────────────────────────────────────────────────────────────────────
# A. the pure pair test
# ─────────────────────────────────────────────────────────────────────────────

HOLLOW = (0.2, 0.7)       # (centre, ring) of a hollow slot
FILLED = (0.99, 0.6)
PAPER = (0.0, 0.05)


class TestFitHollowStackedPair(unittest.TestCase):
    def _reader(self, table):
        return lambda p: table.get(p)

    def test_two_hollow_slots_and_a_long_stem_are_two_heads(self):
        fit = gather.fit_hollow_stacked_pair(self._reader({-1: HOLLOW, 1: HOLLOW}), [-1],
                                             lambda p: 2.8)
        self.assertTrue(fit["accepted"])
        self.assertEqual(fit["positions"], (-1, 1))
        self.assertGreater(fit["margin"], 0)

    def test_the_same_slots_with_no_stem_past_them_are_not_a_pair(self):
        """The 8 of 9/8: both loops read hollow, the 'stem' is the numeral's own height."""
        fit = gather.fit_hollow_stacked_pair(self._reader({-1: HOLLOW, 1: HOLLOW}), [-1],
                                             lambda p: 0.15)
        self.assertFalse(fit["accepted"])
        self.assertIn("stem", fit["near_miss"]["hollow_pair"])
        self.assertEqual(fit["near_miss"]["stem_extension_spaces"], 0.15)

    def test_no_stem_at_all_is_not_a_pair(self):
        fit = gather.fit_hollow_stacked_pair(self._reader({-1: HOLLOW, 1: HOLLOW}), [-1], lambda p: None)
        self.assertFalse(fit["accepted"])

    def test_a_filled_slot_or_paper_is_not_hollow(self):
        for other in (FILLED, PAPER):
            fit = gather.fit_hollow_stacked_pair(self._reader({-1: HOLLOW, 1: other}), [-1], lambda p: 3.0)
            self.assertFalse(fit["accepted"], other)
            self.assertIn("not both hollow", fit["near_miss"]["hollow_pair"])

    def test_two_placements_that_both_read_hollow_are_ambiguous(self):
        table = {-2: HOLLOW, 0: HOLLOW, 2: HOLLOW}
        fit = gather.fit_hollow_stacked_pair(self._reader(table), [-2, 0], lambda p: 3.0)
        self.assertFalse(fit["accepted"])
        self.assertIn("ambiguous", fit["near_miss"]["hollow_pair"])

    def test_the_clearer_placement_wins(self):
        table = {-2: HOLLOW, 0: (0.1, 0.85), 2: (0.1, 0.85)}
        fit = gather.fit_hollow_stacked_pair(self._reader(table), [-2, 0], lambda p: 3.0)
        self.assertTrue(fit["accepted"])
        self.assertEqual(fit["positions"], (0, 2))

    def test_an_unreadable_slot_is_declined(self):
        fit = gather.fit_hollow_stacked_pair(self._reader({-1: HOLLOW}), [-1], lambda p: 3.0)
        self.assertFalse(fit["accepted"])


class TestDefaultOff(unittest.TestCase):
    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_STACKED_HOLLOW_PAIR", None)
            self.assertFalse(gather.stacked_hollow_pair_enabled())
        for on in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {"OMR_STACKED_HOLLOW_PAIR": on}):
                self.assertTrue(gather.stacked_hollow_pair_enabled())


# ─────────────────────────────────────────────────────────────────────────────
# B. the real page rasters, through the reader
# ─────────────────────────────────────────────────────────────────────────────

def _whiten_lines(img, top_y, sp):
    """The cell's `image_no_staff`: the five line rows whitened (a head on a line loses its middle too)."""
    out = img.copy()
    for j in range(5):
        y = int(round(top_y + j * sp))
        out[max(0, y - 1):y + 2, :] = 255
    return out


def _run(name, flag, *, dets_override=None, top_shift_half=0.0):
    f = _load(name)
    raster = (f["raster"] > 0).astype(np.uint8) * 255 if f["raster"].dtype != np.uint8 else f["raster"]
    sp = float(f["sp"])
    top_y = float(f["top_y"]) + top_shift_half * float(f["half"])
    lines = [top_y + j * sp for j in range(5)]
    H, W = raster.shape
    cell = MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0,
                       image=raster, image_no_staff=_whiten_lines(raster, top_y, sp),
                       bbox_page_px=(0, 0, W, H), staff_line_ys_canonical=lines,
                       upscale_factor=1.0)
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=raster))
    sub = R.cell(0, 0, 0, 0)
    log = Log()
    for sx, sy, sw, sh in _stems_of(f):
        log.observe(sub, Q.STEM, (sx, sy, sw, sh), reader=READERS.CV_LINES, frame="cell:0")
    dets = []
    boxes = dets_override if dets_override is not None else f["dets"]
    for (cx, cy, w, h), cls in zip(boxes, f["cls"]):
        dets.append(types.SimpleNamespace(
            smufl_name=str(cls), x_canonical=cx - w / 2, y_canonical=cy - h / 2,
            width_canonical=w, height_canonical=h, x_center=cx, y_center=cy))
    with mock.patch.dict(os.environ, {"OMR_STACKED_HOLLOW_PAIR": flag}):
        gather.gather_stacked_head_fit(log, [cell], {0: (0, 0)}, {sub.to_key(): dets}, pws=pws)
    rows = [log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, gi)) for gi in range(len(dets))]
    return [r[0] for r in rows if r]


def _stems_of(f):
    rows = f["stems"] if "stems" in f else [f["stem"]]
    return [tuple(float(v) for v in r) for r in rows]


def _witness(name, dets_override=None, top_shift_half=0.0):
    """`gather._hollow_pair_from_page` alone, on the real page raster and stem, candidates from the boxes."""
    f = _load(name)
    raster = f["raster"]
    sp, half = float(f["sp"]), float(f["half"])
    top_y = float(f["top_y"]) + top_shift_half * half
    H, W = raster.shape
    cell = types.SimpleNamespace(bbox_page_px=(0, 0, W, H), upscale_factor=1.0)
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=raster))
    boxes = dets_override if dets_override is not None else f["dets"]
    observed = [(cy - top_y) / half for (_, cy, _, _) in boxes]
    cx = float(np.mean([b[0] for b in boxes]))
    cands = [p for p in range(int(min(observed)) - 2, int(max(observed)) + 3)
             if gather._stacked_slots_have_boxes((p, p + 2), observed)]
    return gather._hollow_pair_from_page(pws, cell, cx, top_y, half, sp,
                                         _stems_of(f), cands)


class TestRealPages(unittest.TestCase):
    def test_tile9_off_is_k1_and_says_it_was_not_tested(self):
        rows = _run("tile9_hollow_pair", "0")
        self.assertEqual([r.value[0] for r in rows], [1, 1])
        self.assertIn("not_tested", rows[0].detail["near_miss"])

    def test_tile9_on_is_two_heads_each_box_its_own_slot(self):
        """Sean's tile 9: a real hollow second head."""
        rows = _run("tile9_hollow_pair", "1")
        self.assertEqual([r.value[0] for r in rows], [2, 2])
        self.assertEqual({r.value[1] for r in rows}, {0, 1})
        self.assertEqual(rows[0].detail["second_head_by"], "hollow_pair")
        self.assertGreater(rows[0].detail["near_miss"]["stem_extension_spaces"], 1.5)

    def test_the_8_of_a_printed_9_over_8_is_not_two_heads(self):
        """Brahms pdf 0 `glyph/0/0/11/7/1`: two white loops 1.0 space apart, ring 0.71/0.62 -- and no head in
        Sean's truth. The print's loops sit on the staff's own slots; the record's boxes stand 0.44 half-step
        high of them, so the grid is shifted to the boxes (slots 5 and 7) to give the ink witness its best case:
        both loops read hollow. Only the stem tells it from tile 9."""
        fit = _witness("numeral_8_of_9over8", top_shift_half=0.44)
        self.assertFalse(fit["accepted"])
        nm = fit["near_miss"]
        self.assertEqual(nm["hollow_pair"], "stem does not run past the pair")
        self.assertLess(nm["stem_extension_spaces"], 0.5)
        rows = _run("numeral_8_of_9over8", "1", top_shift_half=0.44)
        self.assertEqual([r.value[0] for r in rows], [1, 1])
        self.assertNotIn("second_head_by", rows[0].detail)

    def test_a_bass_clef_is_not_two_heads_by_the_hollow_test(self):
        """Brahms pdf 18 `glyph/18/1/3/7/20` + `/26`: a bass clef boxed as a whole note and a black head. The page
        fixture's staff-line-whitened raster makes the OLD mean test read k=2 here (the real, erased cell reads
        k=1), so the control is the witness itself, on the real page raster and the real stem."""
        rows = _run("bass_clef", "1")
        self.assertNotEqual(rows[0].detail.get("second_head_by"), "hollow_pair")
        fit = _witness("bass_clef")
        self.assertFalse(fit["accepted"])

    def test_litolff_a_neighbours_stem_overlapping_first_does_not_hide_the_pair(self):
        """Litolff (Beethoven 5) pdf 3 `glyph/3/0/1/5/7` + `/10`: two half notes a third apart. Two `Q.STEM` rows
        overlap the wide boxes; the FIRST is the next note's stem (2.3 spaces), the pair's own is the longer one
        (5.2 spaces). Read off the first, the extension was 0.14 and a real pair was refused."""
        fit = _witness("litolff_pair_two_stems")
        self.assertTrue(fit["accepted"], fit["near_miss"])
        self.assertGreater(fit["near_miss"]["stem_extension_spaces"], 1.5)

    def test_litolff_second_pair_end_to_end(self):
        rows = _run("litolff_pair_kept", "1")
        self.assertEqual([r.value[0] for r in rows], [2, 2])
        self.assertEqual(rows[0].detail["second_head_by"], "hollow_pair")

    def test_a_single_hollow_head_cut_by_a_line_stays_one(self):
        """Brahms pdf 0 q711/q712: one half note on a line, its two white holes boxed separately 0.4 space
        apart. The boxes are not at two heads' distance: no slot pair is even tried."""
        fit = _witness("line_cut_single_head")
        self.assertFalse(fit["accepted"])
        self.assertEqual(fit["near_miss"]["candidates"], 0)
        for r in _run("line_cut_single_head", "1"):
            self.assertNotEqual(r.detail.get("second_head_by"), "hollow_pair")

    def test_a_ghost_box_a_third_from_a_single_hollow_head_stays_one(self):
        """The boxes of the line-cut head pulled to a third apart, centred on it (the geometry gate now passes):
        the slot windows overlap the one head's own ring, not two heads' -- the ink witness refuses."""
        f = _load("line_cut_single_head")
        (cx0, cy0, w0, h0), (cx1, cy1, w1, h1) = f["dets"]
        mid, sp = (cy0 + cy1) / 2.0, float(f["sp"])
        boxes = [(cx0, mid - sp / 2.0, w0, h0), (cx1, mid + sp / 2.0, w1, h1)]
        fit = _witness("line_cut_single_head", dets_override=boxes)
        self.assertFalse(fit["accepted"])
        self.assertGreater(fit["near_miss"]["candidates"], 0)
        self.assertIn("not both hollow", fit["near_miss"]["hollow_pair"])


if __name__ == "__main__":
    unittest.main()
