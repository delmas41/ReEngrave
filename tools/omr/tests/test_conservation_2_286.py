"""ROADMAP 2.286: note conservation. Fast tier: the invariant and its controls on the smallest fixture that exists
(`test_staged_export._one_staff_page`). The real-page run is `test_conservation_real_page_2_286.py` (slow)."""
import copy
import os
import unittest
from unittest import mock

from tools.omr.staged import conservation as CON
from tools.omr.staged import export as SX
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page

FOUR_FOUR = {"numerator": 4, "denominator": 4, "raw": "4/4"}
SHORT = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]       # 3 of 4: a bar that does not add up
FULL = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER), ("F4", QUARTER)]


def _report(notes, red="1"):
    with mock.patch.dict(os.environ, {"OMR_RED_BARS": red, "OMR_PARTIAL_BARS": "on"}):
        return SX.to_musicxml(_one_staff_page(notes=notes, meter=FOUR_FOUR))


class TestTheInvariantHolds(unittest.TestCase):
    def test_a_bar_that_adds_up(self):
        _x, rep = _report(FULL)
        self.assertEqual(CON.check(rep), [])
        c = rep["conservation"]
        self.assertEqual((c["read_by_adjudicate"], c["written"], c["not_written_total"]), (4, 4, 0))
        self.assertEqual(c["in_red_bars"]["rows"], 0)

    def test_a_red_bar_is_listed_by_bar_and_counted_written(self):
        _x, rep = _report(SHORT)
        c = rep["conservation"]
        self.assertEqual(CON.check(rep), [])
        self.assertEqual(c["in_red_bars"]["rows"], 3)
        self.assertEqual(c["written"], 3)
        (p,) = c["in_red_bars"]["places"]
        self.assertEqual((p["page"], p["system"], p["staff"], p["cell"], p["rows"]), (0, 0, 0, 0, 3))
        self.assertEqual(len(p["glyphs"]), 3)

    def test_a_held_bar_is_listed_by_bar_and_counted_not_written(self):
        _x, rep = _report(SHORT, red="0")
        c = rep["conservation"]
        self.assertEqual(CON.check(rep), [])
        self.assertEqual(c["in_held_bars"]["rows"], 3)
        self.assertEqual(c["not_written"], {"bar_does_not_add_up": 3})
        self.assertEqual(c["written"], 0)

    def test_the_report_changes_no_byte_of_the_file(self):
        a, _ = _report(SHORT)
        with mock.patch.object(SX, "_conservation_report", return_value={}):
            b, _ = _report(SHORT)
        self.assertEqual(a, b)


class TestControlsThatCanFail(unittest.TestCase):
    """CLAUDE rule 7: each is run where the invariant must fail."""

    def test_a_head_removed_without_a_reason_is_caught_by_the_export(self):
        original = SX._place_notes

        def swallow(rec, runs, by_system=None, held_out=None, **kw):
            original(rec, runs, by_system=by_system, held_out=held_out, **kw)
            for run in runs.values():
                run.cells.clear()
            return {}
        with mock.patch.object(SX, "_place_notes", swallow):
            with self.assertRaises(SX.Unbalanced):
                _report(FULL)

    def test_a_head_missing_from_the_report_is_caught_by_check(self):
        _x, rep = _report(FULL)
        bad = copy.deepcopy(rep)
        bad["conservation"]["written"] -= 1
        self.assertTrue(any("neither written nor counted" in m for m in CON.check(bad)))

    def test_an_unnamed_reason_is_caught(self):
        _x, rep = _report(FULL)
        bad = copy.deepcopy(rep)
        bad["conservation"]["not_written"] = {"": 1}
        bad["conservation"]["not_written_total"] = 1
        bad["conservation"]["written"] -= 1
        self.assertTrue(any("unnamed reason" in m for m in CON.check(bad)))

    def test_a_gap_bar_head_miscounted_as_written_is_caught(self):
        """Move a held bar's three heads from not-written to written: the totals still balance, so only the
        bar-vs-reason cross-check can see it."""
        _x, rep = _report(SHORT, red="0")
        bad = copy.deepcopy(rep)
        c = bad["conservation"]
        c["written"] += 3
        c["not_written"] = {}
        c["not_written_total"] = 0
        self.assertEqual(c["read_by_adjudicate"], c["written"] + c["not_written_total"])   # balanced on its face
        self.assertTrue(any("counted as written" in m for m in CON.check(bad)))

    def test_a_red_bar_head_that_cannot_be_located_is_caught(self):
        _x, rep = _report(SHORT)
        bad = copy.deepcopy(rep)
        bad["conservation"]["in_red_bars"]["places"] = []
        self.assertTrue(any("located by bar" in m for m in CON.check(bad)))


if __name__ == "__main__":
    unittest.main()
