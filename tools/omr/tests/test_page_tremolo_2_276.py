"""ROADMAP 2.276 -- tremolo slashes read ONCE on the page and claimed (STAGED GATHER, `page_tremolo.py`, flag `OMR_PAGE_TREMOLO` default ON).

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


def _head(img, cy, side="L"):
    """A heavy filled head blob beside the stem at height `cy` (1.2 sp wide, 0.9 sp tall)."""
    cx = SX0 - 24 if side == "L" else SX1 + 24
    cv2.ellipse(img, (cx, cy), (26, 30), 0, 0, 360, 0, -1)


class TestStemEndTest(unittest.TestCase):
    """ROADMAP 2.276 r2 (Sean 2026-11-09): a slash is never at or past the stem's HEAD end; from ink alone; abstains when the ink cannot tell."""

    def test_a_slash_away_from_the_head_end_is_kept(self):
        img = _paper()
        _stem(img)
        _head(img, SBOT - 10)
        _slash(img, 150)
        got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE)
        self.assertEqual(len(got), 1)
        self.assertEqual(reasons.get("end:ok"), 1)

    def test_a_slash_at_the_head_end_is_refused_by_the_end_test(self):
        img = _paper()
        _stem(img)
        _head(img, SBOT - 10)
        _slash(img, 150)
        with mock.patch.object(PT, "head_end_verdict", return_value="refuse"):      # the geometry of a slash touching a head defeats the finder first; the verdict is tested alone below
            got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE)
        self.assertEqual(got, [])
        self.assertEqual(reasons.get("at_head_end"), 1)

    def test_a_stem_whose_head_end_the_ink_cannot_tell_abstains_and_keeps_the_slash(self):
        """Blobs at BOTH ends (a chord, a fused neighbour) and at NEITHER: no refusal on a guess."""
        for both in (True, False):
            img = _paper()
            _stem(img)
            if both:
                _head(img, SBOT - 10)
                _head(img, STOP + 10, "R")
            _slash(img, 200)
            got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE)
            self.assertEqual(len(got), 1, both)
            self.assertEqual(reasons.get("end:abstain"), 1, both)

    def test_the_verdict_alone(self):
        img = _paper()
        _stem(img)
        _head(img, STOP + 10, "R")
        box = _stems()[0][1]
        self.assertEqual(PT.head_end_verdict(img == 0, box, STOP + 20, SP), "refuse")
        self.assertEqual(PT.head_end_verdict(img == 0, box, STOP - 15, SP), "refuse")      # past the end
        self.assertEqual(PT.head_end_verdict(img == 0, box, 250, SP), "ok")


class TestHeldByAnEarlierRead(unittest.TestCase):
    """ROADMAP 2.276 r3 (Sean 2026-10-16 reading order: beam / flag before the slash, which never overturns them; dynamics claim first): a candidate that lies inside the
    detector's read of a dynamic letter, a beam or a flag is that mark's ink. Each refusal has its positive control: the same raster, no earlier read there, is a slash."""

    def _raster(self):
        img = _paper()
        _stem(img)
        _slash(img, 200)
        return img

    def test_no_earlier_read_there_the_slash_is_kept(self):
        got, reasons = PT.read_page(self._raster() == 0, _stems(), [], SP, LINE, held=[(0.0, 0.0, 40.0, 40.0)])
        self.assertEqual(len(got), 1)
        self.assertNotIn("held_by_earlier_read", reasons)

    def test_an_earlier_read_over_the_candidate_holds_it(self):
        img = self._raster()
        a, _ = PT.read_page(img == 0, _stems(), [], SP, LINE)
        box = a[0]["box"]
        held = [(box[0] - 5.0, box[1] - 5.0, box[2] - box[0] + 10.0, box[3] - box[1] + 10.0)]
        got, reasons = PT.read_page(img == 0, _stems(), [], SP, LINE, held=held)
        self.assertEqual(got, [])
        self.assertEqual(reasons.get("held_by_earlier_read"), 1)

    def test_a_read_that_holds_less_than_the_register_cut_keeps_it(self):
        img = self._raster()
        box = PT.read_page(img == 0, _stems(), [], SP, LINE)[0][0]["box"]
        third = [(box[0], box[1], (box[2] - box[0]) * 0.3, box[3] - box[1])]
        got, _r = PT.read_page(img == 0, _stems(), [], SP, LINE, held=third)
        self.assertEqual(len(got), 1)

    def test_held_share_alone(self):
        self.assertEqual(PT.held_share([0, 0, 10, 10], []), 0.0)
        self.assertAlmostEqual(PT.held_share([0, 0, 10, 10], [(0, 0, 5, 10)]), 0.5)
        self.assertEqual(PT.held_share([0, 0, 10, 10], [(20, 20, 5, 5)]), 0.0)

    def test_the_cut_is_the_registers(self):
        from tools.omr.staged import claims as CL
        self.assertEqual(PT.HELD_SHARE_MIN, CL.INSIDE_SHARE_MIN)


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

    def test_flag_zero_files_nothing_and_reads_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != PT.ENV}
        env[PT.ENV] = "0"
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
        self.assertEqual(len(rows), 1)

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
