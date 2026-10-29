"""ROADMAP 2.220 milestone 1 -- `Q.HEAD_INK`: is the notehead box ONE head, and that head's fill. STAGED GATHER (`head_ink.trim_head` /
`read_head_ink`, `gather.gather_head_ink`, flag `OMR_FILL_FROM_STROKES`, default ON).

The cause (benchmarks/ink-map-fill-2026-10/FINDINGS.md): fill was read in the DETECTOR's box. On Sean's 8 class-A tiles the box was too
big for 2.148, so the detector's black was written (5 halves wrong), and the slit on those boxes reads "hollow" on the ff, the flag and
the sharp-quarter too (0.50 / 0.52 / 0.70): a box must be shown to be ONE head before its fill is asked.

Real fixtures: `data_head_ink_2220_tiles.npz` -- page crops (600 dpi, `render_page(...).binary`, nothing erased) of Sean's 8 tiles
(out/print/2.220-plan/answers.json) with the detector box, the same cell's accidental / key / flag / dynamic boxes and the page space;
`data_part_boxed_tile13_cell.npz` -- 2.115's tile 13 page crop (a half boxed on its upper rim only)."""
import os
import pathlib
import unittest

import numpy as np

from tools.omr.staged import head_ink as HI
from tools.omr.staged.gather import head_interior_white, notehead_ink_under

HERE = pathlib.Path(__file__).parent
TILES = np.load(HERE / "data_head_ink_2220_tiles.npz")
T13 = np.load(HERE / "data_part_boxed_tile13_cell.npz")


def _tile(n):
    shape = tuple(int(v) for v in TILES[f"t{n}_shape"])
    ink = np.unpackbits(TILES[f"t{n}_ink"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    page = np.where(ink, 0, 255).astype(np.uint8)
    return page, [float(v) for v in TILES[f"t{n}_box"]], [list(map(float, f)) for f in TILES[f"t{n}_foreign"]], float(TILES[f"t{n}_sp"])


def _read(n, **kw):
    page, box, foreign, sp = _tile(n)
    return HI.read_head_ink(page, kw.get("box", box), sp, foreign, head_interior_white, notehead_ink_under)


def _t13():
    shape = tuple(int(v) for v in T13["page_shape"])
    ink = np.unpackbits(T13["page_ink"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    page = np.where(ink, 0, 255).astype(np.uint8)
    ox, oy = (float(v) for v in T13["page_origin"])
    b = [float(v) for v in T13["page_box"]]
    return page, [b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], float(T13["page_space"])


class SeansTiles(unittest.TestCase):
    # Head trim fix 2 (2026-10-29): with the landed line-only trim alone tile 5 reads not_one_head=too_tall (1.59 sp against the 1.5 cap);
    # OMR_HEAD_TRIM_LINE_ONLY_V2 (default ON) lifts the cap to 1.6 and the five halves read hollow again. Pinned to that arm.
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in (HI.TRIM_ENV, HI.TRIM_V2_ENV)}
        os.environ[HI.TRIM_ENV] = "1"
        os.environ[HI.TRIM_V2_ENV] = "1"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_the_five_halves_read_hollow(self):
        for n in (1, 4, 5, 7, 8):
            r = _read(n)
            self.assertEqual(str(TILES[f"t{n}_answer"]), "half")
            self.assertEqual(r["value"], "hollow", (n, r["why"], r["not_one_head"], r["extent_sp"], r["slit"]))

    def test_CONTROL_tile_5_is_too_tall_without_the_v2_cap(self):
        os.environ[HI.TRIM_V2_ENV] = "0"
        r = _read(5)
        self.assertEqual(r["not_one_head"], "too_tall", r)

    def test_the_ff_and_the_flag_are_not_one_head(self):
        for n in (2, 3):
            r = _read(n)
            self.assertIsNone(r["value"], n)
            self.assertEqual(r["why"], "not_one_head", (n, r))

    def test_the_quarter_whose_box_holds_a_sharp_is_never_hollow(self):
        r = _read(6)
        self.assertIn(r["value"] or r["why"], ("filled", "not_one_head"), r)

    def test_CONTROL_the_detector_box_alone_reads_hollow_on_the_non_heads(self):
        """The control that can fail: 2.148's slit on the DETECTOR box (no trim, no head-hood) reads hollow on the ff, the flag and the
        sharp-quarter -- the mechanism, not the cut, is what keeps them from being written as halves."""
        for n in (2, 3, 6):
            page, box, _f, _sp = _tile(n)
            iw = head_interior_white(page, (box[0], box[1], box[2] - box[0], box[3] - box[1]))
            self.assertGreaterEqual(iw["rows_share"], 0.18, n)

    def test_CONTROL_without_the_foreign_boxes_the_flag_still_does_not_read_hollow_by_size_alone(self):
        page, box, _f, sp = _tile(3)
        r = HI.read_head_ink(page, box, sp, [], head_interior_white, notehead_ink_under)
        self.assertIn(r["why"], ("not_one_head",), r)


class FixD(unittest.TestCase):
    def test_tile13_trimmed_head_is_stable_across_windows_and_boxes(self):
        """2.115's tile 13: the window centroid moved 0.36 sp with the window. The trimmed head is an EXTENT of the head's own columns
        and rows, so neither the slack nor where the box sits on the head moves it by more than 2.115's own guard (0.1 sp)."""
        page, box, sp = _t13()
        got = []
        old = HI.SLACK_SPACES
        try:
            for slack in (0.4, 0.5, 0.7):
                HI.SLACK_SPACES = slack
                for dy in (0.0, 0.15, 0.3):
                    b = [box[0], box[1] + dy * sp, box[2], box[3] + dy * sp]
                    r = HI.read_head_ink(page, b, sp, [], head_interior_white, notehead_ink_under)
                    self.assertEqual(r["value"], "hollow", (slack, dy, r))
                    got.append(r["trimmed"])
        finally:
            HI.SLACK_SPACES = old
        arr = np.array(got, dtype=float)
        cx, cy = (arr[:, 0] + arr[:, 2]) / 2.0, (arr[:, 1] + arr[:, 3]) / 2.0
        self.assertLessEqual((cx.max() - cx.min()) / sp, 0.1, got)
        self.assertLessEqual((cy.max() - cy.min()) / sp, 0.1, got)
        # and it is the HEAD, not the box: the trimmed centre stands below the upper-rim box's centre
        self.assertGreater(cy.mean() - (box[1] + box[3]) / 2.0, 0.1 * sp)


class GatherFlag(unittest.TestCase):
    """`gather_head_ink` files nothing with the flag off (the default), one row per head box with it on."""

    def _run(self, flag):
        from tools.omr.staged import gather as G
        from tools.omr.staged.record import Q
        page, box, foreign, sp = _tile(1)

        class Page:
            binary = page

        class PWS:
            pass
        pws = PWS()
        pws.page = Page()

        class Cell:
            page_index, staff_index, measure_index = 0, 0, 0
            bbox_page_px = (0.0, 0.0, float(page.shape[1]), float(page.shape[0]))
            upscale_factor = 1.0
            staff_line_ys_canonical = [10.0 + i * sp for i in range(5)]

        class Det:
            smufl_name = "noteheadBlackOnLine"
            x_canonical, y_canonical = box[0], box[1]
            width_canonical, height_canonical = box[2] - box[0], box[3] - box[1]
        log = G.Log()
        dets = {G.R.cell(0, 0, 0, 0).to_key(): [Det()]}
        old = os.environ.get(HI.ENV)
        os.environ[HI.ENV] = flag
        try:
            G.gather_head_ink(log, pws, [Cell()], {0: (0, 0)}, dets)
        finally:
            if old is None:
                os.environ.pop(HI.ENV, None)
            else:
                os.environ[HI.ENV] = old
        return log.rows(Q.HEAD_INK, G.R.glyph(0, 0, 0, 0, 0)) if hasattr(log, "rows") else []

    def test_flag_off_files_nothing(self):
        self.assertEqual(list(self._run("0")), [])

    def test_flag_on_files_one_hollow_row(self):
        rows = list(self._run("1"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value, "hollow")
        for k in ("trimmed", "extent_sp", "slit", "page_box", "size_margin_sp"):
            self.assertIn(k, rows[0].detail)


if __name__ == "__main__":
    unittest.main()
