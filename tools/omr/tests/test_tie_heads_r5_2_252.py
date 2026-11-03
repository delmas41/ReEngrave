"""ROADMAP 2.252 round 5 -- the tied heads the hole position broke, and the tie a staff line swallowed (STAGED GATHER + ADJUDICATE).

Cause (benchmarks/omr-arc-binding-2026-10/FINDINGS.md, round 5; Sean's r4 tiles 4, 6, 7, 9 and the r4 loss list): of the six tie links
`OMR_HEAD_HOLE_POSITION` lost, the MOVED head was right in three and its partner, left at its box centre, wrong -- the partner's own
hole could not be read: a tall BLACK box round a dyad (tile 9), an arc's end making the head's ink too wide for the witness (tile 6),
an arc opening the slit (tile 4, not fixed: nothing to read). In two more (Litolff p3) the moved head was wrong: the line-cut merge
joined a dyad's two slits round a line, one of them inside the neighbour's box. Brahms tile 12's lower tie lies along a staff line and
was refused as one while the page-wide trace read it as a bowed tie.

Flags: `OMR_HEAD_HOLE_POSITION` (r4 flag, r5 revisions ride on it) and `OMR_ARC_TRACE_NOT_A_LINE`, both default OFF.
"""
from __future__ import annotations

import dataclasses
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import box_kind as BK
from tools.omr.staged import head_hole_position as HP
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import family_precision as FP
from tools.omr.staged.record import Log, Q, READERS

SP = 40.0
HALF = SP / 2.0
TOP = 200.0
LINES = [200, 240, 280, 320, 360]
HOLE_ON = {HP.ENV: "1"}
HOLE_OFF = {HP.ENV: "0"}


@dataclasses.dataclass
class _D:
    smufl_name: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 0.3


def _staff(h=600, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in LINES:
        img[y - 2:y + 2, :] = 0
    return img


def _half(img, cx, cy):
    import cv2
    cv2.ellipse(img, (int(cx), int(cy)), (27, 20), -20, 0, 360, 0, -1)
    cv2.ellipse(img, (int(cx), int(cy)), (20, 8), -30, 0, 360, 255, -1)
    for y in LINES:
        if cy - 20 <= y <= cy + 20:
            img[y - 2:y + 2, int(cx) - 30:int(cx) + 30] = 0


def _read(img, box, others=()):
    pos_box = ((box[1] + box[3]) / 2.0 - TOP) / HALF
    return HP.hole_position(img, box, HALF, TOP, LINES, pos_box, img, box, HALF, others), pos_box


class TestCutPieceOfANeighbour(unittest.TestCase):
    """A head ON a line: its slit is two pieces either side of the line, read as one hole at the line -- unless another head box of
    the cell stands on one of the pieces (that piece is the neighbour's)."""

    def _on_line(self):
        img = _staff()
        _half(img, 200, 240)                       # ON the second line: position 2
        return img, (172, 212, 228, 242)           # a box clipped high: centre reads 1.35

    def test_a_line_head_moves_to_its_cut_hole(self):
        img, box = self._on_line()
        with mock.patch.dict(os.environ, HOLE_ON):
            res, pos_box = _read(img, box)
        self.assertEqual(int(round(pos_box)), 1)
        self.assertEqual(res["position"], 2.0, res)

    def test_RED_a_piece_inside_another_head_box_is_not_this_heads_hole(self):
        img, box = self._on_line()
        neighbour = (172, 243, 228, 275)           # a box below the line holding the lower piece only
        with mock.patch.dict(os.environ, HOLE_ON):
            res, _ = _read(img, box, [neighbour])
        self.assertIsNone(res["position"])
        self.assertEqual(res["why"], "cut_piece_in_another_head")

    def test_a_box_over_both_pieces_is_a_twin_of_the_head_not_a_neighbour(self):
        img, box = self._on_line()
        twin = (170, 216, 230, 262)                # a second box over the whole head (Litolff double-boxes)
        with mock.patch.dict(os.environ, HOLE_ON):
            res, _ = _read(img, box, [twin])
        self.assertEqual(res["position"], 2.0, res)

    def test_OFF_reads_as_round_4(self):
        img, box = self._on_line()
        with mock.patch.dict(os.environ, HOLE_OFF):
            res, _ = _read(img, box, [(172, 243, 228, 275)])
        self.assertEqual(res["position"], 2.0, res)


class TestWideInkOneHeadTall(unittest.TestCase):
    """r4 tile 6's partner: a tie's end runs into the head's side, so its ink is too WIDE for one head; one head TALL still witnesses."""

    def _trim(self, height):
        # the head's trimmed ink: too wide (an arc's end on its side), `height` spaces tall, centred on the second space (position 3)
        top = 260 - height * SP / 2.0
        return {"trimmed": [168, top, 240, top + height * SP], "extent_sp": [1.8, height], "not_one_head": "too_wide"}

    def _read_with(self, height, env):
        img = _staff()
        _half(img, 200, 260)                       # second space: position 3
        box = (172, 262, 228, 290)                 # a clipped box: centre 4.4 -> 4
        with mock.patch.dict(os.environ, env), mock.patch("tools.omr.staged.head_ink.trim_head",
                                                         return_value=self._trim(height)):
            return _read(img, box)

    def test_RED_too_wide_but_one_head_tall_moves_with_the_flag(self):
        res, pos_box = self._read_with(1.14, HOLE_ON)
        self.assertEqual(int(round(pos_box)), 4)
        self.assertEqual(int(round(res["position"])), 3, res)

    def test_CONTROL_too_wide_and_too_tall_still_refuses(self):
        res, _ = self._read_with(1.6, HOLE_ON)
        self.assertIsNone(res["position"])
        self.assertEqual(res["why"], "ink_not_one_head")


class TestTallBlackBox(unittest.TestCase):
    """r4 tile 9's partner (Litolff p10 `10/1/2/0/10`): a BLACK-class box round a dyad of halves and their stem."""

    def _dyad(self):
        img = _staff()
        _half(img, 100, 260)
        _half(img, 100, 300)
        return img, _D("noteheadBlackInSpace", 72, 236, 56, 88)

    def test_RED_black_too_reads_the_two_holes(self):
        img, tall = self._dyad()
        out, info = BK.split_tall_heads([tall], img, SP, TOP, LINES, black_too=True)
        t = info[0]["tall_split"]
        self.assertEqual((t["read"], t["steps"], len(t["added"])), (True, [3, 5], 2))
        self.assertTrue(all(out[k].smufl_name.startswith("noteheadBlack") for k in t["added"]))

    def test_CONTROL_without_black_too_nothing_is_read(self):
        img, tall = self._dyad()
        out, info = BK.split_tall_heads([tall], img, SP, TOP, LINES)
        self.assertEqual((len(out), info), (1, {}))

    def test_CONTROL_a_filled_black_box_has_no_hole_and_is_not_split(self):
        import cv2
        img = _staff()
        cv2.ellipse(img, (100, 260), (27, 20), -20, 0, 360, 0, -1)
        cv2.ellipse(img, (100, 300), (27, 20), -20, 0, 360, 0, -1)
        out, info = BK.split_tall_heads([_D("noteheadBlackInSpace", 72, 236, 56, 88)], img, SP, TOP, LINES, black_too=True)
        self.assertEqual(len(out), 1)
        self.assertFalse(info[0]["tall_split"]["read"])


def _arc_row(log, gi, *, trace=None):
    g = R.glyph(5, 1, 5, 4, gi)
    log.observe(g, Q.ARC_BOX, "tie", reader=READERS.DETECTOR, frame="cell:4", score=0.6,
                x0=0, x1=100, y0=0, y1=10, bbox_page_px=[0, 0, 100, 10])
    log.observe(g, Q.ARC_INK_SHAPE, 0.16, reader=READERS.CV_ARC_INK, frame="cell:4", tall_cols=0.0,
                lines_in_box=1, width_spaces=6.5, height_spaces=0.82)
    if trace is not None:
        log.observe(g, Q.SYSTEM_ARC, trace, reader=READERS.CV_SYSTEM_ARC, frame="page", pieces=[g.to_key()], coverage=[0.85])
    return g


def _decide(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.ARC_IS_NOT_AN_ARC,))
    return log.verdict(Q.ARC_IS_NOT_AN_ARC, g)


class TestTieAlongALine(unittest.TestCase):
    """Brahms p5 `5/1/5/4/8` (Sean's r3/r4 tile 12): a tie along a staff line read 'no curve' once the line was erased."""

    def test_RED_a_traced_tie_is_not_a_staff_line_with_the_flag(self):
        log = Log()
        g = _arc_row(log, 8, trace=FP.ARC_TRACE_TIE_SHAPE)
        with mock.patch.dict(os.environ, {FP.ARC_TRACE_NOT_A_LINE_ENV: "1"}):
            v = _decide(log, g)
        self.assertFalse(v.value)
        self.assertEqual(v.reason, "arc")
        self.assertIn("staff_line_refusal_overruled_by", v.detail)

    def test_OFF_it_is_refused_as_before(self):
        log = Log()
        g = _arc_row(log, 8, trace=FP.ARC_TRACE_TIE_SHAPE)
        with mock.patch.dict(os.environ, {FP.ARC_TRACE_NOT_A_LINE_ENV: "0"}):
            v = _decide(log, g)
        self.assertTrue(v.value)
        self.assertEqual(v.reason, "ink_is_a_staff_line")

    def test_CONTROL_a_trace_of_another_shape_or_none_does_not_overrule(self):
        for trace in ("end_unanchored", "two_positions", None):
            log = Log()
            g = _arc_row(log, 8, trace=trace)
            with mock.patch.dict(os.environ, {FP.ARC_TRACE_NOT_A_LINE_ENV: "1"}):
                v = _decide(log, g)
            self.assertEqual(v.reason, "ink_is_a_staff_line", trace)

    def test_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FP.ARC_TRACE_NOT_A_LINE_ENV, None)
            self.assertTrue(FP.arc_trace_not_a_line_enabled())


class TestJudgedPlaceForAnArcTileOnItsNote(unittest.TestCase):
    """The lane report's judged matcher: a tile that asks about an arc through the NOTE it boxes (2.250's tiles) is found by place."""

    ROW = {"subject": "glyph/2/1/1/11/3", "mark_kind": "slur",
           "position": {"page": 2, "system": 1, "staff": 1, "cell": 11, "page_box": [100.0, 100.0, 125.0, 120.0]}}

    def test_RED_an_arc_kind_tile_boxing_a_head_is_found_at_the_head(self):
        from tools.omr.staged import judged as J
        boxes = {(2, 1, 1, 11): [("glyph/2/1/1/11/3", [101.0, 101.0, 124.0, 121.0], "notehead"),
                                 ("glyph/2/1/1/11/5", [130.0, 80.0, 300.0, 100.0], "structural")]}
        self.assertEqual(J.resolve_place(self.ROW, boxes), ("glyph/2/1/1/11/3", "place"))

    def test_CONTROL_no_box_of_the_tiles_own_kind_there_is_still_no_mark(self):
        from tools.omr.staged import judged as J
        boxes = {(2, 1, 1, 11): [("glyph/2/1/1/11/9", [400.0, 100.0, 425.0, 120.0], "notehead")]}
        self.assertEqual(J.resolve_place(self.ROW, boxes), (None, "place_no_mark"))


if __name__ == "__main__":
    unittest.main()
