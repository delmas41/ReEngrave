"""ROADMAP 2.313 -- a re-gather lane report loads the plate's OPENING page too (never counts it).

The real case: the frozen Litolff sample is pages 2,4,...,16 and prints its staff names, meter and key on page 1 only. A
`--from gather` run that gathered the sample pages alone read no names (Litolff p11 alone on today's main: 20 notes
`staff_not_identified`, 21 red bars all 'unread', 15 values refused; with page 1: 0, 31 red bars, 9 refused). The control
can fail: it drives the real `run_report` / `one_test.run` with the gather stubbed and fails if page 1 is not asked for.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from tools.omr.staged import lane_report as L
from tools.omr.staged import one_test as OT


class _Stop(Exception):
    pass


class TestGatherLoadsTheOpeningPage(unittest.TestCase):
    def setUp(self):
        self.sample = L.load_sample()
        self.asked = []
        self._orig = L.gather_one

        def fake(plate, arm, flag_env, pages, work, env0):
            self.asked.append((plate, list(pages)))
            raise _Stop()
        L.gather_one = fake

    def tearDown(self):
        L.gather_one = self._orig

    def test_the_real_sample_needs_page_one_for_litolff(self):
        pl = self.sample["plates"]["litolff"]
        self.assertNotIn(1, pl["pages"])            # the counted pages never include it ...
        self.assertIn(1, L.loaded_pages(self.sample, "litolff"))   # ... the gathered pages must

    def test_lane_report_gathers_the_context_page(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(_Stop):
                L.run_report([("OMR_X", "0", "1")], ["litolff"], "gather", pathlib.Path(d), "20261029-night", 2188, 1, self.sample, [])
        self.assertEqual(self.asked[0][0], "litolff")
        self.assertIn(1, self.asked[0][1])
        self.assertEqual([p for p in self.asked[0][1] if p != 1], self.sample["plates"]["litolff"]["pages"])

    def test_one_test_gathers_the_context_page(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(_Stop):
                OT.run([("OMR_X", "0", "1")], ["litolff"], "gather", pathlib.Path(d), "20261029-night", 2188, 1, self.sample, [])
        self.assertIn(1, self.asked[0][1])


if __name__ == "__main__":
    unittest.main()
