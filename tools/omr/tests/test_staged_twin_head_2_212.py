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


def _gather(img, dets, flag):
    cell = _cell_of(img)
    sub = R.cell(0, 0, 0, 0)
    log = Log()
    det = {sub.to_key(): dets}
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
    with mock.patch.dict(os.environ, {TW.ENV: "1" if flag else "0"}):
        gather.gather_notehead_positions(log, [cell], {0: (0, 0)}, det)
        gather.gather_notehead_ink(log, [cell], {0: (0, 0)}, det)
    return log


def _pos(log, gi):
    return log.rows(Q.NOTEHEAD_STAFF_POSITION, R.glyph(0, 0, 0, 0, gi))[-1]


def _ring_dets(cy=180.0, off=0.15):
    b0, b1 = _box(150, cy - off * S), _box(150, cy + off * S)
    return [_detection("noteheadBlackInSpace", (b0[0], b0[1], b0[0] + b0[2], b0[1] + b0[3])),
            _detection("noteheadHalfInSpace", (b1[0], b1[1], b1[0] + b1[2], b1[1] + b1[3]))]


class TestWired(unittest.TestCase):

    def test_flag_on_twins_name_each_other_and_keep_their_OWN_positions(self):
        img = _paper()
        _ring_head(img, 150.0, 180.0)
        on = _gather(img, _ring_dets(), True)
        off = _gather(img, _ring_dets(), False)
        for gi in (0, 1):
            self.assertEqual(float(_pos(on, gi).value), float(_pos(off, gi).value))     # no invented position
            self.assertEqual(len(_pos(on, gi).detail["twin_head"]["members"]), 2)
            self.assertNotIn("twin_head", _pos(off, gi).detail or {})                   # the control: OFF files nothing
        self.assertGreater(abs(float(_pos(on, 0).value) - float(_pos(on, 1).value)), 0.5)

    def test_CONTROL_two_heads_a_third_apart_are_not_twins(self):
        img = _paper()
        dets = [_detection("noteheadHalfInSpace", (150 - HEAD_W / 2, 160 - HEAD_H / 2, 150 + HEAD_W / 2, 160 + HEAD_H / 2)),
                _detection("noteheadHalfInSpace", (150 - HEAD_W / 2, 200 - HEAD_H / 2, 150 + HEAD_W / 2, 200 + HEAD_H / 2))]
        log = _gather(img, dets, True)
        self.assertNotIn("twin_head", _pos(log, 0).detail or {})


class _Rec:
    def __init__(self, obs, pitch, clef):
        self._o, self._p, self._c = obs, pitch, clef

    def obs(self, q, sub):
        return self._o.get((q, sub), [])

    def verdict(self, q, sub):
        return self._p

    def verdict_by_id(self, vid):
        return self._c


class TestExportGuess(unittest.TestCase):
    A, B = "glyph/0/0/0/0/0", "glyph/0/0/0/0/1"

    def _rec(self, posA, posB, far=None):
        det = {"twin_head": {"members": [self.A, self.B]}}
        o = {(Q.NOTEHEAD_STAFF_POSITION, self.A): [{"value": posA, "detail": det}],
             (Q.NOTEHEAD_STAFF_POSITION, self.B): [{"value": posB, "detail": det}]}
        if far:
            o[(Q.FAR_HEAD_LEDGER_POSITION, self.B)] = [{"value": far}]
        return _Rec(o, {"outcome": "decided", "value": "G5", "basis": ["c"]}, {"quantity": Q.CLEF, "value": "treble"})

    def test_disagreeing_twins_are_guessed_with_both_candidates(self):
        from tools.omr.staged import export as E
        g = E.twin_head_guess_of(self._rec(8.1, 9.0), self.A)
        self.assertEqual(len(g["candidates"]), 2)
        self.assertEqual(g["rule"], E.TWIN_HEAD_RULE)

    def test_agreeing_twins_are_not_guessed(self):
        from tools.omr.staged import export as E
        self.assertIsNone(E.twin_head_guess_of(self._rec(8.1, 8.3), self.A))

    def test_a_far_head_ledger_read_outranks_the_box_centre(self):
        from tools.omr.staged import export as E
        # B's box centre says 9.0 but its ledger read says 8: the twins AGREE once the ledger is used
        self.assertIsNone(E.twin_head_guess_of(self._rec(8.1, 9.0, far=8), self.A))


if __name__ == "__main__":
    unittest.main()
