"""ROADMAP 2.240 step 1: `Q.PAGE_MARK` -- boxes of one family from two padded cells on the same page ink are ONE page mark.
A synthetic page of KNOWN geometry (two overlapping cells, heads drawn as ellipses); every control can fail."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import page_marks as PM
from tools.omr.staged import record as RC
from tools.omr.staged.record import Q

H, W = 300, 200
SP = 20                         # staff space, page px
CELL_A = (0, 0, 200, 200)       # staff 0's padded cell
CELL_B = (0, 100, 200, 300)     # staff 1's padded cell: rows 100..200 are seen by both


def _ellipse(ink, cx, cy, rx=11, ry=9):
    yy, xx = np.mgrid[0:H, 0:W]
    ink |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0


def _view(rect, ink):
    """A cell's 'stroke' labels = the page ink inside its rectangle, at scale 1 (one stroke per pixel group is enough here)."""
    x0, y0, x1, y1 = rect
    lab = ink[y0:y1, x0:x1].astype(np.int16)
    return PM.seen_on_page(rect, lab)


def _box(key, cell, gi, fam, pb, ink, rect):
    v = _view(rect, ink)
    return PM.BoxInk(key, cell, gi, fam, "noteheadBlackInSpace" if fam == "head" else "x", tuple(map(float, pb)), PM.box_pixels(v[0], v[1], pb, ink))


def _head_box(cx, cy):
    """A detector head box is a little taller than the head: a stacked third's two boxes overlap (as on the plates)."""
    return (cx - 12, cy - 12, cx + 12, cy + 12)


class OneHeadTwoCells(unittest.TestCase):
    def setUp(self):
        self.ink = np.zeros((H, W), bool)
        _ellipse(self.ink, 100, 150)              # one head in the gap, inside both cells
        self.a = _box("glyph/0/0/0/0/0", (0, 0, 0, 0), 0, "head", _head_box(100, 150), self.ink, CELL_A)
        self.b = _box("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, "head", _head_box(101, 151), self.ink, CELL_B)

    def test_one_head_boxed_from_two_cells_is_one_mark(self):
        m = PM.link([self.a, self.b])
        self.assertEqual(m.mark_of[self.a.key], m.mark_of[self.b.key])
        self.assertEqual(m.why[self.a.key], "shared_ink")
        self.assertEqual(len(m.merged_pairs), 1)

    def test_CONTROL_another_family_on_the_same_ink_is_not_merged(self):
        b = PM.BoxInk(self.b.key, self.b.cell, 0, "rest", "restQuarter", self.b.page_box, self.b.pix)
        m = PM.link([self.a, b])
        self.assertNotEqual(m.mark_of[self.a.key], m.mark_of[b.key])

    def test_CONTROL_two_boxes_over_blank_paper_never_merge_whatever_the_iou(self):
        blank = np.zeros((H, W), bool)
        a = _box("glyph/0/0/0/0/0", (0, 0, 0, 0), 0, "head", _head_box(100, 150), blank, CELL_A)
        b = _box("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, "head", _head_box(100, 150), blank, CELL_B)
        m = PM.link([a, b])
        self.assertNotEqual(m.mark_of[a.key], m.mark_of[b.key])
        self.assertEqual(m.why[a.key], "no_ink")

    def test_a_clipped_view_is_the_same_mark(self):
        # cell B's view cut at its top edge: its box holds only part of the head, all of it shared
        rect = (0, 150, 200, 300)
        b = _box("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, "head", (89, 150, 113, 161), self.ink, rect)
        m = PM.link([self.a, b])
        self.assertEqual(m.mark_of[self.a.key], m.mark_of[b.key])

    def test_twin_ink_collapses(self):
        m = PM.link([self.a, self.b])
        t = PM.twin_ink([self.a, self.b], m.mark_of)["head"]
        self.assertGreater(t["before"], 100)
        self.assertEqual(t["after"], 0)
        # CONTROL: with every box its own mark, the twin ink stays
        t0 = PM.twin_ink([self.a, self.b], {self.a.key: 0, self.b.key: 1})["head"]
        self.assertEqual(t0["after"], t0["before"])


class StackedThird(unittest.TestCase):
    """Two heads a third apart (one space), touching -- one ink component -- seen by both cells. Two real marks."""

    def setUp(self):
        self.ink = np.zeros((H, W), bool)
        _ellipse(self.ink, 100, 140)
        _ellipse(self.ink, 100, 160)
        self.boxes = [
            _box("glyph/0/0/0/0/0", (0, 0, 0, 0), 0, "head", _head_box(100, 140), self.ink, CELL_A),
            _box("glyph/0/0/0/0/1", (0, 0, 0, 0), 1, "head", _head_box(100, 160), self.ink, CELL_A),
            _box("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, "head", _head_box(100, 141), self.ink, CELL_B),
            _box("glyph/0/0/1/0/1", (0, 0, 1, 0), 1, "head", _head_box(100, 161), self.ink, CELL_B),
        ]

    def test_two_marks_each_seen_twice(self):
        m = PM.link(self.boxes)
        ids = [m.mark_of[b.key] for b in self.boxes]
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(ids[0], ids[2])
        self.assertEqual(ids[1], ids[3])
        self.assertNotEqual(ids[0], ids[1])

    def test_CONTROL_the_broken_arm_fuses_them(self):
        m = PM.link(self.boxes, share_min=0.0, guard=False)
        self.assertEqual(len({m.mark_of[b.key] for b in self.boxes}), 1)

    def test_a_mark_never_holds_two_boxes_of_one_cell(self):
        m = PM.link(self.boxes)
        for mem in m.members.values():
            cells = [k.rsplit("/", 1)[0] for k in mem]
            self.assertEqual(len(cells), len(set(cells)))


class UnisonOnTwoStaves(unittest.TestCase):
    def test_two_heads_at_two_page_places_are_two_marks(self):
        ink = np.zeros((H, W), bool)
        _ellipse(ink, 100, 60)      # staff 0's head
        _ellipse(ink, 100, 240)     # staff 1's head (same pitch, another staff)
        a = _box("glyph/0/0/0/0/0", (0, 0, 0, 0), 0, "head", _head_box(100, 60), ink, CELL_A)
        b = _box("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, "head", _head_box(100, 240), ink, CELL_B)
        m = PM.link([a, b])
        self.assertNotEqual(m.mark_of[a.key], m.mark_of[b.key])
        self.assertEqual(m.why[a.key], "alone")


class Deterministic(unittest.TestCase):
    def test_the_readout_of_identical_inputs_is_identical(self):
        st = StackedThird()
        st.setUp()
        r1 = PM.page_report(st.boxes, PM.link(st.boxes))
        r2 = PM.page_report(list(st.boxes), PM.link(list(st.boxes)))
        self.assertEqual(r1, r2)
        self.assertEqual(r1["merged_pairs"], 2)


# ── the GATHER step on fake cells ──

class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.category = "notehead"


def _cell(staff, rect):
    return SimpleNamespace(page_index=0, staff_index=staff, measure_index=0, bbox_page_px=rect, upscale_factor=1.0,
                           image_no_staff=np.zeros((rect[3] - rect[1], rect[2] - rect[0]), np.uint8))


def _res(rect, ink):
    x0, y0, x1, y1 = rect
    return SimpleNamespace(scale=1.0, masks=[(ink[y0:y1, x0:x1].copy(), 0, 0)])


class GatherStep(unittest.TestCase):
    def setUp(self):
        self.ink = np.zeros((H, W), bool)
        _ellipse(self.ink, 100, 150)
        self.pws = SimpleNamespace(page=SimpleNamespace(binary=np.where(self.ink, 0, 255).astype(np.uint8)))
        self.cells = [_cell(0, CELL_A), _cell(1, CELL_B)]
        self.local = {0: (0, 0), 1: (0, 1)}
        self.dets = {RC.cell(0, 0, 0, 0).to_key(): [_Det("noteheadBlackInSpace", 88, 140, 24, 20)],
                     RC.cell(0, 0, 1, 0).to_key(): [_Det("noteheadBlackInSpace", 89, 41, 24, 20)]}
        self.strokes = {(0, 0, 0, 0): _res(CELL_A, self.ink), (0, 0, 1, 0): _res(CELL_B, self.ink)}

    def _rows(self, log):
        return [o for o in log._obs.values() if o.quantity == Q.PAGE_MARK]

    def test_off_files_nothing(self):
        log = RC.Log()
        with mock.patch.dict(os.environ, {PM.ENV: "0"}):
            self.assertIsNone(PM.gather_page_marks(log, self.pws, self.cells, self.local, self.dets, self.strokes))
        self.assertEqual(self._rows(log), [])

    def test_on_files_one_row_per_box_with_one_shared_ordinal(self):
        log = RC.Log()
        with mock.patch.dict(os.environ, {PM.ENV: "1"}):
            PM.gather_page_marks(log, self.pws, self.cells, self.local, self.dets, self.strokes)
        rows = self._rows(log)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].value, rows[1].value)
        self.assertEqual(rows[0].detail["why"], "shared_ink")
        self.assertEqual(sorted(rows[0].detail["cells"]), [[0, 0, 0], [0, 1, 0]])

    def test_a_cell_without_a_stroke_map_abstains_per_box(self):
        log = RC.Log()
        self.strokes[(0, 0, 1, 0)] = "no_mask"
        with mock.patch.dict(os.environ, {PM.ENV: "1"}):
            PM.gather_page_marks(log, self.pws, self.cells, self.local, self.dets, self.strokes)
        ab = [a for a in log._abs.values() if a.quantity == Q.PAGE_MARK]
        self.assertEqual(len(ab), 1)
        self.assertEqual(len(self._rows(log)), 1)


if __name__ == "__main__":
    unittest.main()
