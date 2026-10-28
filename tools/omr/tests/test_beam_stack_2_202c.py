"""ROADMAP 2.202c: tip levels are STACKED from the tip (pure `beam_strokes`, constructed cells). A thick stroke 3 sp inward of the tip that
touches the stem (a head of the other voice) is not a level; a real second level stacked under the first is. Control: the filter off turns the RED."""
from __future__ import annotations

import unittest

from tools.omr.staged import beam_strokes as BS
from tools.omr.tests.test_beam_faults_2_202b import SP, TIP, sv, stems, tip


def beam(i, outer, thick=0.6):       # down stems: the beam hangs from the tip (outer edge nearest y=TIP+5)
    return sv(i, "horizontal", (251, outer - thick * SP, 480, thick * SP), 4.8, thick, (0, 1, 2), sag=0.03)


class TestStack(unittest.TestCase):
    def run_(self, extra, on=True):
        old = BS.STACK_FILTER
        BS.STACK_FILTER = on
        try:
            st = stems(touching={0: (3, 4), 1: (3, 4), 2: (3, 4)})
            return tip(st + [beam(3, TIP + 5)] + extra, 0)["beams"]
        finally:
            BS.STACK_FILTER = old

    def test_head_end_slab_is_not_a_level(self):
        blob = sv(4, "horizontal", (251, TIP - 3.7 * SP, 480, 1.0 * SP), 4.8, 1.0, (0, 1, 2), sag=0.03)
        self.assertEqual(len(self.run_([blob])), 1)

    def test_control_filter_off_counts_it(self):
        blob = sv(4, "horizontal", (251, TIP - 3.7 * SP, 480, 1.0 * SP), 4.8, 1.0, (0, 1, 2), sag=0.03)
        self.assertGreaterEqual(len(self.run_([blob], on=False)), 2)

    def test_stacked_second_level_counts(self):
        second = sv(4, "horizontal", (251, TIP - 0.75 * SP - 0.6 * SP + 5, 480, 0.6 * SP), 4.8, 0.6, (0, 1, 2), sag=0.03)
        self.assertEqual(len(self.run_([second])), 2)


class TestFreeEndHookAndLocalFused(unittest.TestCase):
    """2.202e. A hook whose far end touches another stroke is a slur's start, not a flag; a double slab whose second beam starts AT this stem
    (local 0.96 on the coarse profile) is two levels. Controls: the constant off / back at 1.0 turns the RED."""

    def hook(self, touches):
        return sv(3, "horizontal", (251, 810, 106, 25), 1.06, 0.25, touches, sag=0.0)

    def test_free_hook_is_a_hook_touching_another_stroke_is_not(self):
        st = stems(touching={0: (3,)})
        other = sv(4, "blob", (300, 820, 50, 19), 0.5, 0.09, (3,), sag=0.0)
        free = tip(st + [self.hook((0,))], 0)["hooks"]
        held = tip(st + [self.hook((0, 4)), other], 0)["hooks"]
        BS.FREE_END_HOOK = False
        try:
            off = tip(st + [self.hook((0, 4)), other], 0)["hooks"]
        finally:
            BS.FREE_END_HOOK = True
        self.assertEqual(held, [])
        self.assertEqual(off, free)          # control: with the rule off the touching hook reads like the free one
        self.assertEqual(free, [3])

    def test_local_cut_is_inside_the_measured_gap(self):
        self.assertGreater(BS.FUSED_LOCAL_MIN_SPACES, 0.66)
        self.assertLess(BS.FUSED_LOCAL_MIN_SPACES, 0.8 + 1e-9)


if __name__ == "__main__":
    unittest.main()
