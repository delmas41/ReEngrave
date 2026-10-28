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


if __name__ == "__main__":
    unittest.main()
