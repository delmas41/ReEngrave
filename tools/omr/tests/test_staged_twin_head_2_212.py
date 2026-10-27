"""ROADMAP 2.212 -- ONE PRINTED HEAD, ONE MEASUREMENT (flag `OMR_TWIN_HEAD_MERGE`, default OFF). PATH: STAGED GATHER.

The detector boxes one head twice; the position was read off each box's own centre and ADJUDICATE's keeper choice then
chose the written pitch. Layers (each with a control that can fail):
  A. `twin_head.twin_groups` -- which boxes are ONE head (a second / a third / a chain are not).
  B. `twin_head.group_centre` -- the one centre, from the hole of a hollow head or the ink of a filled one.
  C. `gather.gather_notehead_positions` / `gather_notehead_ink` wired: flag ON shares one position and one fill window,
     flag OFF is the box's own reading (the control), a head the ink cannot place keeps each box's own position.
NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""
from __future__ import annotations
import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged import twin_head as TW
from tools.omr.staged.record import Log, Q
from tools.omr.tests.test_staged_head_line_cut_2_73 import (
    HEAD_H, HEAD_W, LINES, S, _cell_of, _detection, _paper, _ring_head)


def _box(cx, cy, w=HEAD_W, h=HEAD_H):
    return (cx - w / 2.0, cy - h / 2.0, w, h)


class TestTwinGroups(unittest.TestCase):

    def test_two_boxes_a_third_of_a_space_apart_are_one_head(self):
        self.assertEqual(TW.twin_groups([_box(150, 150), _box(150, 150 + 0.3 * S)], S), [[0, 1]])

    def test_CONTROL_a_third_a_whole_space_apart_is_two_heads(self):
        self.assertEqual(TW.twin_groups([_box(150, 150), _box(150, 150 + 1.0 * S)], S), [])

    def test_CONTROL_a_second_on_the_other_side_of_the_stem_is_two_heads(self):
        """Half a space apart but a head width sideways: opposite sides of one stem."""
        self.assertEqual(TW.twin_groups([_box(150, 150), _box(150 + HEAD_W, 150 + 0.5 * S)], S), [])

    def test_CONTROL_a_chain_that_walks_off_the_head_is_dropped_whole(self):
        chain = [_box(150, 150), _box(150, 150 + 0.4 * S), _box(150, 150 + 0.8 * S)]
        self.assertEqual(TW.twin_groups(chain, S), [])

    def test_a_lone_box_and_no_spacing_give_no_group(self):
        self.assertEqual(TW.twin_groups([_box(150, 150)], S), [])
        self.assertEqual(TW.twin_groups([_box(150, 150), _box(150, 151)], 0.0), [])


class TestGroupCentre(unittest.TestCase):

    def test_a_hollow_head_is_placed_by_its_hole_whichever_way_the_boxes_sit(self):
        img = _paper()
        _ring_head(img, 150.0, 170.0)
        for off in (-0.3, 0.0, 0.3):
            boxes = [_box(150, 170 + off * S), _box(150, 170 + (off + 0.25) * S)]
            r = TW.group_centre(img, boxes, S)
            self.assertIsNone(r["reason"])
            self.assertEqual(r["by"], "hole")
            self.assertAlmostEqual(r["cy"], 170.0, delta=0.08 * S)

    def test_a_black_cap_over_the_ring_does_not_pull_the_hole(self):
        """The Litolff p8 head: a black mark touching the ring's top. The ink centroid is pulled; the hole is not."""
        img = _paper()
        _ring_head(img, 150.0, 170.0)
        img[int(170 - 0.9 * S):int(170 - 0.5 * S), 125:170] = 0
        r = TW.group_centre(img, [_box(150, 165), _box(150, 175)], S)
        self.assertEqual(r["by"], "hole")
        self.assertAlmostEqual(r["cy"], 170.0, delta=0.1 * S)

    def test_a_filled_head_is_placed_by_its_ink(self):
        img = _paper()
        _ring_head(img, 150.0, 170.0, ink_fill=True)
        r = TW.group_centre(img, [_box(150, 160), _box(150, 175)], S)
        self.assertIsNone(r["reason"])
        self.assertEqual(r["by"], "ink")
        self.assertAlmostEqual(r["cy"], 170.0, delta=0.1 * S)

    def test_CONTROL_blank_paper_places_nothing(self):
        r = TW.group_centre(_paper(), [_box(150, 160), _box(150, 175)], S)
        self.assertIsNotNone(r["reason"])
        self.assertNotIn("cy", r)


def _gather(img, dets, flag):
    cell = _cell_of(img)
    sub = R.cell(0, 0, 0, 0)
    log = Log()
    det = {sub.to_key(): dets}
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
    with mock.patch.dict(os.environ, {TW.ENV: "1" if flag else "0"}):
        gather.gather_notehead_positions(log, [cell], {0: (0, 0)}, det, pws=pws)
        gather.gather_notehead_ink(log, [cell], {0: (0, 0)}, det, pws=pws)
    return log


def _pos(log, gi):
    return log.rows(Q.NOTEHEAD_STAFF_POSITION, R.glyph(0, 0, 0, 0, gi))[-1]


def _ring_dets(cy=180.0, off=0.15):
    b0, b1 = _box(150, cy - off * S), _box(150, cy + off * S)
    return [_detection("noteheadBlackInSpace", (b0[0], b0[1], b0[0] + b0[2], b0[1] + b0[3])),
            _detection("noteheadHalfInSpace", (b1[0], b1[1], b1[0] + b1[2], b1[1] + b1[3]))]


class TestWired(unittest.TestCase):

    def test_flag_on_the_two_boxes_share_one_position_read_off_the_head(self):
        img = _paper()
        _ring_head(img, 150.0, 180.0)
        log = _gather(img, _ring_dets(), True)
        p0, p1 = _pos(log, 0), _pos(log, 1)
        self.assertAlmostEqual(float(p0.value), float(p1.value), places=9)
        self.assertAlmostEqual(float(p0.value), (180.0 - LINES[0]) / (S / 2.0), delta=0.2)
        self.assertEqual(p0.detail["twin_head"]["by"], "hole")
        self.assertEqual(sorted(p0.detail["twin_head"]["classes"]), ["noteheadBlackInSpace", "noteheadHalfInSpace"])
        self.assertIn("detector_position_float", p0.detail)

    def test_CONTROL_flag_off_each_box_keeps_its_own_centre(self):
        img = _paper()
        _ring_head(img, 150.0, 180.0)
        log = _gather(img, _ring_dets(), False)
        p0, p1 = _pos(log, 0), _pos(log, 1)
        self.assertGreater(abs(float(p0.value) - float(p1.value)), 0.5)
        self.assertNotIn("twin_head", p0.detail or {})

    def test_the_twins_read_the_head_fill_in_one_window(self):
        img = _paper()
        _ring_head(img, 150.0, 180.0)
        on = _gather(img, _ring_dets(), True)
        i0 = on.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1]
        i1 = on.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 1))[-1]
        self.assertEqual(i0.detail["ink_raw"], i1.detail["ink_raw"])
        self.assertEqual(i0.detail["box_source"].split(":")[0], "twin_head")
        off = _gather(img, _ring_dets(), False)
        j0 = off.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1]
        j1 = off.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 1))[-1]
        self.assertNotEqual(j0.detail["ink_raw"], j1.detail["ink_raw"])     # the control: apart, they read different windows

    def test_CONTROL_a_head_the_ink_cannot_place_keeps_each_boxes_own_position(self):
        log = _gather(_paper(), _ring_dets(), True)
        p0, p1 = _pos(log, 0), _pos(log, 1)
        self.assertNotIn("twin_head", p0.detail or {})
        self.assertIn("twin_head_declined", p0.detail)
        self.assertGreater(abs(float(p0.value) - float(p1.value)), 0.5)

    def test_CONTROL_two_heads_a_third_apart_are_not_merged(self):
        img = _paper()
        _ring_head(img, 150.0, 160.0)
        _ring_head(img, 150.0, 200.0)
        dets = [_detection("noteheadHalfInSpace", (150 - HEAD_W / 2, 160 - HEAD_H / 2, 150 + HEAD_W / 2, 160 + HEAD_H / 2)),
                _detection("noteheadHalfInSpace", (150 - HEAD_W / 2, 200 - HEAD_H / 2, 150 + HEAD_W / 2, 200 + HEAD_H / 2))]
        log = _gather(img, dets, True)
        self.assertNotIn("twin_head", _pos(log, 0).detail or {})
        self.assertNotIn("twin_head", _pos(log, 1).detail or {})


if __name__ == "__main__":
    unittest.main()
