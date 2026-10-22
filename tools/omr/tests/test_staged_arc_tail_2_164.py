"""ROADMAP 2.164 -- an arc's tail at a bar's left edge boxed as a notehead (STAGED GATHER `gather.gather_head_oval`
-> `Q.HEAD_OVAL` via the pure `head_oval.oval_width`; ADJUDICATE `adjudicate_notehead_is_not_a_notehead`, reason
`is_an_arc_tail`; flag `OMR_ARC_TAIL_NOT_A_HEAD`, default ON since Sean 2026-10-17).

Sean 2026-10-17, on the 2.160 sheets: head boxes at a bar's left edge are "almost entirely tie ends ... or a bar
line". The detector reads one bar's crop at a time; the tie is cut at the barline and its tail is boxed as a head.

CONVENTION ASSUMED: a notehead is an oval ~1 space tall and ~1.25 wide (filled, or an outline whose top and bottom
edges are a space apart); a tie's end is one thin stroke. WHAT WOULD FALSIFY IT: a head Sean values whose columns read
as thin as a tie's stroke. NOT CONFIRMED: the refusal cut (half a head's width) is measured on two plates only.
Every CONTROL_ test is green with the rule absent or present, and `test_the_refusal_needs_the_rule` goes RED when
`_arc_tail_refusal` is removed, so a rule that refuses everything -- or nothing -- cannot pass.
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import gather, head_oval
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Q, READERS

ON = {head_oval.ENV: "1"}
SP = 20.0                        # page px per staff space in the synthetic page


# ── synthetic page rasters (0 = ink, 255 = paper) ────────────────────────────

def _page(lines=True):
    img = np.full((300, 400), 255, np.uint8)
    if lines:
        for k in range(5):
            y = 100 + int(k * SP)
            img[y:y + 3, :] = 0                     # a 3-px staff line
    return img


def _ellipse(img, cx, cy, rx, ry, hollow=False, t=3):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    r = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    m = r <= 1.0
    if hollow:
        inner = ((xx - cx) / max(1, rx - t)) ** 2 + ((yy - cy) / max(1, ry - t)) ** 2 <= 1.0
        m &= ~inner
    img[m] = 0


def _tail(img, x0, x1, y_left, y_right, t=4):
    """A tie's end: one stroke `t` px thick from (x0, y_left) curving to (x1, y_right)."""
    for x in range(x0, x1):
        f = (x - x0) / float(max(1, x1 - x0))
        y = int(round(y_left + (y_right - y_left) * f * f))
        img[y:y + t, x] = 0


class TestOvalWidth(unittest.TestCase):

    def test_a_filled_head_on_a_line_reads_most_of_a_head_wide(self):
        img = _page()
        _ellipse(img, 200, 141, 12.5, 10)            # on the 3rd line
        got = head_oval.oval_width(img, (186, 130, 214, 152), SP)
        self.assertGreaterEqual(got["oval_width_sp"], 0.9, got)

    def test_a_hollow_head_in_a_space_whose_edges_merge_into_the_lines_reads_as_an_oval(self):
        """Its top and bottom outline lie ON the two lines: a bare line is left out, a THICKENED one is kept."""
        img = _page()
        _ellipse(img, 200, 131, 12.5, 15, hollow=True, t=3)       # outline 3-4 px past each line, as printed
        got = head_oval.oval_width(img, (186, 118, 214, 144), SP)
        self.assertGreaterEqual(got["oval_width_sp"], NP.ARC_TAIL_OVAL_MAX_SPACES, got)

    def test_a_tie_tail_crossing_a_line_reads_thin(self):
        img = _page()
        _tail(img, 186, 214, 150, 138)
        got = head_oval.oval_width(img, (186, 130, 214, 155), SP)
        self.assertLess(got["oval_width_sp"], NP.ARC_TAIL_OVAL_MAX_SPACES, got)

    def test_a_barline_with_a_tail_on_it_reads_thin(self):
        img = _page()
        img[100:183, 186:189] = 0                     # the barline, 3 px wide
        _tail(img, 189, 210, 150, 140)
        got = head_oval.oval_width(img, (184, 130, 212, 155), SP)
        self.assertLess(got["oval_width_sp"], NP.ARC_TAIL_OVAL_MAX_SPACES, got)

    def test_declines_off_the_raster_or_without_a_unit(self):
        img = _page()
        self.assertIsNone(head_oval.oval_width(None, (0, 0, 10, 10), SP))
        self.assertIsNone(head_oval.oval_width(img, (0, 0, 10, 10), 0))
        self.assertIsNone(head_oval.oval_width(img, (20, 20, 10, 10), SP))

    def test_flag_is_on_by_default(self):
        """Default ON since the landing (Sean 2026-10-17, "Yes both on"); an explicit off-word or empty disables."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(head_oval.ENV, None)
            self.assertTrue(head_oval.enabled())
        for on in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {head_oval.ENV: on}):
                self.assertTrue(head_oval.enabled())
        for off in ("0", "false", "no", "off", ""):
            with mock.patch.dict(os.environ, {head_oval.ENV: off}):
                self.assertFalse(head_oval.enabled())


# ── GATHER: the row is filed only for a left-edge head, only while the flag is ON ──────────────────────

def _cells_and_dets(head_x_canonical):
    cell = types.SimpleNamespace(staff_index=0, page_index=0, measure_index=1, bbox_page_px=[180, 80, 380, 200],
                                 upscale_factor=1.0, staff_line_ys_canonical=[20, 40, 60, 80, 100])
    det = types.SimpleNamespace(smufl_name="noteheadBlackOnLine", x_canonical=head_x_canonical, y_canonical=50,
                                width_canonical=28, height_canonical=22)
    return [cell], {0: (0, 0)}, {R.cell(0, 0, 0, 1).to_key(): [det]}


class TestGather(unittest.TestCase):

    def _run(self, x, env):
        img = _page()
        _tail(img, 182, 210, 150, 138)
        pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
        cells, local, dets = _cells_and_dets(x)
        log = Log()
        with mock.patch.dict(os.environ, env):
            gather.gather_head_oval(log, pws, cells, local, dets)
        return log.rows(Q.HEAD_OVAL, R.glyph(0, 0, 0, 1, 0))

    def test_a_left_edge_head_gets_its_row(self):
        rows = self._run(2, ON)
        self.assertEqual(len(rows), 1)
        self.assertLess(rows[0].value, NP.ARC_TAIL_OVAL_MAX_SPACES)
        self.assertEqual(rows[0].detail["space_page_px"], 20.0)

    def test_CONTROL_a_head_inside_the_bar_gets_none(self):
        self.assertEqual(len(self._run(60, ON)), 0)

    def test_CONTROL_flag_off_files_nothing(self):
        self.assertEqual(len(self._run(2, {head_oval.ENV: "0"})), 0)


# ── ADJUDICATE ───────────────────────────────────────────────────────────────

PREV, HERE = R.cell(0, 0, 0, 0), R.cell(0, 0, 0, 1)
#: canonical 100 per staff space, page 20 px per staff space: page = cell_x0 + canonical / 5
HEAD_PAGE = (402.0, 190.0, 428.0, 210.0)


def _fixture(oval=0.44, arc_page=(300.0, 196.0, 399.0, 214.0), head_cell=HERE, prev=PREV, head_page=HEAD_PAGE,
             with_oval_row=True):
    log = Log()
    for c, box in ((prev, [100.0, 100.0, 400.0, 300.0]), (head_cell, [400.0, 100.0, 700.0, 300.0])):
        log.observe(c, Q.CELL_BOX, box, reader=READERS.GEOMETRY, frame="cell:%d" % c.cell)
        log.observe(c, Q.CELL_STAFF_SPACE, 100.0, reader=READERS.GEOMETRY, frame="cell:%d" % c.cell)
    g = R.glyph(head_cell.page, head_cell.system, head_cell.staff, head_cell.cell, 0)
    cx = (head_page[0] - 400.0) * 5
    cls = "noteheadBlackOnLine"
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:1", score=0.28)
    log.observe(g, Q.GLYPH_BOX, (cls, cx, 450.0, 130.0, 100.0), reader=READERS.DETECTOR, frame="cell:1",
                score=0.28, category="notehead", bbox_page_px=list(head_page))
    if arc_page is not None:
        a = R.glyph(prev.page, prev.system, prev.staff, prev.cell, 0)
        log.observe(a, Q.ARC_BOX, "tie", reader=READERS.DETECTOR, frame="cell:%d" % prev.cell,
                    bbox_page_px=list(arc_page))
    if with_oval_row:
        log.observe(g, Q.HEAD_OVAL, oval, reader=READERS.CV_HEAD_OVAL, frame="cell:1", oval_width_sp=oval,
                    space_page_px=20.0, left_gap_sp=0.1)
    return log, g


def _nn(log, g):
    adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestArcTailRefusal(unittest.TestCase):

    def test_the_refusal_needs_the_rule(self):
        """RED when `_arc_tail_refusal` is removed: the tie's tail at the left edge is refused, with its margin."""
        log, g = _fixture()
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertTrue(v.value is True and v.reason == "is_an_arc_tail", (v.value, v.reason))
        self.assertGreater(v.margin, 0.0)
        self.assertEqual(v.detail["arc_tail"]["arc_kind"], "tie")

    def test_CONTROL_a_real_tied_to_head_at_the_bar_start_is_kept(self):
        """The same tie, the same left edge -- but the box holds a whole head (Litolff 2/1/1/14/3 reads 1.44)."""
        log, g = _fixture(oval=1.44)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)
        self.assertNotEqual(v.reason, "is_an_arc_tail")

    def test_CONTROL_flag_off_the_box_stands(self):
        log, g = _fixture()
        with mock.patch.dict(os.environ, {head_oval.ENV: "0"}):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_no_arc_in_the_previous_bar_keeps_it(self):
        log, g = _fixture(arc_page=None)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_an_arc_that_ends_inside_the_previous_bar_keeps_it(self):
        """An arc the crop did NOT cut (it ends 2 spaces before the barline) is not this box's arc."""
        log, g = _fixture(arc_page=(250.0, 196.0, 360.0, 214.0))
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_an_arc_on_other_rows_keeps_it(self):
        log, g = _fixture(arc_page=(300.0, 100.0, 399.0, 150.0))
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_head_inside_the_bar_is_kept(self):
        log, g = _fixture(head_page=(440.0, 190.0, 466.0, 210.0))
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_no_oval_row_keeps_it(self):
        log, g = _fixture(with_oval_row=False)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_systems_first_bar_is_kept(self):
        log, g = _fixture(head_cell=R.cell(0, 0, 0, 0), prev=R.cell(0, 0, 0, 5))
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)


if __name__ == "__main__":
    unittest.main()


import pytest as _pytest_2176


@_pytest_2176.fixture(autouse=True)
def _pin_head_on_another_mark_off_2_176(monkeypatch):
    """ROADMAP 2.176 flipped OMR_HEAD_ON_ANOTHER_MARK ON; these fixtures put a head at a system's first cell, so pin it OFF here."""
    monkeypatch.setenv("OMR_HEAD_ON_ANOTHER_MARK", "0")
