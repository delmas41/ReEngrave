"""ROADMAP 2.195 step 1: `Q.STROKE`. A synthetic cell of KNOWN geometry (a stem, a filled head, a beam, a ledger rung, a slanted bar) must come
back as those strokes with those measurements, and every control below must be able to FAIL: a broken kernel, a flipped angle or a wrong
staff-step reference changes the answer the test pins."""
import os
import unittest

import numpy as np

from tools.omr.staged import stroke_map as SM

SP = 100          # canonical px per space (the real cells are 90-100)
LINES = [300 + SP * i for i in range(5)]


def _cell(w=1400, h=1000):
    img = np.full((h, w), 255, np.uint8)
    raw = img.copy()
    for y in LINES:                                   # raw raster keeps the staff lines; the erased one does not
        raw[y - 3:y + 4, :] = 0
    return img, raw


def _fill(img, x0, y0, x1, y1):
    img[y0:y1, x0:x1] = 0


def _build():
    img, raw = _cell()
    _fill(img, 200, 350, 220, 700)                    # stem: 0.2 sp x 3.5 sp
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    img[((xx - 150) / 65.0) ** 2 + ((yy - 700) / 50.0) ** 2 <= 1.0] = 0   # filled head 1.3 x 1.0 sp
    _fill(img, 600, 340, 1000, 390)                   # beam 4 sp x 0.5 sp
    _fill(img, 700, 800, 950, 812)                    # ledger rung 2.5 sp x 0.12 sp
    return img, raw


class StrokeMap(unittest.TestCase):
    def setUp(self):
        img, raw = _build()
        self.res = SM.map_strokes(img, SP, LINES, raw)

    def _one(self, kind, near):
        c = [s for s in self.res.strokes if s.kind == kind and abs(s.box[0] - near[0]) < 80 and abs(s.box[1] - near[1]) < 80]
        self.assertEqual(len(c), 1, (kind, near, [(s.kind, s.box) for s in self.res.strokes]))
        return c[0]

    def test_kinds_and_sizes(self):
        stem = self._one("vertical", (200, 350))
        self.assertAlmostEqual(stem.length_sp, 3.5, delta=0.5)      # the stem's own pixels run on through the head's right edge
        self.assertAlmostEqual(stem.angle_deg, 90.0, delta=2)
        self.assertAlmostEqual(stem.thickness_sp, 0.2, delta=0.07)
        beam = self._one("horizontal", (600, 340))
        self.assertAlmostEqual(beam.length_sp, 4.0, delta=0.25)
        self.assertAlmostEqual(beam.thickness_sp, 0.5, delta=0.08)
        self.assertAlmostEqual(beam.angle_deg, 0.0, delta=2)
        rung = self._one("horizontal", (700, 800))
        self.assertAlmostEqual(rung.length_sp, 2.5, delta=0.25)
        head = self._one("blob", (85, 650))
        self.assertAlmostEqual(head.hole_share, 0.0, delta=0.02)
        self.assertGreater(head.fill, 0.6)

    def test_ends_in_steps_against_the_local_staff(self):
        stem = self._one("vertical", (200, 350))
        top, bottom = sorted(stem.end_steps)
        # y 350 is half a space below the top line (300): step 1; y 700 is 4 spaces below: step 8 -> the stem runs from step 1 to 8
        self.assertAlmostEqual(top, 1.0, delta=0.3)
        self.assertAlmostEqual(bottom, 8.0, delta=0.9)

    def test_touch_between_stem_and_head(self):
        stem = self._one("vertical", (200, 350))
        head = self._one("blob", (85, 650))
        j = self.res.strokes.index(head)
        self.assertIn(j, [t[0] for t in stem.touches])

    def test_tilted_staff_is_measured_locally(self):
        img, raw = _cell()
        for x in range(raw.shape[1]):                 # the staff drops 30 px across the cell
            raw[:, x] = 255
            for y in LINES:
                yy = y + int(30 * x / raw.shape[1])
                raw[yy - 3:yy + 4, x] = 0
        _fill(img, 100, 350, 120, 700)
        _fill(img, 1250, 350, 1270, 700)
        res = SM.map_strokes(img, SP, LINES, raw)
        left, right = [s for s in res.strokes if s.kind == "vertical"]
        self.assertTrue(res.staff_local)
        self.assertGreater(right.lines_left[0] - left.lines_left[0], 20)      # the line is lower at the right stem
        # a stem whose top is 50 px under the top line at its OWN x sits at step 1 on either side
        self.assertAlmostEqual(left.end_steps[0] if left.ends[0][1] < left.ends[1][1] else left.end_steps[1], 1.0, delta=0.4)
        self.assertAlmostEqual(right.end_steps[0] if right.ends[0][1] < right.ends[1][1] else right.end_steps[1], 0.4, delta=0.5)

    def test_specks_are_counted_not_filed(self):
        img, raw = _build()
        _fill(img, 900, 900, 906, 906)
        res = SM.map_strokes(img, SP, LINES, raw)
        self.assertEqual(res.n_below_floor, 1)
        self.assertEqual(len(res.strokes), len(self.res.strokes))

    def test_deterministic(self):
        img, raw = _build()
        a = SM.map_strokes(img, SP, LINES, raw)
        self.assertEqual([s.__dict__ for s in a.strokes], [s.__dict__ for s in self.res.strokes])

    def test_empty_cell(self):
        img, raw = _cell()
        r = SM.map_strokes(img, SP, LINES, raw)
        self.assertEqual((r.strokes, r.n_below_floor), ([], 0))

    # ---- the controls: each must be able to fail ----
    def test_control_a_broken_vertical_kernel_loses_the_stem(self):
        old = SM.V_MIN_SPACES
        try:
            SM.V_MIN_SPACES = 6.0                     # longer than any stroke here
            img, raw = _build()
            res = SM.map_strokes(img, SP, LINES, raw)
        finally:
            SM.V_MIN_SPACES = old
        self.assertFalse([s for s in res.strokes if s.kind == "vertical"])

    def test_control_a_flipped_staff_reference_moves_the_steps(self):
        img, raw = _build()
        res = SM.map_strokes(img, SP, [y + 100 for y in LINES], None)      # nominal lines a space too low, no raw raster
        stem = [s for s in res.strokes if s.kind == "vertical"][0]
        self.assertNotAlmostEqual(min(stem.end_steps), 1.0, delta=0.5)
        self.assertFalse(res.staff_local)

    def test_control_angle_sign(self):
        img, raw = _cell()
        for x in range(600, 1000):                    # a beam rising to the right by 60 px
            y = 400 - int(60 * (x - 600) / 400)
            img[y:y + 40, x] = 0
        res = SM.map_strokes(img, SP, LINES, raw)
        beam = [s for s in res.strokes if s.kind == "horizontal"][0]
        self.assertGreater(beam.angle_deg, 5)          # counter-clockwise on the page: rising = positive
        self.assertLess(beam.angle_deg, 15)


class StrokeFlag(unittest.TestCase):
    def test_default_on_and_explicit_off(self):
        from tools.omr.staged import gather as G
        old = os.environ.pop(G.STROKE_MAP_ENV, None)
        try:
            self.assertTrue(G.stroke_map_enabled())
            for word, want in (("1", True), ("on", True), ("", True), ("0", False), ("false", False), ("no", False), ("off", False)):
                os.environ[G.STROKE_MAP_ENV] = word
                self.assertIs(G.stroke_map_enabled(), want, word)
        finally:
            os.environ.pop(G.STROKE_MAP_ENV, None)
            if old is not None:
                os.environ[G.STROKE_MAP_ENV] = old

    def test_rows_filed_only_when_on(self):
        from tools.omr.staged import gather as G
        from tools.omr.staged.record import Q

        class C:
            page_index, system_index, staff_index, measure_index = 0, 0, 0, 0
            staff_line_ys_canonical = LINES
            upscale_factor = 2.0
            bbox_page_px = (10, 20, 710, 520)

        c = C()
        c.image_no_staff, c.binary = _build()
        old = os.environ.get(G.STROKE_MAP_ENV)
        try:
            counts = {}
            for word in ("0", "1"):
                os.environ[G.STROKE_MAP_ENV] = word
                log = G.Log()
                G.gather_stroke_map(log, [c], {0: (0, 0)})
                counts[word] = [r for r in log.all_rows() if r.quantity == Q.STROKE]
            self.assertEqual(counts["0"], [])
            rows = counts["1"]
            self.assertGreaterEqual(len(rows), 4)
            self.assertEqual({r.value for r in rows} - set(SM.KINDS), set())
            self.assertTrue(all("bbox_page_px" in r.detail for r in rows))
            self.assertEqual(len({r.subject for r in rows}), len(rows))
        finally:
            if old is None:
                os.environ.pop(G.STROKE_MAP_ENV, None)
            else:
                os.environ[G.STROKE_MAP_ENV] = old


if __name__ == "__main__":
    unittest.main()
