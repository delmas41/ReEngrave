"""ROADMAP 2.260a M2: the PAGE stroke map (`OMR_PAGE_STROKES`). A synthetic two-staff page of KNOWN geometry: a stem crossing the gap between the staves
(one stroke on the page, two cut pieces in the cells), a head touching a TILTED barline (carved first, so it does not fuse with the rule), the rule itself
(ONE stroke, not two half strokes). Controls that can fail: a perturbed raster breaks stroke-for-stroke parity inside a band; the carve off fuses the
head to the rule; the flag off files nothing."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import barline_columns as BC
from tools.omr.staged import page_strokes as PS
from tools.omr.staged import record as RC
from tools.omr.staged import stroke_map as SM
from tools.omr.staged.record import Q

SP = 20
H, W = 640, 1000
TOP = [100, 400]
SLOPE, X0 = 0.01, 700.0
UP = 2


def _lines(img, t):
    for k in range(5):
        img[t + SP * k - 1:t + SP * k + 2, 50:950] = 0


def _marks(img):
    img[190:431, 299:302] = 0                                        # a stem from staff 1's gap into staff 2: crosses the gap
    yy, xx = np.ogrid[:H, :W]
    img[((xx - 305) / 10.0) ** 2 + ((yy - 190) / 8.0) ** 2 <= 1.0] = 0   # its head, at the bottom of staff 1
    for y in range(100, 481):                                        # the TILTED rule, 3 px, through staff 1, the gap and staff 2
        x = int(round(SLOPE * y + X0))
        img[y, x - 1:x + 2] = 0
    img[((xx - (int(SLOPE * 150 + X0) - 11)) / 10.0) ** 2 + ((yy - 150) / 8.0) ** 2 <= 1.0] = 0   # a head touching the rule's left side


def _build():
    marks = np.full((H, W), 255, np.uint8)
    _marks(marks)
    page = marks.copy()
    for t in TOP:
        _lines(page, t)
    cells = []
    for i, t in enumerate(TOP):
        y0, y1 = t - 3 * SP, t + 4 * SP + 3 * SP
        crop = marks[y0:y1, 0:W]                                     # the erased cell: the marks, no lines
        img = np.repeat(np.repeat(crop, UP, 0), UP, 1)
        cells.append(SimpleNamespace(page_index=0, system_index=0, staff_index=i, measure_index=0, bbox_page_px=(0, y0, W, y1),
                                     image_no_staff=img, upscale_factor=float(UP), binary=np.repeat(np.repeat(page[y0:y1], UP, 0), UP, 1)))
    staves = [SimpleNamespace(staff_index=i, system_index=0, line_ys=[t + SP * k for k in range(5)], top_y=t, bottom_y=t + 4 * SP,
                              line_spacing_px=float(SP)) for i, t in enumerate(TOP)]
    barline = SimpleNamespace(system_index=0, x=SLOPE * 290 + X0, y_top=100.0, y_bottom=480.0)
    pws = SimpleNamespace(page=SimpleNamespace(binary=page, page_index=0), staves=staves, barlines=[barline])
    return pws, cells, {0: (0, 0), 1: (0, 1)}


def _box(st):
    return (st.box[0], st.box[1], st.box[0] + st.box[2], st.box[1] + st.box[3])


class PageMap(unittest.TestCase):
    def setUp(self):
        self.pws, self.cells, self.local = _build()
        self.cols = BC.fit_columns(self.pws)

    def test_the_column_is_fitted_tilted(self):
        self.assertEqual(len(self.cols), 1)
        self.assertAlmostEqual(self.cols[0]["slope"], SLOPE, delta=0.003)

    def test_one_stem_across_the_gap_one_rule_and_a_separate_head(self):
        pm = PS.map_page(self.pws, self.cells, self.local, {}, self.cols)
        stems = [s for s in pm.strokes if s.kind == "vertical" and abs(s.box[0] - 299) <= 3]
        self.assertEqual(len(stems), 1, [(s.kind, s.box) for s in pm.strokes])
        self.assertGreaterEqual(stems[0].length_sp, 11.0)                       # 240 px / 20: the cells cut it in two
        self.assertEqual(len(pm.barlines), 1)                                   # ONE rule through both staves
        b = pm.barlines[0]["box"]
        self.assertLessEqual(b[1], 105)
        self.assertGreaterEqual(b[3], 475)
        # no rule-like vertical stroke is left in the raster beside it
        rule_like = [s for s in pm.strokes if s.kind == "vertical" and s.length_sp >= 3.0 and abs(s.box[0] - (SLOPE * (s.box[1] + s.box[3] / 2.0) + X0)) <= 12]
        self.assertEqual(rule_like, [])
        # the head that touched the rule is its own stroke, off the rule
        head = [s for s in pm.strokes if s.kind == "blob" and abs(s.box[0] + s.box[2] / 2.0 - 689) <= 8 and abs(s.box[1] + s.box[3] / 2.0 - 150) <= 8]
        self.assertEqual(len(head), 1, [(s.kind, s.box) for s in pm.strokes if s.kind == "blob"])
        self.assertGreaterEqual(head[0].box[2], 17)                              # the whole head, 19 x 16 px: carved clear of the rule
        self.assertGreaterEqual(head[0].box[3], 14)
        self.assertLess(head[0].length_sp, 2.0)

    def test_without_the_carve_the_head_fuses_with_the_rule(self):
        # CONTROL: the same page, the carve skipped -> the head and the rule are one stroke, not a head
        asm = PS.assemble(self.pws, self.cells)
        res = SM.map_strokes(asm.canvas, float(SP), [], self.pws.page.binary,
                             staff_override=PS.PageStaff(SM._reduce_float(self.pws.page.binary, 0.8), self.pws.staves, 0.8, SM.TARGET_SP_PX))
        whole_head = [s for s in res.strokes if s.kind == "blob" and s.box[2] >= 17 and s.box[3] >= 14
                      and abs(s.box[0] + s.box[2] / 2.0 - 689) <= 8 and abs(s.box[1] + s.box[3] / 2.0 - 150) <= 8]
        self.assertEqual(whole_head, [])

    def test_the_stroke_is_read_against_its_own_staff(self):
        pm = PS.map_page(self.pws, self.cells, self.local, {}, self.cols)
        head = [(s, so) for s, so in zip(pm.strokes, pm.staff_of) if s.kind == "blob" and abs(s.box[0] + s.box[2] / 2.0 - 689) <= 8]
        self.assertEqual(head[0][1], (0, 0))
        self.assertGreater(head[0][0].lines_left[0], 0)

    def test_parity_inside_a_band_and_a_perturbed_raster_breaks_it(self):
        pm = PS.map_page(self.pws, self.cells, self.local, {}, self.cols)
        pm_bad = PS.map_page(self.pws, self.cells, self.local, {}, self.cols, assembly=self._shifted())
        real, bad = self._parity(pm), self._parity(pm_bad)
        self.assertGreaterEqual(real, 0.9)
        self.assertLess(bad, 0.5)

    def _shifted(self):
        asm = PS.assemble(self.pws, self.cells)
        for _s, y0, y1 in PS.bands(self.pws):
            asm.canvas[y0:y1] = np.roll(asm.canvas[y0:y1], 45, axis=1)
        return asm

    def _parity(self, pm):
        """Share of the strokes the CELL reader finds wholly inside a staff band (the stem excluded: it leaves the band) that the page map has too."""
        page_boxes = [(s.kind, _box(s)) for s in pm.strokes]
        n = hit = 0
        for c, (_s, y0, y1) in zip(self.cells, PS.bands(self.pws)):
            res = SM.map_strokes(c.image_no_staff[::UP, ::UP], float(SP), [(t - c.bbox_page_px[1]) for t in self.pws.staves[c.staff_index].line_ys], None)
            for st in res.strokes:
                x, yy, w, h = st.box
                b = (x, yy + c.bbox_page_px[1], x + w, yy + h + c.bbox_page_px[1])
                if b[1] < y0 or b[3] > y1 or st.cut or b[2] > 600:        # (right of x=600: the tilted rule and the head on it -- the carve changes those on purpose)
                    continue
                n += 1
                for k, pb in page_boxes:
                    if k == st.kind and min(b[2], pb[2]) > max(b[0], pb[0]) and min(b[3], pb[3]) > max(b[1], pb[1]):
                        ix = (min(b[2], pb[2]) - max(b[0], pb[0])) * (min(b[3], pb[3]) - max(b[1], pb[1]))
                        if ix / float((b[2] - b[0]) * (b[3] - b[1]) + (pb[2] - pb[0]) * (pb[3] - pb[1]) - ix) >= 0.5:
                            hit += 1
                            break
        self.assertGreater(n, 0)
        return hit / float(n)


class Assembly(unittest.TestCase):
    def test_a_band_takes_its_cell_and_the_gap_takes_the_page(self):
        pws, cells, _local = _build()
        asm = PS.assemble(pws, cells)
        c = asm.canvas
        self.assertEqual(int((c[TOP[0] + SP * 2 - 1:TOP[0] + SP * 2 + 2, 60:90] == 0).sum()), 0)     # the staff line is erased inside the band
        self.assertEqual(int((pws.page.binary[TOP[0] + SP * 2 - 1:TOP[0] + SP * 2 + 2, 60:90] == 0).sum()) > 0, True)
        self.assertEqual(int((c[250, 299:302] == 0).sum()), 3)                                       # the stem in the gap: the page's own ink
        self.assertEqual(asm.stats["band_placed_twice_px"], 0)

    def test_a_band_no_cell_covers_loses_its_staff_lines_and_is_counted(self):
        pws, cells, _local = _build()
        asm = PS.assemble(pws, cells[:1])                                                            # staff 2 has no cell
        y = TOP[1] + SP * 2
        self.assertEqual(int((asm.canvas[y - 1:y + 2, 60:900] == 0).sum()), 0)
        self.assertGreater(asm.stats["band_uncovered_px"], 0)
        self.assertGreater(asm.stats["line_ink_removed_px"], 0)


class Gather(unittest.TestCase):
    def _rows(self, log):
        return [o for o in log._obs.values() if o.quantity == Q.PAGE_STROKE]

    def test_off_files_nothing(self):
        pws, cells, local = _build()
        log = RC.Log()
        with mock.patch.dict(os.environ, {PS.ENV: "0", "OMR_PAGE_CLAIMS": "0"}):
            self.assertIsNone(PS.gather_page_strokes(log, pws, cells, local, {}))
        self.assertEqual(self._rows(log), [])

    def test_on_files_a_row_per_stroke_and_a_barline(self):
        pws, cells, local = _build()
        log = RC.Log()
        with mock.patch.dict(os.environ, {PS.ENV: "1"}):
            pm = PS.gather_page_strokes(log, pws, cells, local, {})
        rows = self._rows(log)
        self.assertEqual(len(rows), len(pm.strokes) + len(pm.barlines))
        self.assertEqual([r.value for r in rows].count("barline"), 1)
        self.assertTrue(all(r.subject.to_key() == RC.page(0).to_key() for r in rows))


if __name__ == "__main__":
    unittest.main()
