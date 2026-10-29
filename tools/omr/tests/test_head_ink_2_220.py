"""ROADMAP 2.220 milestone 1 -- `Q.HEAD_INK`: ONE fill reading per printed head, read on that head's own ink. STAGED GATHER
(`stroke_map.head_mask` / `head_ink_value`, `gather.gather_head_ink`, flag `OMR_FILL_FROM_STROKES`, default OFF).

The cause (benchmarks/ink-map-fill-2026-10/FINDINGS.md): the stroke map cuts a hollow head's ring into lunes and rims, so a stroke's own
`hole_share` is 0 on every half. RED before this change: `stroke_map.head_mask` does not exist, and the map's own blob `hole_share` on the
synthetic half below is 0.0 (the control `test_CONTROL_the_stroke_maps_own_blob_hole_is_zero_on_the_half`).

Synthetic cells at 100 canonical px a space, 0 = ink, a staff of five lines; `erased` = the same drawing with the line rows removed (the
eraser's cut through a ring tangent to a line included)."""
import os
import unittest

import cv2
import numpy as np

from tools.omr.staged import stroke_map as SM

SP = 100
TOP = 200
LINES = [TOP + i * SP for i in range(5)]
LINE_T = 10


def _canvas(w=900, h=900):
    return np.full((h, w), 255, np.uint8)


def _lines(img):
    for y in LINES:
        img[y - LINE_T // 2:y + LINE_T // 2, :] = 0


def _head(img, cx, cy, hollow, angle=-20.0):
    cv2.ellipse(img, (cx, cy), (66, 46), angle, 0, 360, 0, -1)
    if hollow:
        cv2.ellipse(img, (cx, cy), (50, 22), angle, 0, 360, 255, -1)


def _stem_up(img, cx, cy):
    x = cx + 60
    img[cy - 340:cy + 5, x:x + 12] = 0
    return x


def _sharp(img, cx, cy):
    for dx in (-25, 25):
        img[cy - 150:cy + 150, cx + dx - 5:cx + dx + 5] = 0
    for dy in (-45, 45):
        pts = np.array([[cx - 60, cy + dy + 15], [cx + 60, cy + dy - 15], [cx + 60, cy + dy - 40], [cx - 60, cy + dy - 10]], np.int32)
        cv2.fillPoly(img, [pts], 0)


def _cell(draw):
    """(raw, erased, CellStrokes) for a cell drawn by `draw(img)` on top of a staff."""
    notes = _canvas()
    draw(notes)
    raw = notes.copy()
    _lines(raw)
    erased = raw.copy()
    for y in LINES:            # the eraser: every line row whose vertical run is short (the ring top/bottom tangent to a line goes too)
        band = slice(y - LINE_T // 2, y + LINE_T // 2)
        col_ink = (notes[y - 25:y + 25] == 0).sum(axis=0)
        cut = col_ink < 30
        erased[band, cut] = 255
    res = SM.map_strokes(erased, float(SP), LINES, raw)
    return raw, erased, res


def _box(cx, cy, w=1.35, h=1.0):
    return (cx - w * SP / 2.0, cy - h * SP / 2.0, cx + w * SP / 2.0, cy + h * SP / 2.0)


def _read(raw, erased, res, box, foreign=None):
    from tools.omr.staged.gather import head_interior_white
    hm = SM.head_mask(res, erased, raw, box, foreign)
    slit = None
    if hm.get("mask") is not None:
        img = np.where(hm["mask"], 0, 255).astype(np.uint8)
        ox, oy = hm["origin"]
        ex0, ey0, ex1, ey1 = hm["extent"]
        iw = head_interior_white(img, (ex0 - ox, ey0 - oy, ex1 - ex0, ey1 - ey0))
        slit = iw["rows_share"] if iw else None
    return hm, slit, SM.head_ink_value(hm, slit)


class HeadMask(unittest.TestCase):
    def test_CONTROL_the_stroke_maps_own_blob_hole_is_zero_on_the_half(self):
        """The cause, pinned: the map alone has no head -- no blob under the half's box encloses paper."""
        cx, cy = 400, LINES[2] + SP // 2           # in a space: the lines above and below are tangent to the ring
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        under = [i for i, sh in SM.strokes_in_box(res, _box(cx, cy)) if sh >= SM.COVER_SHARE_MIN]
        self.assertTrue(under)
        self.assertEqual(max((res.strokes[i].hole_share or 0.0) for i in under), 0.0)

    def test_a_half_in_a_space_reads_hollow_on_its_own_ink(self):
        cx, cy = 400, LINES[2] + SP // 2
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy))
        self.assertGreater(hm["hole_share"], 0.0)
        self.assertEqual(value, "hollow", (hm, slit))
        self.assertEqual(hm["stem_cut"], "right")
        self.assertIsNone(hm["not_one_head"])

    def test_the_erasers_cut_through_the_ring_is_mended_and_the_control_fails_without_it(self):
        """The ring's top rows lie on a line and the eraser took them (the ring opens on the erased raster). With the unerased raster the
        line pixels inside the head's hull are put back and the ring encloses paper; without it (raw=None, the control) it does not."""
        cx, cy = 400, LINES[2] + SP // 2
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        hole_top = int(np.nonzero((raw[:, cx] == 255) & (np.arange(raw.shape[0]) > LINES[2] + LINE_T))[0][0])   # the hole's first row
        erased = erased.copy()
        erased[LINES[2] - LINE_T // 2:hole_top, cx - 70:cx + 55] = 255     # the eraser's walk took the line AND the rim under it
        self.assertGreater(int(((raw == 0) & (erased == 255))[LINES[2] + LINE_T:hole_top].sum()), 0)   # rim ink was taken
        res = SM.map_strokes(erased, float(SP), LINES, raw)
        hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy))
        self.assertGreater(hm["line_px_restored"], 0)
        self.assertGreater(hm["hole_share"], 0.0, (hm, slit))
        hm0 = SM.head_mask(res, erased, None, _box(cx, cy))
        self.assertEqual(hm0["hole_share"], 0.0)

    def test_a_half_on_a_line_reads_hollow(self):
        cx, cy = 400, LINES[2]
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy))
        self.assertGreater(hm["hole_share"], 0.0)
        self.assertEqual(value, "hollow", (hm, slit))

    def test_a_too_big_box_on_a_half_still_reads_hollow(self):
        """The 2.220 class A: the detector box is 1.9 sp wide (not head-sized for 2.148); the head's own ink is one head and hollow."""
        cx, cy = 400, LINES[1] + SP // 2
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy, w=1.95, h=1.25))
        self.assertEqual(value, "hollow", (hm, slit))
        self.assertLessEqual(hm["extent_sp"][0], SM.HEAD_INK_MAX_WIDTH_SPACES)

    def test_CONTROL_a_filled_head_reads_filled_with_no_hole(self):
        for cy in (LINES[2], LINES[2] + SP // 2):
            cx = 400
            raw, erased, res = _cell(lambda im: (_head(im, cx, cy, False), _stem_up(im, cx, cy)))
            hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy))
            self.assertEqual(hm["hole_share"], 0.0)
            self.assertEqual(value, "filled", (hm, slit))

    def test_fix_A_a_box_holding_a_sharp_is_not_hollow(self):
        """Sean's tile 6: a quarter whose box takes in a good part of a sharp. With the sharp's box: its strokes are dropped and the
        head reads filled; without it the extent is not one head (`not_one_head`). Never hollow."""
        cx, cy = 500, LINES[2] + SP // 2

        def draw(im):
            _head(im, cx, cy, False)
            _stem_up(im, cx, cy)
            _sharp(im, cx - 120, cy)
        raw, erased, res = _cell(draw)
        box = (cx - 175, cy - 57, cx + 70, cy + 57)            # 2.45 x 1.14 sp: head + the sharp's right half
        sharp_box = (cx - 190, cy - 160, cx - 50, cy + 160)
        foreign = {i: "accidentalSharp" for i, sh in SM.strokes_in_box(res, sharp_box) if sh >= SM.COVER_SHARE_MIN}
        for fg in (foreign, None):
            hm, slit, (value, why, margin) = _read(raw, erased, res, box, fg)
            self.assertNotEqual(value, "hollow", (fg is not None, hm.get("extent_sp"), hm.get("hole_share"), slit))
            self.assertIn(value if value else why, ("filled", "not_one_head"))

    def test_fix_A_a_flag_box_is_not_one_head(self):
        """Sean's tile 3: a head-classed box on a flag. With the flag's box the stroke is another mark's (`ink_is_another_marks`)."""
        def draw(im):
            x = 400
            im[200:600, x:x + 12] = 0
            pts = np.array([[x, 200], [x + 12, 200], [x + 110, 330], [x + 90, 420], [x + 70, 330]], np.int32)
            cv2.fillPoly(im, [pts], 0)
        raw, erased, res = _cell(draw)
        box = (395, 190, 395 + 152, 190 + 222)
        foreign = {i: "flag8thUp" for i, sh in SM.strokes_in_box(res, box) if sh >= SM.COVER_SHARE_MIN and res.strokes[i].kind != "vertical"}
        hm, slit, (value, why, margin) = _read(raw, erased, res, box, foreign)
        self.assertIsNone(value)
        self.assertEqual(why, "not_one_head")

    def test_fix_A_a_wide_letter_run_is_not_one_head(self):
        """Sean's tile 2: part of an ff boxed 3.9 sp wide -- the ink extent is not one head's."""
        def draw(im):
            for x0 in (300, 470):
                cv2.ellipse(im, (x0, 470), (70, 20), -30, 0, 360, 0, -1)
                cv2.ellipse(im, (x0 + 60, 430), (40, 14), 0, 0, 360, 0, -1)
        raw, erased, res = _cell(draw)
        hm, slit, (value, why, margin) = _read(raw, erased, res, (220, 420, 220 + 388, 420 + 103))
        self.assertIsNone(value)
        self.assertEqual(why, "not_one_head")

    def test_fix_D_the_extent_and_centre_do_not_move_with_the_window(self):
        """2.115's tile-13 lesson: a centre computed from a window moved 0.36 sp with the window. The mask's extent is the head's own ink,
        so neither the crop margin nor the box size moves it."""
        cx, cy = 400, LINES[2]
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))
        centres = []
        old = SM.HEAD_WINDOW_MARGIN_SPACES
        try:
            for mg in (0.2, 0.3, 0.5, 0.8):
                SM.HEAD_WINDOW_MARGIN_SPACES = mg
                for w, h, dy in ((1.35, 1.0, 0.0), (0.83, 0.81, -0.3), (1.9, 1.2, 0.0)):
                    hm = SM.head_mask(res, erased, raw, _box(cx, int(cy + dy * SP), w, h))
                    centres.append(hm["centre"])
        finally:
            SM.HEAD_WINDOW_MARGIN_SPACES = old
        xs, ys = [c[0] for c in centres], [c[1] for c in centres]
        # 2.115's own stability guard cut (spread 0.1 sp); its window centroid moved 0.36 sp on tile 13
        self.assertLessEqual((max(xs) - min(xs)) / SP, 0.1, centres)
        self.assertLessEqual((max(ys) - min(ys)) / SP, 0.1, centres)

    def test_fix_C_a_stacked_pair_is_clipped_to_the_boxs_own_head(self):
        """Two heads a second apart on one stem: the column is two heads tall; the head-sized box's mask is clipped to its own rows."""
        cx = 400
        cy1, cy2 = LINES[2], LINES[2] + SP // 2

        def draw(im):
            _head(im, cx, cy1, False)
            _head(im, cx, cy2, False)
            _stem_up(im, cx, cy2)
        raw, erased, res = _cell(draw)
        hm, slit, (value, why, margin) = _read(raw, erased, res, _box(cx, cy1))
        self.assertTrue(hm["stack_clipped"])
        self.assertNotEqual(value, "hollow")


class GatherFlag(unittest.TestCase):
    """`gather_head_ink` files nothing with the flag off (the default), one row per head box with it on."""

    def _run(self, flag):
        from tools.omr.staged import gather as G
        from tools.omr.staged.record import Q
        cx, cy = 400, LINES[2] + SP // 2
        raw, erased, res = _cell(lambda im: (_head(im, cx, cy, True), _stem_up(im, cx, cy)))

        class Cell:
            page_index, staff_index, measure_index = 0, 0, 0
            image_no_staff, binary = erased, raw

        class Det:
            smufl_name = "noteheadBlackInSpace"
            x_canonical, y_canonical = cx - 95.0, cy - 60.0
            width_canonical, height_canonical = 190.0, 120.0
        log = G.Log()
        dets = {G.R.cell(0, 0, 0, 0).to_key(): [Det()]}
        old = os.environ.get(G.FILL_FROM_STROKES_ENV)
        os.environ[G.FILL_FROM_STROKES_ENV] = flag
        try:
            G.gather_head_ink(log, [Cell()], {0: (0, 0)}, dets, {(0, 0, 0, 0): res})
        finally:
            if old is None:
                os.environ.pop(G.FILL_FROM_STROKES_ENV, None)
            else:
                os.environ[G.FILL_FROM_STROKES_ENV] = old
        return [r for r in log.all_rows() if r.quantity == Q.HEAD_INK]

    def test_flag_off_files_nothing(self):
        self.assertEqual(self._run("0"), [])

    def test_flag_on_files_one_hollow_row(self):
        rows = self._run("1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value, "hollow")
        d = rows[0].detail
        for k in ("hole_share", "slit_rows_share", "extent_sp", "centre", "line_px_restored", "stem_cut", "n_pieces", "stroke_set"):
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
