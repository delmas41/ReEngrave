"""ROADMAP 2.202b: the two tip faults of 2.202's beam reading, on constructed cells (pure `beam_strokes`; no record, no gather).

  * a FUSED DOUBLE beam (one slab >= 1.0 sp thick at the tip: beam 0.5 + gap 0.25 + beam 0.5 sp = 1.25) is two levels;
  * a beam that ends within 0.5 sp of the stem stroke (a hair short of it) joins it.
Every RED has a twin that must NOT fire, and each control breaks the one constant and shows the RED turn."""
from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import beam_strokes as BS

SP = 100.0
STEM_X = (244, 400, 563)
STEM_TOP, TIP = 383, 820          # down stems; the tip (outer end of the beam) is y 820


def sv(i, kind, box, length, thick, touches=(), angle=0.0, sag=0.03, profile=()):
    return BS.StrokeView(i, kind, tuple(float(v) for v in box), length, thick, sag, angle, tuple((j, 1.0) for j in touches), SP, "", tuple(profile))


def stems(n=3, touching=None):
    t = touching or {}
    return [sv(i, "vertical", (STEM_X[i], STEM_TOP, 31, TIP - STEM_TOP), 4.37, 0.3, t.get(i, ()), angle=90.0, sag=0.0) for i in range(n)]


def tip(strokes, stem=0):
    role = BS.roles(strokes)
    return BS.tip_reading(strokes, role, strokes[stem], "down")


class TestFusedDouble(unittest.TestCase):

    def slab(self, thick, outer=825, kind="horizontal", x=251, w=480):
        return sv(3, kind, (x, outer - thick * SP, w, thick * SP), w / SP, thick, (0, 1, 2), sag=0.03 if kind == "horizontal" else 0.4)

    def case(self, slab):
        st = stems(touching={0: (3,), 1: (3,), 2: (3,)})
        return tip(st + [slab], 0)

    def test_one_slab_of_1_25_sp_at_the_tip_is_two_levels_RED(self):
        t = self.case(self.slab(1.25))
        self.assertEqual(len(t["beams"]), 2)
        self.assertEqual(t["fused"], [3])

    def test_twin_a_single_beam_is_one_level(self):
        for thick in (0.5, 0.63, 0.8, 0.95):
            t = self.case(self.slab(thick))
            self.assertEqual(len(t["beams"]), 1, thick)
            self.assertEqual(t["fused"], [])

    def test_twin_a_thick_blob_far_from_the_tip_is_not_doubled(self):
        # the same 1.25 sp slab 3 sp INWARD of the tip is a head cluster (2.202 cause 2): still counted as before (one level), never two
        t = self.case(self.slab(1.25, outer=TIP - 300 + 25))
        self.assertEqual(len(t["beams"]), 1)
        self.assertEqual(t["fused"], [])

    def test_twin_a_slab_double_only_along_its_second_half_doubles_only_the_stems_there(self):
        # 12 profile samples in sixteenths: 0.6 sp over the first half, 1.3 sp over the second (the secondary beam covers the right-hand stems only)
        prof = (10,) * 6 + (21,) * 6
        slab = sv(3, "horizontal", (251, 700, 480, 125), 4.8, 1.25, (0, 1, 2), profile=prof)
        st = stems(touching={0: (3,), 1: (3,), 2: (3,)}) + [slab]
        self.assertEqual(len(tip(st, 0)["beams"]), 1)           # stem 0 stands at x 244..275: the single-beam stretch
        self.assertEqual(len(tip(st, 2)["beams"]), 2)           # stem 2 at x 563..594: the double stretch

    def test_twin_a_short_bump_in_a_single_beam_is_a_head_merged_with_it_not_a_slab(self):
        prof = (8, 11, 12, 13, 21, 21, 14, 12, 11, 10, 9, 8)          # median 0.7 sp, a 1.3 sp bump mid-stroke (Litolff p6: 16 such heads)
        slab = sv(3, "horizontal", (251, 700, 480, 125), 4.8, 0.7, (0, 1, 2), profile=prof)
        st = stems(touching={0: (3,), 1: (3,), 2: (3,)}) + [slab]
        self.assertEqual([len(tip(st, i)["beams"]) for i in (0, 1, 2)], [1, 1, 1])

    def test_twin_three_levels_fused_is_left_alone_not_called_two(self):
        t = self.case(self.slab(2.0))
        self.assertEqual(len(t["beams"]), 1)

    def test_twin_a_thick_curve_is_a_slur_and_no_beam_at_all(self):
        t = self.case(self.slab(1.25, kind="curve"))
        self.assertEqual(t["beams"], [])


class TestControlFusedCanFail(unittest.TestCase):
    def test_with_the_fused_rule_removed_the_same_slab_is_one_level(self):
        st = stems(touching={0: (3,), 1: (3,), 2: (3,)}) + [sv(3, "horizontal", (251, 700, 480, 125), 4.8, 1.25, (0, 1, 2))]
        self.assertEqual(len(tip(st, 0)["beams"]), 2)
        with mock.patch.object(BS, "FUSED_DOUBLE_MIN_THICKNESS_SPACES", 99.0):
            self.assertEqual(len(tip(st, 0)["beams"]), 1)


class TestBeamJoin(unittest.TestCase):

    def beam(self, x0, x1=640, y=757, h=63):
        return sv(3, "horizontal", (x0, y, x1 - x0, h), (x1 - x0) / SP, h / SP, (1, 2))

    def case(self, beam):
        st = stems(touching={1: (3,), 2: (3,)})          # the beam touches stems 1 and 2 only
        return tip(st + [beam], 0)

    def test_a_beam_that_stops_0_3_sp_short_of_the_stem_joins_it_RED(self):
        t = self.case(self.beam(275 + 30))
        self.assertEqual(len(t["beams"]), 1)
        self.assertEqual(t["joined"], [3])

    def test_twin_a_beam_0_8_sp_away_does_not(self):
        t = self.case(self.beam(275 + 80))
        self.assertEqual(t["beams"], [])
        self.assertEqual(t["joined"], [])

    def test_twin_the_edge_is_the_cut_0_5_joins_0_6_does_not(self):
        self.assertEqual(len(self.case(self.beam(275 + 50))["beams"]), 1)
        self.assertEqual(len(self.case(self.beam(275 + 60))["beams"]), 0)

    def test_twin_a_beam_level_with_the_stem_but_outside_the_tip_window_does_not(self):
        t = self.case(self.beam(275 + 30, y=390))              # 4.3 sp inward of the tip (the window ends 3.3): not this stem's level
        self.assertEqual(t["beams"], [])

    def test_twin_a_stub_touching_one_stem_is_still_no_beam_so_nothing_joins(self):
        st = stems(touching={1: (3,)})
        stub = sv(3, "horizontal", (305, 757, 95, 63), 0.95, 0.63, (1,))
        self.assertEqual(tip(st + [stub], 0)["beams"], [])

    def test_twin_a_stem_that_already_has_a_level_gets_no_second_one_from_a_near_stroke(self):
        st = stems(touching={0: (3,), 1: (3,), 2: (3, 4)}) + [sv(3, "horizontal", (251, 757, 120, 63), 1.2, 0.63, (0, 1)),
                                                              sv(4, "horizontal", (305, 690, 335, 63), 3.35, 0.63, (1, 2))]
        t = tip(st, 0)
        self.assertEqual((len(t["beams"]), t["joined"]), (1, []))        # level 1 touches the stem; the stroke 0.3 sp short is not added as level 2

    def test_twin_a_slab_thicker_than_one_beam_near_the_stem_is_a_head_cluster_not_a_join(self):
        self.assertEqual(self.case(self.beam(275 + 30, y=715, h=105))["beams"], [])     # 1.05 sp thick, 0.3 sp short of the stem

    def test_twin_a_stroke_whose_outer_edge_is_not_at_the_tip_is_not_the_first_level(self):
        self.assertEqual(self.case(self.beam(275 + 30, y=640, h=63))["beams"], [])      # outer edge 1.2 sp inward of the tip

    def test_the_stem_a_beam_already_touches_is_unchanged(self):
        st = stems(touching={0: (3,), 1: (3,), 2: (3,)})
        t = tip(st + [sv(3, "horizontal", (251, 757, 480, 63), 4.8, 0.63, (0, 1, 2))], 0)
        self.assertEqual((len(t["beams"]), t["joined"]), (1, []))


class TestControlJoinCanFail(unittest.TestCase):
    def test_with_the_join_gap_at_zero_the_same_cell_is_not_joined(self):
        st = stems(touching={1: (3,), 2: (3,)}) + [sv(3, "horizontal", (305, 757, 335, 63), 3.35, 0.63, (1, 2))]
        self.assertEqual(len(tip(st, 0)["beams"]), 1)
        with mock.patch.object(BS, "JOIN_MAX_GAP_SPACES", 0.0):
            self.assertEqual(tip(st, 0)["beams"], [])


if __name__ == "__main__":
    unittest.main()
