"""ROADMAP 2.260a M1: `Q.BARLINE_COLUMN_FIT` -- the tilted line of each barline column, refit in staged from the page raster and the page-wide
barlines. Controls that can fail: a known tilt is recovered; the same raster with ONE staff's rule moved changes the fit (so the fit reads the
raster); a column seen on one staff says slope 0 and says which staves it saw; staff lines alone are not a rule."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import barline_columns as BC
from tools.omr.staged import record as RC
from tools.omr.staged.record import Q

SP = 20
H, W = 1600, 900
# three staves of one system, 5 lines SP apart, 100 px between them
STAVES = [SimpleNamespace(staff_index=i, system_index=0, line_ys=[300 + 400 * i + SP * k for k in range(5)], top_y=300 + 400 * i,
                          bottom_y=300 + 400 * i + 4 * SP, line_spacing_px=float(SP)) for i in range(3)]
SLOPE, X0 = 0.02, 400.0           # 0.02 px per row: 24 px over 1200 rows -- the Litolff p6 drift


def _page(shift=None):
    img = np.full((H, W), 255, np.uint8)
    for s in STAVES:
        for y in s.line_ys:
            img[y - 1:y + 2, 100:800] = 0
        mid = (s.top_y + s.bottom_y) / 2.0
        x = int(round(SLOPE * (mid - 300) + X0)) + (shift or {}).get(s.staff_index, 0)
        img[s.top_y:s.bottom_y + 1, x - 1:x + 2] = 0                      # the rule, 3 px wide, on this staff only
    return img


def _pws(img, x_mean=None):
    mid = [(s.top_y + s.bottom_y) / 2.0 for s in STAVES]
    xm = x_mean if x_mean is not None else SLOPE * (sum(mid) / 3.0 - 300) + X0
    return SimpleNamespace(page=SimpleNamespace(binary=img, page_index=0), staves=STAVES,
                           barlines=[SimpleNamespace(system_index=0, x=xm, y_top=300.0, y_bottom=1100.0)])


class Fit(unittest.TestCase):
    def test_known_tilt_is_recovered(self):
        c = BC.fit_columns(_pws(_page()))
        self.assertEqual(len(c), 1)
        self.assertAlmostEqual(c[0]["slope"], SLOPE, delta=0.004)
        self.assertEqual(c[0]["staves"], [0, 1, 2])
        self.assertLess(c[0]["resid_px"], 1.5)
        self.assertAlmostEqual(BC.x_at(c[0], 700.0), SLOPE * 400.0 + X0, delta=1.5)

    def test_the_fit_reads_the_raster_not_the_mean(self):
        base = BC.fit_columns(_pws(_page()))[0]
        moved = BC.fit_columns(_pws(_page({2: 8}), x_mean=base["x"]))[0]      # CONTROL: one staff's rule 8 px right
        self.assertNotAlmostEqual(base["slope"], moved["slope"], delta=0.002)
        self.assertEqual(moved["staves"], [0, 1, 2])

    def test_one_staff_says_slope_zero_and_names_it(self):
        img = _page()
        for s in STAVES[1:]:
            img[s.top_y - 5:s.bottom_y + 6, 350:460] = 255          # blank the rule on staves 1 and 2 (their lines go too: no matter)
        c = BC.fit_columns(_pws(img))[0]
        self.assertEqual(c["staves"], [0])
        self.assertEqual(c["slope"], 0.0)

    def test_staff_lines_alone_are_not_a_rule(self):
        img = np.full((H, W), 255, np.uint8)
        for s in STAVES:
            for y in s.line_ys:
                img[y - 1:y + 2, 100:800] = 0
        c = BC.fit_columns(_pws(img, x_mean=400.0))[0]
        self.assertEqual(c["staves"], [])
        self.assertEqual(c["slope"], 0.0)


class Gather(unittest.TestCase):
    def _rows(self, log):
        return [o for o in log._obs.values() if o.quantity == Q.BARLINE_COLUMN_FIT]

    def test_default_off_files_nothing(self):
        log = RC.Log()
        with mock.patch.dict(os.environ, {BC.ENV: ""}):
            self.assertEqual(BC.gather_barline_columns(log, _pws(_page())), [])
        self.assertEqual(self._rows(log), [])

    def test_on_files_one_row_per_column(self):
        log = RC.Log()
        with mock.patch.dict(os.environ, {BC.ENV: "1"}):
            BC.gather_barline_columns(log, _pws(_page()))
        rows = self._rows(log)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0].value[0], SLOPE, delta=0.004)
        self.assertEqual(rows[0].detail["staves"], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
