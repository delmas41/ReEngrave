"""ROADMAP 2.115 -- a notehead box drawn on only PART of the head is re-centred
before its inside is read. PATH: STAGED GATHER (`gather.recentre_part_boxed`,
`gather.gather_notehead_ink`; flag `OMR_RECENTRE_PART_BOXED`, default OFF).

The case (Sean's 2.114 tile 13, Litolff glyph/1/0/9/11/1): a half note with the
top staff line through its middle, its white two slits above and below the line;
BOTH detectors boxed only the upper rim (0.83 x 0.81 of a standard head, 0.3 sp
above the head's centre), so the 2.88 centre window read solid rim = 1.00 =
black. Sean (2026-10-13): *"many hollow noteheads have lines through the middle
of them. It needs to be a certain amount of white on the inside."*

Each refusal/no-op test has a positive control in the same class (a test that
cannot fail passes by refusing everything). ⚠️ RUN RED FIRST: on the tree
before this change `gather.recentre_part_boxed` does not exist (AttributeError)
and the wired tests read the part-box as black (1.00).
NO TEST HERE ASSERTS ON MODULE SOURCE TEXT.
"""
from __future__ import annotations

import math
import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q
from tools.omr.types import MeasureCell

S = 40.0
HEAD_W, HEAD_H = 1.4 * S, 1.1 * S
LINES = (100.0, 140.0, 180.0, 220.0, 260.0)
FLAG = "OMR_RECENTRE_PART_BOXED"


def _paper(h=300, w=300):
    return np.full((h, w), 255, np.uint8)


def _head(img, cx, cy, *, hollow=True, tilt_deg=30.0):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = HEAD_W / 2.0, HEAD_H / 2.0
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0
    if hollow:
        t = math.radians(tilt_deg)
        dx, dy = xx - cx, -(yy - cy)
        u = dx * math.cos(t) + dy * math.sin(t)
        v = -dx * math.sin(t) + dy * math.cos(t)
        img[(u / (0.34 * S)) ** 2 + (v / (0.12 * S)) ** 2 <= 1.0] = 255


def _line(img, y, cx, half=1.6 * S, thick=4):
    img[int(y - thick // 2):int(y + (thick + 1) // 2),
        int(cx - half):int(cx + half)] = 0


def _stem(img, x, y0, y1, w=3):
    img[int(y0):int(y1), int(x):int(x + w)] = 0


def _box(cx, cy, w_ratio, h_ratio, dy_sp=0.0):
    """A detector box centred (cx, cy + dy_sp staff spaces), at the given
    fractions of the standard head."""
    w, h = w_ratio * HEAD_W, h_ratio * HEAD_H
    cy = cy + dy_sp * S
    return (cx - w / 2.0, cy - h / 2.0, w, h)


def _tile13():
    """Tile 13's geometry: hollow head ON the middle line, detector box = the
    upper rim, 0.83 x 0.81 of a head, centre 0.3 sp above the head's."""
    img = _paper()
    _head(img, 150.0, 180.0)
    _line(img, 180.0, 150.0)
    return img, _box(150.0, 180.0, 0.83, 0.81, dy_sp=-0.3)


def _detection(box):
    x, y, w, h = box
    return types.SimpleNamespace(
        smufl_name="noteheadBlackOnLine", x_canonical=x, y_canonical=y,
        width_canonical=w, height_canonical=h,
        x_center=x + w / 2.0, y_center=y + h / 2.0)


def _gather_ink(img, box, *, net=None, flag=True):
    cell = MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img if net is None else net,
        bbox_page_px=(0, 0, 300, 300),
        staff_line_ys_canonical=list(LINES), upscale_factor=1.0)
    cell.__dict__["binary"] = img
    sub = R.cell(0, 0, 0, 0)
    det = {sub.to_key(): [_detection(box)]}
    log = Log()
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
    env = {FLAG: "1"} if flag else {}
    with mock.patch.dict(os.environ, env, clear=False):
        if not flag:
            os.environ.pop(FLAG, None)
        gather.gather_notehead_recentre(log, [cell], {0: (0, 0)}, det)
        gather.gather_notehead_ink(log, [cell], {0: (0, 0)}, det, pws=pws)
    return log.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1], log


def _centre(row, key):
    return row.detail[key]["windows"]["center"]


class TestPureCentreOfAPartBox(unittest.TestCase):

    def test_tile13_the_upper_rim_box_is_moved_down_onto_its_head(self):
        img, box = _tile13()
        r = gather.recentre_part_boxed(img, box, S)
        self.assertTrue(r["accepted"], r)
        self.assertAlmostEqual(r["dy_sp"], 0.3, delta=0.12)
        self.assertGreater(r["line_rows"], 0)          # the line rows were seen

    def test_the_same_part_box_off_the_other_rim_moves_up(self):
        img = _paper()
        _head(img, 150.0, 180.0)
        _line(img, 180.0, 150.0)
        r = gather.recentre_part_boxed(img, _box(150.0, 180.0, 0.83, 0.81, 0.3), S)
        self.assertTrue(r["accepted"], r)
        self.assertAlmostEqual(r["dy_sp"], -0.3, delta=0.12)

    def test_CONTROL_a_correctly_sized_box_is_untouched(self):
        img, _ = _tile13()
        r = gather.recentre_part_boxed(img, _box(150.0, 180.0, 1.0, 1.0, -0.3), S)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "box_head_sized")
        self.assertEqual(r["dy_sp"], 0.0)

    def test_CONTROL_an_undersized_box_already_on_its_head_is_a_no_op(self):
        """Undersized (0.83 x 0.81) but CENTRED: the ink centre is where the
        box is, so nothing moves and the refusal says how close it came."""
        img = _paper()
        _head(img, 150.0, 160.0, hollow=False)
        r = gather.recentre_part_boxed(img, _box(150.0, 160.0, 0.83, 0.81, 0.0), S)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "centred_enough")
        self.assertLess(r["shift_margin"], 0.0)         # signed: short of the cut
        self.assertEqual(r["dy_sp"], 0.0)

    def test_CONTROL_a_box_on_blank_paper_is_declined_not_guessed(self):
        r = gather.recentre_part_boxed(_paper(), _box(150.0, 180.0, 0.6, 0.6), S)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "no_ink")

    def test_CONTROL_a_stem_alone_does_not_pull_the_centre(self):
        """A box beside a long stem and no head: the stem's columns are left
        out, so there is no ink to centre on."""
        img = _paper()
        _stem(img, 150.0, 60.0, 260.0)
        r = gather.recentre_part_boxed(img, _box(150.0, 150.0, 0.5, 0.5), S)
        self.assertFalse(r["accepted"], r)

    def test_CONTROL_a_stem_on_the_head_does_not_drag_the_centre(self):
        img, box = _tile13()
        _stem(img, 150.0 + 0.62 * S, 180.0 - 3.4 * S, 180.0)     # stem up, right
        r = gather.recentre_part_boxed(img, box, S)
        self.assertTrue(r["accepted"], r)
        self.assertAlmostEqual(r["dy_sp"], 0.3, delta=0.15)

    def test_CONTROL_a_part_box_that_already_reads_hollow_keeps_its_reading(self):
        """The box is short and off its head, but its window already lands in
        the white (a hollow head with no line, box centred a little low): no
        move, so a hollow found stays found."""
        img = _paper()
        _head(img, 150.0, 160.0)
        r = gather.recentre_part_boxed(img, _box(150.0, 160.0, 0.83, 0.81, 0.0), S)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "already_reads_hollow")
        self.assertLess(r["drawn_margin"], 0.0)

    def test_the_restated_cut_is_the_adjudicators(self):
        from tools.omr.staged.adjudicators import rhythm
        self.assertEqual(gather.RECENTRE_PART_ONLY_ABOVE_CENTRE,
                         rhythm.HEAD_FILL_HOLLOW_CENTER_MAX)
        self.assertEqual(gather.RECENTRE_PART_HOLLOW_FLOOR,
                         rhythm.HEAD_RAW_CENTER_FLOOR)

    def test_CONTROL_an_estimate_that_depends_on_the_window_is_refused_unstable(self):
        """Litolff tile 13 IN ITS REAL canonical cell (a 400 x 700 px crop of
        `cell/0/9/11`'s binary raster; 100 px per staff space): the stem and the
        next staff line merge into the head, so the centroid's centre depends on
        the window (0.00 / 0.15 / 0.57 sp, Sean's truth box 0.27). The box is left
        as drawn, the spread filed -- a refusal says how close it came."""
        import pathlib
        z = np.load(pathlib.Path(__file__).with_name("data_part_boxed_tile13_cell.npz"))
        shape = tuple(int(v) for v in z["shape"])
        ink = np.unpackbits(z["ink"])[:shape[0] * shape[1]].reshape(shape).astype(bool)
        raw = np.where(ink, 0, 255).astype(np.uint8)
        with mock.patch.object(gather, "RECENTRE_PART_WINDOWS",
                               (0.6, 0.65, 0.7, 0.75)), \
                mock.patch.object(gather, "RECENTRE_PART_HALF_WINDOW_SPACES", 0.7):
            r = gather.recentre_part_boxed(
                raw, tuple(float(v) for v in z["box"]), 100.0)
        self.assertEqual(r["reason"], "unstable", r)
        self.assertFalse(r["accepted"])
        self.assertLess(r["spread_margin"], 0.0)

    def test_off_the_raster_or_no_spacing_is_none(self):
        self.assertIsNone(gather.recentre_part_boxed(None, (0, 0, 9, 9), S))
        self.assertIsNone(gather.recentre_part_boxed(_paper(), (0, 0, 9, 9), 0.0))


class TestWiredIntoTheInteriorReading(unittest.TestCase):

    def test_tile13_flag_off_reads_black_as_before(self):
        img, box = _tile13()
        row, _ = _gather_ink(img, box, flag=False)
        self.assertGreaterEqual(_centre(row, "ink_raw"), 0.9)
        self.assertNotIn("part_boxed", row.detail)
        self.assertNotIn("box_source", row.detail)

    def test_tile13_flag_on_reads_hollow_inside_the_hollow_band(self):
        """THE POINT: re-centred, the interior (line rows left out) is the
        head's white, inside Sean's confirmed hollow band (0.21-0.86)."""
        img, box = _tile13()
        row, _ = _gather_ink(img, box)
        self.assertEqual(row.detail["box_source"], "part_boxed_recentre")
        self.assertTrue(row.detail["part_boxed"]["accepted"])
        off = _centre(row, "ink_off_line")
        self.assertLessEqual(off, 0.75)
        self.assertGreaterEqual(off, 0.2)

    def test_a_FILLED_head_with_a_line_through_it_stays_black(self):
        """The control that must fail the other way: the same part-box on a
        black head with a staff line through it. Moved or not, every reading
        stays at the black heads' value."""
        img = _paper()
        _head(img, 150.0, 180.0, hollow=False)
        _line(img, 180.0, 150.0)
        row, _ = _gather_ink(img, _box(150.0, 180.0, 0.83, 0.81, -0.3))
        for key in ("ink_raw", "ink_net", "ink_off_line"):
            self.assertGreaterEqual(_centre(row, key), 0.85, key)

    def test_a_filled_head_in_a_space_stays_black_and_unmoved_when_centred(self):
        img = _paper()
        _head(img, 150.0, 160.0, hollow=False)
        row, _ = _gather_ink(img, _box(150.0, 160.0, 0.83, 0.81, 0.0))
        self.assertGreaterEqual(_centre(row, "ink_raw"), 0.9)
        self.assertNotEqual(row.detail.get("box_source"), "part_boxed_recentre")

    def test_a_head_sized_box_is_never_touched_even_with_the_flag_on(self):
        img, _ = _tile13()
        full = _box(150.0, 180.0, 1.0, 1.0, -0.3)
        on, _ = _gather_ink(img, full, flag=True)
        off, _ = _gather_ink(img, full, flag=False)
        self.assertEqual(on.value, off.value)
        self.assertEqual(on.detail["ink_raw"], off.detail["ink_raw"])
        self.assertNotIn("part_boxed", on.detail)

    def test_no_notehead_recentre_row_is_filed_so_other_readers_see_the_same_box(self):
        img, box = _tile13()
        _, log = _gather_ink(img, box)
        self.assertEqual(len(log.rows(Q.NOTEHEAD_RECENTRE, R.glyph(0, 0, 0, 0, 0))), 0)

    def test_a_declined_move_files_why_and_how_close(self):
        img = _paper()
        _head(img, 150.0, 160.0, hollow=False)
        row, _ = _gather_ink(img, _box(150.0, 160.0, 0.83, 0.81, 0.0))
        pb = row.detail["part_boxed"]
        self.assertFalse(pb["accepted"])
        self.assertEqual(pb["reason"], "centred_enough")
        self.assertIn("shift_margin", pb)


# ───────────────────────── ROUND 2: the PAGE raster ─────────────────────────
import pathlib

_HERE = pathlib.Path(__file__).parent


def _tile13_real():
    """Sean's tile 13 as the gather sees it: a PAGE binary (600 dpi, the real
    crop pasted at its page position) and a CELL whose canonical raster is the
    real merged one (head + stem + next staff line: the cell-frame rule says
    `unstable` on it, see the test above)."""
    z = np.load(_HERE / "data_part_boxed_tile13_cell.npz")
    cell_ink = np.unpackbits(z["ink"])[:int(z["shape"][0]) * int(z["shape"][1])] \
        .reshape(tuple(int(v) for v in z["shape"])).astype(bool)
    cell_raw = np.where(cell_ink, 0, 255).astype(np.uint8)
    pshape = tuple(int(v) for v in z["page_shape"])
    crop = np.unpackbits(z["page_ink"])[:pshape[0] * pshape[1]].reshape(pshape)
    ox, oy = (int(v) for v in z["page_origin"])
    page = np.full((oy + pshape[0], ox + pshape[1]), 255, np.uint8)
    page[oy:, ox:][crop.astype(bool)] = 0
    up = float(z["cell_up"])
    bx, by, bw, bh = (float(v) for v in z["box"])
    px0, py0 = (float(v) for v in z["page_box"][:2])
    # the crop starts 219 canonical rows below the cell's top (fixture origin)
    lines = [v - 219 for v in (590, 686, 787, 889, 990)]
    cell = MeasureCell(
        page_index=1, system_index=0, staff_index=9, measure_index=11,
        image=cell_raw, image_no_staff=cell_raw,
        bbox_page_px=(px0 - bx / up, py0 - by / up, px0 + 1, py0 + 1),
        staff_line_ys_canonical=lines, upscale_factor=up)
    cell.__dict__["binary"] = cell_raw
    return cell, page, (bx, by, bw, bh)


def _run_real(cell, page, box, *, flag, with_page=True):
    sub = R.cell(1, 0, 9, 11)
    det = {sub.to_key(): [_detection(box)]}
    log = Log()
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=page)) \
        if with_page else None
    env = {FLAG: "1"} if flag else {}
    with mock.patch.dict(os.environ, env, clear=False):
        if not flag:
            os.environ.pop(FLAG, None)
        gather.gather_notehead_recentre(log, [cell], {9: (0, 9)}, det)
        gather.gather_notehead_ink(log, [cell], {9: (0, 9)}, det, pws=pws)
    return log.rows(Q.NOTEHEAD_INK, R.glyph(1, 0, 9, 11, 0))[-1]


class TestPageFrameRound2(unittest.TestCase):

    def test_tile13_real_cell_flag_off_reads_black(self):
        cell, page, box = _tile13_real()
        row = _run_real(cell, page, box, flag=False)
        self.assertGreaterEqual(_centre(row, "ink_raw"), 0.9)
        self.assertNotIn("part_boxed", row.detail)

    def test_tile13_real_cell_the_cell_raster_alone_would_have_refused(self):
        """The control that can fail: round 1's windows on the cell's merged
        raster are `unstable` (the cell frame refused it, 0 heads moved); the
        page-frame gather must succeed where it refused. And the cell raster
        is not to be trusted even with the new windows (it lands 0.41 sp, 0.1
        past the page's and the eye's): the gather does not use it."""
        cell, page, box = _tile13_real()
        with mock.patch.object(gather, "RECENTRE_PART_WINDOWS",
                               (0.6, 0.65, 0.7, 0.75)), \
                mock.patch.object(gather, "RECENTRE_PART_HALF_WINDOW_SPACES", 0.7):
            r = gather.recentre_part_boxed(cell.binary, box, 100.0)
        self.assertEqual(r["reason"], "unstable")
        row = _run_real(cell, page, box, flag=True)
        pb = row.detail["part_boxed"]
        self.assertTrue(pb["accepted"], pb)
        self.assertEqual(pb["frame"], "page")

    def test_tile13_real_cell_flag_on_reads_hollow_off_the_line(self):
        cell, page, box = _tile13_real()
        row = _run_real(cell, page, box, flag=True)
        self.assertEqual(row.detail["box_source"], "part_boxed_recentre")
        # by eye the head is 0.27-0.30 sp below the box centre
        # (the stable window sets read it 0.36; 0.06 sp low is inside the
        # standard box's own tolerance and the reading is the same hollow)
        self.assertGreater(row.detail["part_boxed"]["dy_sp"], 0.2)
        self.assertLess(row.detail["part_boxed"]["dy_sp"], 0.42)
        off = _centre(row, "ink_off_line")
        self.assertGreaterEqual(off, 0.2)
        self.assertLessEqual(off, 0.75, off)
        self.assertLessEqual(_centre(row, "ink_raw"), 0.9)

    def test_the_guard_still_bites_on_the_page_with_round_ones_windows(self):
        """Round 1's windows (0.6-0.75) on the REAL page crop: shifts 0.01 ..
        0.38, spread 0.37 sp -> `unstable`. The guard is unchanged; what moved
        is the window set that contains a whole head."""
        cell, page, box = _tile13_real()
        with mock.patch.object(gather, "RECENTRE_PART_WINDOWS",
                               (0.6, 0.65, 0.7, 0.75)), \
                mock.patch.object(gather, "RECENTRE_PART_HALF_WINDOW_SPACES", 0.7):
            row = _run_real(cell, page, box, flag=True)
        pb = row.detail["part_boxed"]
        self.assertEqual(pb["reason"], "unstable")
        self.assertGreater(pb["window_spread_sp"], 0.3)

    def test_no_page_raster_is_declined_not_read_from_the_cell(self):
        cell, page, box = _tile13_real()
        row = _run_real(cell, page, box, flag=True, with_page=False)
        pb = row.detail["part_boxed"]
        self.assertFalse(pb["accepted"])
        self.assertEqual(pb["reason"], "no_page_raster")
        self.assertNotIn("box_source", row.detail)
        self.assertGreaterEqual(_centre(row, "ink_raw"), 0.9)

    def _black_tile(self, name):
        z = np.load(_HERE / "data_part_boxed_black_tiles.npz")
        shape = tuple(int(v) for v in z[name + "_shape"])
        crop = np.unpackbits(z[name + "_ink"])[:shape[0] * shape[1]] \
            .reshape(shape).astype(bool)
        ox, oy = (int(v) for v in z[name + "_origin"])
        page = np.full((oy + shape[0], ox + shape[1]), 255, np.uint8)
        page[oy:, ox:][crop] = 0
        box = tuple(float(v) for v in z[name + "_box"])
        sp = float(z[name + "_space"])
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=page, image_no_staff=page,
            bbox_page_px=(0.0, 0.0, 1.0, 1.0),
            staff_line_ys_canonical=[0.0, sp, 2 * sp, 3 * sp, 4 * sp],
            upscale_factor=1.0)
        cell.__dict__["binary"] = page
        det = types.SimpleNamespace(
            smufl_name="noteheadBlackOnLine", x_canonical=box[0],
            y_canonical=box[1], width_canonical=box[2] - box[0],
            height_canonical=box[3] - box[1],
            x_center=(box[0] + box[2]) / 2, y_center=(box[1] + box[3]) / 2)
        return cell, page, det, sp

    def _black_tile_row(self, name, flag):
        cell, page, det, sp = self._black_tile(name)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=page))
        with mock.patch.dict(os.environ, {FLAG: "1"} if flag else {}, clear=False):
            if not flag:
                os.environ.pop(FLAG, None)
            gather.gather_notehead_ink(
                log, [cell], {0: (0, 0)}, {sub.to_key(): [det]}, pws=pws)
        return log.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1]

    def test_seans_black_tiles_stay_black_and_unmoved_on_the_page(self):
        """Tiles 7 and 11 (Brahms), 16 (Litolff): his BLACK heads, real page
        crops. Flag ON leaves every reading exactly as OFF (head-sized boxes:
        `box_head_sized`, never moved); tiles 7 and 11 read 1.00, tile 16 (a
        black head with a staff line through it) reads 0.78 raw / 0.875 off the
        line on the page, which is its reading with the flag OFF too."""
        for name in ("t7_bra", "t11_bra", "t16_lit"):
            on = self._black_tile_row(name, True)
            off = self._black_tile_row(name, False)
            self.assertEqual(on.value, off.value, name)
            self.assertEqual(on.detail["ink_raw"], off.detail["ink_raw"], name)
            self.assertEqual(on.detail["ink_off_line"],
                             off.detail["ink_off_line"], name)
            self.assertNotIn("box_source", on.detail, name)
        for name in ("t7_bra", "t11_bra"):
            self.assertGreaterEqual(
                _centre(self._black_tile_row(name, True), "ink_raw"), 0.85, name)
        # tile 16 is the weakest black: its unmoved page reading is the floor
        r16 = self._black_tile_row("t16_lit", True)
        self.assertGreater(_centre(r16, "ink_off_line"), 0.85)

    def test_centred_head_sized_box_is_a_noop_on_the_page(self):
        img = _paper(); _head(img, 150.0, 160.0, hollow=False)
        full = _box(150.0, 160.0, 1.0, 1.0)
        on, _ = _gather_ink(img, full, flag=True)
        off, _ = _gather_ink(img, full, flag=False)
        self.assertEqual(on.value, off.value)
        self.assertEqual(on.detail["ink_raw"], off.detail["ink_raw"])
        self.assertNotEqual(on.detail.get("box_source"), "part_boxed_recentre")


if __name__ == "__main__":
    unittest.main()
