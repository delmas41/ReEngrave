"""ROADMAP 2.276 -- tremolo slashes read ONCE on the page and claimed (STAGED GATHER, `page_tremolo.py`, flag `OMR_PAGE_TREMOLO` default OFF).

Every refusal has a positive control in the same class: a real slash across a stem is read and claimed; a head beside a stem, a one-sided flag hook, a stem
with nothing across it are not; flag OFF files nothing.
"""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

import cv2
import numpy as np

from tools.omr.staged import page_tremolo as PT
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS, Scope

SP = 40.0
LINE = 4.0
SX0, SX1 = 300, 306
STOP, SBOT = 100, 340


def _paper():
    return np.full((500, 700), 255, dtype=np.uint8)


def _stem(img):
    img[STOP:SBOT, SX0:SX1] = 0


def _slash(img, y, rise=0.45):
    cv2.line(img, (int(303 - SP), int(y + rise * SP)), (int(303 + SP), int(y - rise * SP)), 0, 16)


def _stems():
    return [(7, (float(SX0), float(STOP), float(SX1 - SX0), float(SBOT - STOP)))]


class TestReadPage(unittest.TestCase):

    def test_a_slash_across_a_stem_is_read(self):
        img = _paper()
        _stem(img)
        _slash(img, 200)
        got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["stem"], 7)
        self.assertEqual(reasons.get("None"), 1)

    def test_a_bare_stem_reads_nothing(self):
        img = _paper()
        _stem(img)
        got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE)
        self.assertEqual(got, [])
        self.assertEqual(reasons, {})

    def test_a_flag_hook_on_one_side_is_not_a_slash(self):
        img = _paper()
        _stem(img)
        pts = np.array([[SX1 - 2, STOP], [SX1 + 20, STOP + 20], [SX1 + 34, STOP + 60]], np.int32)
        cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=16)
        got, _r = PT.read_page(img == 0, _stems(), [], SP, LINE)
        self.assertEqual(got, [])

    def test_the_slash_at_a_head_is_the_heads_only_where_the_reader_knows_the_head(self):
        """Order B (heads known) vetoes a stroke at the stem END that a head box explains; order A (no head known) reads it. Same raster, same finder."""
        img = _paper()
        _stem(img)
        _slash(img, SBOT - 30)
        head = (float(SX0 - SP), float(SBOT - 30 - 0.5 * SP), 2 * SP, SP)
        a, _ = PT.read_page(img == 0, _stems(), [], SP, LINE)
        b, rb = PT.read_page(img == 0, _stems(), [head], SP, LINE)
        self.assertEqual(len(a), 1)
        self.assertEqual(b, [])
        self.assertEqual(rb.get("at_a_head"), 1)

    def test_a_slash_mid_stem_is_read_in_both_orders_even_with_a_head_at_the_end(self):
        img = _paper()
        _stem(img)
        _slash(img, 200)
        head = (float(SX0 - SP), float(SBOT - 0.5 * SP), 2 * SP, SP)
        a, _ = PT.read_page(img == 0, _stems(), [], SP, LINE)
        b, _ = PT.read_page(img == 0, _stems(), [head], SP, LINE)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)


class TestOwnStrokes(unittest.TestCase):

    def test_strokes_held_by_the_slash_box_are_its_own_the_stem_and_far_strokes_are_not(self):
        slash = {"box": [260.0, 160.0, 350.0, 240.0]}
        boxes = [(300, 100, 306, 340), (265, 170, 300, 235), (600, 600, 640, 640), (255, 100, 350, 400)]
        kinds = ["vertical", "blob", "blob", "blob"]
        self.assertEqual(PT.own_strokes(slash, boxes, kinds, stem=0), [1])


class TestFiling(unittest.TestCase):

    def _page(self, img):
        strokes = [SimpleNamespace(kind="vertical", length_sp=6.0, box=(SX0, STOP, SX1 - SX0, SBOT - STOP)),
                   SimpleNamespace(kind="blob", length_sp=2.0, box=(262, 160, 88, 80))]
        pm = SimpleNamespace(strokes=strokes, sp=SP, assembly=SimpleNamespace(canvas=img))
        pws = SimpleNamespace(page=SimpleNamespace(page_index=3), staves=[SimpleNamespace(median_line_thickness_px=LINE)])
        return pm, pws

    def _run(self, env):
        img = _paper()
        _stem(img)
        _slash(img, 200)
        pm, pws = self._page(img)
        log = Log()
        with mock.patch.dict(os.environ, env, clear=False):
            out = PT.gather_page_tremolo(log, pws, [], {}, {}, pm)
        return log, out

    def test_flag_off_files_nothing_and_reads_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != PT.ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            log = Log()
            self.assertIsNone(PT.gather_page_tremolo(log, SimpleNamespace(), [], {}, {}, SimpleNamespace(strokes=[1])))

    def test_flag_on_files_one_claim_with_the_owner_tremolo_and_a_census(self):
        log, out = self._run({PT.ENV: "1"})
        self.assertIsNotNone(out)
        rows = list(log.rows(Q.CLAIMED_AREA, R.page(3), scope=Scope.SELF_AND_DESCENDANTS))
        claims = [r for r in rows if r.value != "census"]
        self.assertEqual(len(claims), 1)
        d = claims[0].detail
        self.assertEqual(d["owner"], "tremolo")
        self.assertEqual(d["unit"], "page_ink")
        self.assertEqual(d["page_strokes"], [1])
        self.assertEqual(claims[0].reader, READERS.CV_PAGE_TREMOLO)
        self.assertEqual(len([r for r in rows if r.value == "census"]), 1)

    def test_the_claim_never_names_the_stem(self):
        log, _out = self._run({PT.ENV: "1"})
        rows = [r for r in log.rows(Q.CLAIMED_AREA, R.page(3), scope=Scope.SELF_AND_DESCENDANTS) if r.value != "census"]
        self.assertNotIn(0, rows[0].detail["page_strokes"])

    def test_the_slash_is_never_filed_as_a_note_value_or_rest(self):
        log, _out = self._run({PT.ENV: "1"})
        for q in (Q.DURATION, Q.NOTEHEAD_CLASS, Q.REST):
            self.assertEqual(list(log.rows(q, R.page(3), scope=Scope.SELF_AND_DESCENDANTS)), [])


if __name__ == "__main__":
    unittest.main()
