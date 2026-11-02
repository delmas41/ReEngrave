"""ROADMAP 2.252 -- a TALL hollow head box is read for the heads inside it by their holes (STAGED GATHER + ADJUDICATE, flag
`OMR_TALL_HEAD_SPLIT`, default OFF; `tools/omr/staged/box_kind.py` 2b).

The cause (Sean's 2.250 r2 wide tiles 2, 4, 8, 11, 2026-11-01: "two half notes in it a third apart. Both notes have ties attached"):
the detector boxed a dyad of halves as ONE head box 2-2.6 spaces tall (Litolff p2 `glyph/2/1/1/12/3`, `2/1/2/12/2`, p3 `3/0/4/4/11`,
p10 `10/1/4/1/2`), and no stage read a tall head box for the heads inside -- one note at the box centre's step, between the two printed
notes. Measured on the 20261031-night record's master cells (probe_holes, 2.252): every such box holds two slit holes exactly on the
grid (steps 1.03/3.05, -1.11/1.01, 5.03/7.01, 0.90/3.14); a single half ON a line shows its slit cut in two by the line, 0.26-0.36 sp
either side of it.
"""
from __future__ import annotations

import dataclasses
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import box_kind as BK
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

ON = {BK.TALL_ENV: "1"}
OFF = {BK.TALL_ENV: "0"}
SP = 40.0
TOP = 200.0
LINES = [200, 240, 280, 320, 360]


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
    cv2.ellipse(img, (int(cx), int(cy)), (20, 8), -30, 0, 360, 255, -1)     # the slit
    for y in LINES:                                                           # a line runs on through the head (and its slit)
        if cy - 20 <= y <= cy + 20:
            img[y - 2:y + 2, int(cx) - 30:int(cx) + 30] = 0


class TestHoles(unittest.TestCase):

    def test_a_dyad_a_third_apart_is_two_heads_on_the_grid_RED(self):
        img = _staff()
        _half(img, 100, 260)                       # step 3
        _half(img, 100, 300)                       # step 5
        holes = BK.head_holes(BK.cell_ink(img), (72, 238, 128, 322), SP, TOP, LINES)
        self.assertEqual(BK.heads_from_holes(holes), [3, 5], holes)

    def test_TWIN_one_half_on_a_line_is_one_hole_never_two_heads(self):
        img = _staff()
        _half(img, 100, 280)                       # ON the third line: the line cuts its slit in two
        img[180:280, 125:129] = 0                  # its stem's ink makes the box tall
        holes = BK.head_holes(BK.cell_ink(img), (72, 220, 130, 302), SP, TOP, LINES)
        self.assertEqual(len(holes), 1, holes)
        self.assertEqual(round(holes[0]["step"]), 4)
        self.assertIsNone(BK.heads_from_holes(holes))

    def test_heads_from_holes_refuses_off_grid_and_seconds(self):
        self.assertIsNone(BK.heads_from_holes([{"step": 1.0}, {"step": 3.5}]))     # a hole off the grid
        self.assertIsNone(BK.heads_from_holes([{"step": 1.0}, {"step": 2.0}]))     # a second is set in two columns
        self.assertIsNone(BK.heads_from_holes([{"step": 1.0}]))
        self.assertEqual(BK.heads_from_holes([{"step": -1.1}, {"step": 1.01}]), [-1, 1])


class TestSplit(unittest.TestCase):

    def test_the_tall_box_gets_one_box_per_head_RED(self):
        img = _staff()
        _half(img, 100, 260)
        _half(img, 100, 300)
        tall = _D("noteheadHalfInSpace", 72, 236, 56, 88)                 # 2.2 sp
        out, info = BK.split_tall_heads([tall], img, SP, TOP, LINES)
        t = info[0]["tall_split"]
        self.assertTrue(t["read"])
        self.assertEqual((t["steps"], len(t["added"]), t["covered"]), ([3, 5], 2, 0))
        heads = [out[k] for k in t["added"]]
        self.assertEqual([(h.y_canonical + h.height_canonical / 2.0 - TOP) / (SP / 2) for h in heads], [3.0, 5.0])
        self.assertEqual([h.smufl_name for h in heads], ["noteheadHalfInSpace", "noteheadHalfInSpace"])
        self.assertIs(out[0], tall)                                       # every detector glyph index unchanged

    def test_a_head_box_already_on_one_head_covers_it(self):
        img = _staff()
        _half(img, 100, 260)
        _half(img, 100, 300)
        upper = _D("noteheadHalfInSpace", 72, 238, 56, 46)                # 1.15 sp: one head
        tall = _D("noteheadHalfInSpace", 72, 236, 56, 88)
        out, info = BK.split_tall_heads([upper, tall], img, SP, TOP, LINES)
        t = info[1]["tall_split"]
        self.assertEqual((len(t["added"]), t["covered"]), (1, 1))
        self.assertEqual(info[0]["tall_split"], {"covers_hole_of": 1, "step": 3})     # the hole names the detector's box a head
        self.assertEqual(round((out[t["added"][0]].y_canonical + out[t["added"][0]].height_canonical / 2.0 - TOP) / (SP / 2)), 5)

    def test_CONTROL_black_boxes_and_short_boxes_are_not_read(self):
        img = _staff()
        _half(img, 100, 260)
        _half(img, 100, 300)
        for d in (_D("noteheadBlackInSpace", 72, 236, 56, 88), _D("noteheadHalfInSpace", 72, 250, 56, 60)):
            out, info = BK.split_tall_heads([d], img, SP, TOP, LINES)
            self.assertEqual((len(out), info), (1, {}), d)

    def test_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(BK.TALL_ENV, None)
            self.assertFalse(BK.tall_split_enabled())
        for val, want in (("1", True), ("on", True), ("0", False), ("", False)):
            with mock.patch.dict(os.environ, {BK.TALL_ENV: val}):
                self.assertEqual(BK.tall_split_enabled(), want, val)


CELL = R.cell(2, 1, 1, 12)


def _log():
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, SP, reader=READERS.GEOMETRY, frame="cell:12")
    return log


def _box(log, gi, cls, box, pos, tall=None):
    g = R.glyph(2, 1, 1, 12, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:12", score=0.6)
    x, y, w, h = box
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:12", score=0.6,
                bbox_page_px=[2000 + x, 2000 + y, 2000 + x + w, 2000 + y + h], **({"tall_split": tall} if tall is not None else {}))
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos), reader=READERS.GEOMETRY, frame="cell:12")
    return g


class TestTheRemainder(unittest.TestCase):

    def _run(self, env, tall):
        log = _log()
        t = _box(log, 3, "noteheadHalfInSpace", (72, 236, 56, 88), 4.0, tall=tall)
        a = _box(log, 7, "noteheadHalfInSpace", (72, 234, 56, 52), 3.0, tall={"split_from": 3, "step": 3})
        b = _box(log, 8, "noteheadHalfInSpace", (72, 274, 56, 52), 5.0, tall={"split_from": 3, "step": 5})
        with mock.patch.dict(os.environ, env):
            adjudicate.run(log)
        return [log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, s) for s in (t, a, b)]

    def test_ON_a_read_tall_box_is_the_remainder_and_refused_RED(self):
        t, a, b = self._run(ON, {"read": True, "steps": [3, 5], "added": [7, 8], "covered": 0, "holes": 2})
        self.assertEqual((t.value, t.reason), (True, "taller_than_a_head"))
        self.assertNotEqual(a.reason, "taller_than_a_head")
        self.assertNotEqual(b.reason, "taller_than_a_head")

    def test_ON_a_box_not_read_or_not_accounted_is_not_refused_by_this_rule(self):
        for tall in ({"read": False, "holes": 1}, {"read": True, "steps": [3, 5], "added": [7], "covered": 0, "holes": 2}, None):
            t, _a, _b = self._run(ON, tall)
            self.assertNotEqual(t.reason, "taller_than_a_head", tall)

    def test_OFF_the_rule_does_not_speak(self):
        t, _a, _b = self._run(OFF, {"read": True, "steps": [3, 5], "added": [7, 8], "covered": 0, "holes": 2})
        self.assertNotEqual(t.reason, "taller_than_a_head")


if __name__ == "__main__":
    unittest.main()
