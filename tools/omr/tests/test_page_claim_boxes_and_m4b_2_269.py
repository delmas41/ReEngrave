"""ROADMAP 2.269 step 3 (`OMR_PAGE_CLAIM_BOXES`, default OFF) and 2.260c M4b (`OMR_PAGE_BEAMS_RETIRE_A`, default OFF). SYNTHETIC masks and rows; no raster, no detector.

Pins: a dynamic / whole-rest / repeat-dot box names the page strokes with at least COVER_SHARE_MIN of their ink inside it and not a long stroke that only
crosses it (the control that can fail: widen the share and the crossbar is named); ledgers and augmentation dots are NOT named here (M6's, the fence);
a stroke an earlier claim names is contested, never taken; the flag off files nothing. M4b: `live_rows` drops cell reader A's rows only where the
flag is on AND the page filed views; a record without views keeps A; flag off drops the views."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import page_beams as PB
from tools.omr.staged import page_claim_names as PN
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

PWS = SimpleNamespace(page=SimpleNamespace(page_index=0))


def stroke_mask(x0, y0, w, h):
    return (np.ones((h, w), bool), x0, y0)


def pagemap(specs):
    """specs: [(x0, y0, w, h)] -- solid rectangles; scale 1."""
    strokes = [SimpleNamespace(box=(x, y, w, h), kind="blob") for x, y, w, h in specs]
    return SimpleNamespace(strokes=strokes, masks=[stroke_mask(*s) for s in specs], scale=1.0, sp=20.0)


def det(name, x, y, w, h):
    return SimpleNamespace(smufl_name=name, x_canonical=x, y_canonical=y, width_canonical=w, height_canonical=h, category=None)


class Cell:
    page_index, staff_index, measure_index = 0, 0, 0
    bbox_page_px = (0.0, 0.0, 400.0, 100.0)
    upscale_factor = 1.0


def run(dets, pm, log=None, env="1"):
    log = log or Log()
    # 2.288 landing: the REST flag defaults ON now; these 2.269 tests are about the dynamics / repeat-dot step and a synthetic page map, so the rest step is pinned OFF here
    with mock.patch.dict(os.environ, {PN.ENV_BOXES: env, PN.ENV_RESTS: "0"}):
        cen = PN.gather_page_claim_boxes(log, PWS, [Cell()], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): dets}, pm)
    return log, cen


def filed(log):
    return [r for r in log.rows(Q.CLAIMED_AREA, R.page(0), scope=R.Scope.SELF_AND_DESCENDANTS) if (r.detail or {}).get("source") == PN.SOURCE_BOXES
            and (r.detail or {}).get("unit") == PN.UNIT]


class Boxes(unittest.TestCase):
    def test_a_dynamic_box_names_the_strokes_inside_it_by_share(self):
        pm = pagemap([(10, 10, 6, 20), (16, 20, 14, 3), (0, 60, 300, 4)])      # a letter stem, its crossbar, a long beam-like bar far off
        log, cen = run([det("dynamicF", 8, 8, 26, 26)], pm)
        rows = filed(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].value, [0, 1])
        self.assertEqual(rows[0].detail["owner"], "dynamic")
        self.assertEqual(cen["boxes"], 1)

    def test_a_long_stroke_that_only_crosses_the_box_is_not_named(self):
        pm = pagemap([(0, 20, 300, 4)])                                         # a beam running through the box: 26 / 300 of its ink inside
        log, _ = run([det("dynamicF", 100, 8, 26, 26)], pm)
        self.assertEqual(filed(log), [])
        # the control that can fail: with the cut dropped to 0.05 the same box DOES name it
        with mock.patch.object(PN, "strokes_by_share", wraps=PN.strokes_by_share) as w:
            idx = PN.StrokeIndex(*PN._boxes_of(pm))
            self.assertEqual(PN.strokes_by_share(pm, (100, 8, 126, 34), idx, 0.05), [0])
            self.assertEqual(PN.strokes_by_share(pm, (100, 8, 126, 34), idx, 0.5), [])

    def test_whole_rests_and_repeat_dots_are_named_ledgers_and_augmentation_dots_are_not(self):
        pm = pagemap([(10, 10, 20, 6), (50, 10, 6, 6), (80, 10, 30, 3), (120, 10, 5, 5)])
        dets = [det("restWhole", 8, 8, 24, 10), det("repeatDot", 48, 8, 10, 10), det("ledgerLine", 78, 8, 34, 8), det("augmentationDot", 118, 8, 9, 9)]
        log, cen = run(dets, pm)
        owners = sorted(r.detail["owner"] for r in filed(log))
        self.assertEqual(owners, ["dot", "whole_rest"])
        self.assertEqual(sum(cen["by_class"].values()), 2)

    def test_an_earlier_claim_keeps_its_stroke_and_the_later_box_is_contested(self):
        pm = pagemap([(10, 10, 20, 6)])
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, [0], reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner="clef", unit=PN.UNIT, standing="READ",
                    source=PN.SOURCE, page_strokes=[0])
        log, cen = run([det("restWhole", 8, 8, 24, 10)], pm, log=log)
        self.assertEqual(filed(log), [])
        self.assertEqual(cen["contested"], 1)

    def test_the_flag_off_files_nothing(self):
        log, cen = run([det("dynamicF", 8, 8, 26, 26)], pagemap([(10, 10, 6, 20)]), env="0")
        self.assertIsNone(cen)
        self.assertEqual(len(log.rows(Q.CLAIMED_AREA, R.page(0), scope=R.Scope.SELF_AND_DESCENDANTS)), 0)

    def test_the_owner_table_leaves_ledgers_to_m6(self):
        self.assertIsNone(PN.box_owner("ledgerLine"))
        self.assertIsNone(PN.box_owner("augmentationDot"))
        self.assertIsNone(PN.box_owner("noteheadBlack"))
        self.assertEqual(PN.box_owner("dynamicPiano"), "dynamic")


class Retire(unittest.TestCase):
    def _ev(self, with_views):
        log = Log()
        cell = R.cell(0, 0, 0, 0)
        a = log.observe(cell, Q.BEAM_STROKE, (0, 0, 10, 2), reader=READERS.CV_LINES, frame="cell:0", x0=0, x1=10, y_center=1)
        v = log.observe(cell, Q.BEAM_STROKE, (0, 0, 12, 2), reader=READERS.CV_PAGE_BEAMS, frame="cell:0", x0=0, x1=12, y_center=1) if with_views else None
        d = log.observe(cell, Q.BEAM_STROKE, (0, 0, 14, 8), reader=READERS.DETECTOR, frame="cell:0", x0=0, x1=14, y_center=4)
        ev = SimpleNamespace(rows=lambda q, scope=None, subject=None: log.rows(q, subject, scope=scope),
                             refusals=lambda q, scope=None, subject=None: [])
        return ev, cell, (a, v, d)

    def test_flag_on_with_views_drops_a_and_keeps_views_and_detector(self):
        ev, cell, (a, v, d) = self._ev(True)
        with mock.patch.dict(os.environ, {PB.RETIRE_ENV: "1"}):
            got = PB.live_rows(ev, cell, ev.rows(Q.BEAM_STROKE, scope=R.Scope.SELF_AND_ANCESTORS, subject=cell))
        self.assertEqual([r.id for r in got], [v.id, d.id])

    def test_flag_off_drops_the_views(self):
        ev, cell, (a, v, d) = self._ev(True)
        with mock.patch.dict(os.environ, {PB.RETIRE_ENV: "0"}):
            got = PB.live_rows(ev, cell, ev.rows(Q.BEAM_STROKE, scope=R.Scope.SELF_AND_ANCESTORS, subject=cell))
        self.assertEqual([r.id for r in got], [a.id, d.id])

    def test_flag_on_without_views_keeps_a(self):
        ev, cell, (a, v, d) = self._ev(False)
        with mock.patch.dict(os.environ, {PB.RETIRE_ENV: "1"}):
            got = PB.live_rows(ev, cell, ev.rows(Q.BEAM_STROKE, scope=R.Scope.SELF_AND_ANCESTORS, subject=cell))
        self.assertEqual([r.id for r in got], [a.id, d.id])


if __name__ == "__main__":
    unittest.main()
