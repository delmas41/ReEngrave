"""ROADMAP 2.264 (STAGED; flag `OMR_TIE_POSITION_EVERYWHERE`, default OFF) -- a tie is read from POSITION, not pitch, in
`_two_note_reading` and `adjudicate_tie_pair` too (page-facts s1, Sean 2026-11-03: *"Tiles 2,3 and 9 are clearly ties going from the
same note to the same note"*), the way the 2.260b binder reads it: each head's LOCAL staff position (`Q.NOTEHEAD_STAFF_POSITION`), never
a rounded step (two positions 0.49 and 0.51 round apart) nor two box centres (a box drawn tall moves its centre half a space).

Each "decides" test sits beside a control in the same geometry with the one fact changed (a position 1 sp away; a position inside the
empty interval between one position and two) so the flag cannot pass by turning every arc into a tie."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import ownership
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

H_W, H_H = 12.0, 10.0          # a staff space is 10 px, a half-step 5 px
TOP = 100.0
CELL_W = 200.0
ORDER = (Q.ARC_IS_NOT_AN_ARC, Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_OWNER, Q.ARC_KIND, Q.TIE_PAIR)
ON = {ownership.TIE_POSITION_ENV: "1"}
OFF = {ownership.TIE_POSITION_ENV: "0"}


def _cells(log, n):
    for m in range(n):
        log.observe(R.cell(0, 0, 0, m), Q.CELL_BOX, [m * CELL_W, 50.0, (m + 1) * CELL_W, 250.0],
                    reader=READERS.GEOMETRY, frame=f"cell:{m}")


def _head(log, cell, gi, x, pos, box_step=None):
    """A head whose staff position (half-steps from the top line) reads `pos` and whose BOX centre stands at `box_step` (default `pos`)."""
    g = R.glyph(0, 0, 0, cell, gi)
    yc = TOP + 5.0 * (pos if box_step is None else box_step)
    log.observe(g, Q.GLYPH_BOX, ("noteheadHalfInSpace", 0, 0, H_W, H_H), reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                category="notehead", bbox_page_px=[x, yc - H_H / 2, x + H_W, yc + H_H / 2])
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos), reader=READERS.GEOMETRY, frame=f"cell:{cell}", residual=0.0,
                rounded=int(round(pos)))
    return g


def _arc(log, cell, gi, x0, x1, cls):
    g = R.glyph(0, 0, 0, cell, gi)
    log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.8, x0=x0, x1=x1, y0=112.0, y1=118.0,
                bbox_page_px=[x0, 112.0, x1, 118.0])
    return g


def _run(pos_a, pos_b, cls, env, box_a=None, box_b=None):
    log = Log()
    _cells(log, 2)
    a = _head(log, 0, 0, 40.0, pos_a, box_a)
    b = _head(log, 0, 1, 120.0, pos_b, box_b)
    arc = _arc(log, 0, 5, 55.0, 115.0, cls)
    log.freeze()
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log, order=ORDER)
    return a, b, arc, log.verdict(Q.ARC_KIND, arc), log.verdict(Q.TIE_PAIR, arc)


def _tn(v):
    return v.detail["grammar"]["tie_slur_rule"]["two_note"]


class TestKindFromPosition(unittest.TestCase):
    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ownership.TIE_POSITION_ENV, None)
            self.assertFalse(ownership.tie_position_everywhere_enabled())

    def test_OFF_boxes_apart_steps_equal_is_a_conflict_and_the_slur_class_stands(self):
        # one position (4.0 and 4.0) but the second box drawn 0.5 sp low: the box test says "not one position"
        _a, _b, _arc_, v, _p = _run(4.0, 4.0, "slur", OFF, box_b=4.0 + 1.0)
        self.assertEqual(_tn(v)["relation"], "conflict")
        self.assertEqual(v.value, "slur")

    def test_ON_same_local_position_is_a_tie_whatever_the_boxes_say(self):
        _a, _b, _arc_, v, _p = _run(4.0, 4.0, "slur", ON, box_b=4.0 + 1.0)
        self.assertEqual(_tn(v)["relation"], "same")
        self.assertEqual(_tn(v)["local_dy_spaces"], 0.0)
        self.assertEqual((v.outcome, v.value), (Outcome.DECIDED, "tie"))

    def test_ON_two_positions_that_round_apart_are_one_position(self):
        # 3.6 and 3.4 round to steps 4 and 3 (conflict OFF); 0.1 sp apart locally
        _a, _b, _arc_, off, _p = _run(3.6, 3.4, "slur", OFF)
        self.assertEqual(_tn(off)["relation"], "conflict")
        _a, _b, _arc_, on, _p = _run(3.6, 3.4, "slur", ON)
        self.assertEqual(_tn(on)["relation"], "same")
        self.assertEqual(on.value, "tie")

    def test_CONTROL_ON_a_position_a_space_away_is_still_a_slur(self):
        _a, _b, _arc_, v, _p = _run(4.0, 6.0, "tie", ON)
        self.assertEqual(_tn(v)["relation"], "different")
        self.assertEqual(v.value, "slur")

    def test_CONTROL_ON_inside_the_empty_interval_changes_nothing(self):
        # 0.3 sp apart is neither one position (<= 0.25) nor two (>= 0.435): the relation is what OFF said
        _a, _b, _arc_, off, _p = _run(4.0, 4.6, "slur", OFF)
        _a, _b, _arc_, on, _p = _run(4.0, 4.6, "slur", ON)
        self.assertEqual(_tn(off)["relation"], _tn(on)["relation"])
        self.assertEqual(off.value, on.value)

    def test_CONTROL_ON_a_head_with_no_position_row_stays_unread(self):
        log = Log()
        _cells(log, 2)
        a = R.glyph(0, 0, 0, 0, 0)
        log.observe(a, Q.GLYPH_BOX, ("noteheadHalfInSpace", 0, 0, H_W, H_H), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    category="notehead", bbox_page_px=[40.0, TOP + 15.0, 52.0, TOP + 25.0])
        _head(log, 0, 1, 120.0, 4.0)
        arc = _arc(log, 0, 5, 55.0, 115.0, "tie")
        log.freeze()
        with mock.patch.dict(os.environ, ON):
            adjudicate.run(log, order=ORDER)
        v = log.verdict(Q.ARC_KIND, arc)
        self.assertNotEqual(_tn(v).get("relation"), "same")


class TestTiePairFromPosition(unittest.TestCase):
    def test_OFF_boxes_apart_no_pair_ON_the_pair_is_found(self):
        _a, _b, _arc_, _k, off = _run(4.0, 4.0, "tie", OFF, box_b=4.0 + 1.0)
        self.assertEqual(off.reason, "no_pair_at_one_position")
        a, b, _arc_, _k, on = _run(4.0, 4.0, "tie", ON, box_b=4.0 + 1.0)
        self.assertEqual(on.outcome, Outcome.DECIDED)
        self.assertEqual(on.value, {"start": a.to_key(), "stop": b.to_key()})

    def test_CONTROL_ON_two_positions_a_space_apart_pair_nothing(self):
        _a, _b, _arc_, _k, on = _run(4.0, 6.0, "tie", ON)
        self.assertNotEqual(on.reason, "paired")           # the kind rule has already made it a slur: `not_a_tie`
        self.assertNotEqual(on.outcome, Outcome.DECIDED)


if __name__ == "__main__":
    unittest.main()
