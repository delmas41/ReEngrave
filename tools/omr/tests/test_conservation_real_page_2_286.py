"""ROADMAP 2.286, SLOW: the conservation invariant on a REAL saved page (Litolff 984073 pages 1-2, the saved
20261029-night gather rows, ADJUDICATE..EXPORT replay, about 35 s). Names `library/` slices, so it is slow by rule."""
import pathlib
import unittest

import pytest

from tools.omr.staged import conservation as CON
from tools.omr.staged import lane_report as LR

pytestmark = pytest.mark.slow
SLICE = LR.slice_dir("litolff", CON.DEFAULT_TAG)


@unittest.skipUnless((SLICE / "observations.jsonl").exists(), "the lane-report slices are machine-local")
class TestRealPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = CON.export_pages(CON.load_pages("litolff", [1, 2], CON.DEFAULT_TAG))

    def test_every_read_head_and_rest_is_accounted_for(self):
        rep = self.out["report"]
        self.assertEqual(CON.check(rep), [])
        c = rep["conservation"]
        self.assertGreater(c["read_by_adjudicate"], 1000)          # a real page, not an empty one
        self.assertEqual(c["read_by_adjudicate"], c["written"] + c["not_written_total"])

    def test_red_bar_heads_are_located(self):
        c = self.out["report"]["conservation"]
        self.assertGreater(c["in_red_bars"]["rows"], 0)            # this page has red bars: the line is exercised
        self.assertTrue(c["located"])

    def test_every_reason_is_named(self):
        for reason in self.out["report"]["conservation"]["not_written"]:
            self.assertNotIn(reason.strip().lower(), CON.UNNAMED)

    def test_control_the_invariant_fails_on_this_page_when_a_head_is_lost_or_a_red_head_is_mislaid(self):
        import copy
        rep = self.out["report"]
        lost = copy.deepcopy(rep)
        lost["conservation"]["written"] -= 1                       # one head gone with no reason
        self.assertTrue(CON.check(lost))
        mislaid = copy.deepcopy(rep)
        mislaid["conservation"]["in_red_bars"]["places"].pop()     # a red-bar head that can no longer be found
        self.assertTrue(CON.check(mislaid))
