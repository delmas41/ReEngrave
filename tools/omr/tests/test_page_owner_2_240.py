"""ROADMAP 2.240 step 2: one owner per page mark (never nearness) and arcs / hairpins page-wide. Synthetic geometry; every control can fail."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import page_marks as PM
from tools.omr.staged import page_owner as PO

SP = 10.0
# two staves of one system: staff 0 lines 100..140, staff 1 lines 220..260 (page px), one bar 0..1000
FRAMES = {
    "staff/0/0/0": [PO.StaffBar(0.0, 1000.0, (100.0, 110.0, 120.0, 130.0, 140.0), SP)],
    "staff/0/0/1": [PO.StaffBar(0.0, 1000.0, (220.0, 230.0, 240.0, 250.0, 260.0), SP)],
}
A, B = "staff/0/0/0", "staff/0/0/1"


class Rows:
    def __init__(self, obs=None, abs_=None):
        self.o, self.a = obs or {}, abs_ or {}

    def obs(self, q, key):
        return self.o.get((q, key), [])

    def abs(self, q, key):
        return self.a.get((q, key), [])


def _ledger(key, cand):
    return {("far_head_owner_ledger", key): [(-2, {"candidate": cand})]}


def _stem(key, way, tip, box):
    return {("head_stem_reach", key): [(way, {"%s_tip_y" % way: tip, "head_box_page": list(box)})]}


GAP_HEAD = (500, 175, 512, 185)           # centre y 180: 4 sp below A, 4 sp above B
M_A, M_B = "glyph/0/0/0/3/1", "glyph/0/0/1/3/2"


class Owner(unittest.TestCase):
    def test_inside_staff_decides_whatever_the_ledger_says(self):
        r = PO.mark_owner("head", [M_A], (500, 115, 512, 125), FRAMES, Rows(_ledger(M_A, B)))
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", A, "inside_staff"))

    def test_space_just_outside_is_inside(self):
        r = PO.mark_owner("head", [M_A], (500, 140, 512, 150), FRAMES, Rows())     # centre 0.5 sp below the bottom line
        self.assertEqual(r["owner"], A)

    def test_CONTROL_never_nearness_a_gap_head_with_no_witness_abstains(self):
        near_a = (500, 150, 512, 160)                                            # 1.5 sp below A, 6.5 above B: nearness would say A
        r = PO.mark_owner("head", [M_A, M_B], near_a, FRAMES, Rows())
        self.assertEqual((r["status"], r["reason"]), ("abstain", "owner_no_witness"))

    def test_ledger_names_the_owner_and_two_views_count_once(self):
        r = PO.mark_owner("head", [M_A, M_B], GAP_HEAD, FRAMES, Rows({**_ledger(M_A, B), **_ledger(M_B, B)}))
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", B, "ledger"))

    def test_ledger_over_stem_is_plain(self):
        rows = {**_ledger(M_A, B), **_stem(M_A, "up", 135.0, GAP_HEAD)}           # stem up into staff A's band
        r = PO.mark_owner("head", [M_A, M_B], GAP_HEAD, FRAMES, Rows(rows))
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", B, "ledger_over_stem"))
        self.assertEqual(set(r["candidates"]), {A, B})

    def test_views_disagree_is_guessed_with_both(self):
        r = PO.mark_owner("head", [M_A, M_B], GAP_HEAD, FRAMES, Rows({**_ledger(M_A, A), **_ledger(M_B, B)}))
        self.assertEqual(r["status"], "guessed")
        self.assertEqual(set(r["candidates"]), {A, B})

    def test_stem_alone_names_it(self):
        r = PO.mark_owner("head", [M_A], GAP_HEAD, FRAMES, Rows(_stem(M_A, "down", 225.0, GAP_HEAD)))
        self.assertEqual((r["owner"], r["reason"]), (B, "stem"))

    def test_ledger_read_but_naming_no_staff_abstains_no_rungs(self):
        rows = Rows(abs_={("far_head_owner_ledger", M_A): [("ledger_not_read", {"candidate": A, "unread": False})]})
        r = PO.mark_owner("head", [M_A], GAP_HEAD, FRAMES, rows)
        self.assertEqual(r["reason"], "owner_no_rungs")

    def test_a_dynamic_in_the_gap_follows_its_note(self):
        r = PO.mark_owner("dynamic", [M_A, M_B], GAP_HEAD, FRAMES, Rows())
        self.assertEqual(r["reason"], "owner_follows_its_note")


class Pieces(unittest.TestCase):
    H, W = 300, 200

    def _setup(self, fam):
        ink = np.zeros((self.H, self.W), bool)
        ink[148:153, 40:70] = True       # piece 1
        ink[148:153, 80:110] = True      # piece 2 (a gap between: two boxes share no ink)
        rect_a, rect_b = (0, 0, 200, 200), (0, 100, 200, 300)
        va = PM.seen_on_page(rect_a, ink[0:200, 0:200].astype(np.int16))
        vb = PM.seen_on_page(rect_b, ink[100:300, 0:200].astype(np.int16))
        mk = lambda key, cell, gi, pb, v: PM.BoxInk(key, cell, gi, fam, "x", pb, PM.box_pixels(v[0], v[1], pb, ink))
        p1 = mk("glyph/0/0/0/0/0", (0, 0, 0, 0), 0, (38.0, 146.0, 72.0, 155.0), va)
        p2 = mk("glyph/0/0/0/0/1", (0, 0, 0, 0), 1, (78.0, 146.0, 112.0, 155.0), va)
        whole = mk("glyph/0/0/1/0/0", (0, 0, 1, 0), 0, (36.0, 145.0, 114.0, 156.0), vb)
        return [p1, p2, whole]

    def test_two_pieces_inside_one_box_are_one_mark(self):
        bs = self._setup("beam")
        m = PM.link(bs, pieces=True)
        self.assertEqual(len({m.mark_of[b.key] for b in bs}), 1)

    def test_CONTROL_without_the_rule_cell_twice_refuses(self):
        bs = self._setup("beam")
        m = PM.link(bs, pieces=False)
        self.assertEqual(len({m.mark_of[b.key] for b in bs}), 2)

    def test_CONTROL_two_heads_inside_one_box_stay_two(self):
        bs = self._setup("head")
        m = PM.link(bs, pieces=True)
        self.assertEqual(len({m.mark_of[b.key] for b in bs}), 2)


def _arc(key, staff, ys, x0=100, x1=160, pieces=None):
    return {"key": key, "staff": staff, "system": "0/0", "pieces": pieces or [key], "trace": [[x, ys, ys + 2] for x in range(x0, x1)],
            "cells": [0], "anchors": [None, None], "x0": float(x0), "x1": float(x1), "cut_at_barline": False}


class Spans(unittest.TestCase):
    def test_same_trace_from_two_staves_is_one_arc(self):
        sp, _ = PO.arc_spans([_arc("glyph/0/0/0/0/1", A, 180), _arc("glyph/0/0/1/0/1", B, 180)], {}, [])
        self.assertEqual(len(sp), 1)
        self.assertEqual(sp[0]["staves_seen_from"], [A, B])

    def test_CONTROL_a_trace_one_space_away_is_another_arc(self):
        sp, _ = PO.arc_spans([_arc("glyph/0/0/0/0/1", A, 180), _arc("glyph/0/0/1/0/1", B, 190)], {}, [])
        self.assertEqual(len(sp), 2)

    def test_CONTROL_a_long_neighbour_trace_never_glues_two_arcs_of_one_staff(self):
        a1 = _arc("glyph/0/0/1/0/1", B, 180, 100, 160)
        a2 = _arc("glyph/0/0/1/1/1", B, 180, 170, 230)
        long_a = _arc("glyph/0/0/0/0/1", A, 180, 100, 230)
        sp, _ = PO.arc_spans([a1, a2, long_a], {}, [])
        self.assertEqual(len(sp), 2)

    def test_one_page_mark_joins(self):
        mk = {"glyph/0/0/0/0/1": 7, "glyph/0/0/1/0/1": 7}
        sp, _ = PO.arc_spans([_arc("glyph/0/0/0/0/1", A, 180), _arc("glyph/0/0/1/0/1", B, 195)], mk, [])
        self.assertEqual(len(sp), 1)
        self.assertEqual(sp[0]["joined_by"], ["one_page_mark"])

    def test_untraced_arc_box_is_a_witness_only(self):
        sp, left = PO.arc_spans([], {}, [(3, ["glyph/0/0/0/0/4"], [1, 2, 3, 4])])
        self.assertEqual((len(sp), len(left)), (0, 1))

    def test_hairpin_wedges_and_boxed_as(self):
        w = [{"key": "glyph/0/0/0/0/100000", "staff": A, "kind": "crescendo", "box": [100, 160, 200, 175]},
             {"key": "glyph/0/0/1/0/100000", "staff": B, "kind": "crescendo", "box": [102, 161, 199, 174]}]
        marks = [(1, "beam", [110, 162, 190, 172], ["glyph/0/0/0/2/3"]), (2, "hairpin", [500, 160, 560, 170], ["glyph/0/0/0/5/1"])]
        sp, left = PO.hairpin_spans(w, marks)
        self.assertEqual(len(sp), 1)
        self.assertEqual(sp[0]["boxed_as"], [[1, "beam"]])
        self.assertEqual([u["page_mark"] for u in left], [2])


class Flag(unittest.TestCase):
    def test_off_files_nothing(self):
        log = mock.MagicMock()
        with mock.patch.dict(os.environ, {"OMR_PAGE_MARKS": "1", "OMR_PAGE_OWNER": "0"}):
            self.assertIsNone(PO.gather_page_owners(log, SimpleNamespace(), [], {}, SimpleNamespace(boxes=[1])))
        log.observe.assert_not_called()
        log.abstain.assert_not_called()

    def test_needs_page_marks(self):
        with mock.patch.dict(os.environ, {"OMR_PAGE_MARKS": "0", "OMR_PAGE_OWNER": "1"}):
            self.assertFalse(PO.enabled())


if __name__ == "__main__":
    unittest.main()
