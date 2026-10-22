"""`reach.py` must be able to FAIL, and must stay derived.

⚠️ Every assertion here exists because the tool's own first run got that
exact thing wrong. The accessor set was hand-written and missed two real
accessors, which produced two false positives.
"""
import unittest

from tools.omr.staged import reach
from tools.omr.staged.record import Q


class TestTheAccessorSetIsDerived(unittest.TestCase):
    def test_it_finds_both_kinds_of_accessor(self):
        read, write = reach._accessors()
        self.assertTrue(read, "no READ accessor derived — the question cannot run")
        self.assertTrue(write, "no WRITE accessor derived")

    def test_it_finds_the_two_that_the_hand_written_list_missed(self):
        read, _ = reach._accessors()
        self.assertIn("obs_of", read)   # export.Record — missed, false-positived CELL_BOX
        self.assertIn("state", read)    # Evidence    — missed, false-positived KEYSIG_RUN_POSITION

    def test_the_quantity_index_is_read_from_the_signature(self):
        """`observe(subject, quantity, ...)` — assuming index 0 reads the SUBJECT."""
        _, write = reach._accessors()
        self.assertEqual(write["observe"], 1)
        self.assertEqual(write["abstain"], 1)


class TestItCanFail(unittest.TestCase):
    def setUp(self):
        self.s = reach.survey()

    def test_the_positive_controls_are_not_zero(self):
        c = self.s["controls"]
        self.assertGreater(c["with_a_reader"], 0)
        self.assertGreater(c["quantity_stage_read_pairs"], 0)
        self.assertGreater(c["files_walked"], 0)

    def test_the_two_false_positives_are_LIVE(self):
        by_q = {r["quantity"]: r for r in self.s["rows"]}
        for q in (Q.CELL_BOX, Q.KEYSIG_RUN_POSITION):
            self.assertEqual(by_q[q]["state"], "LIVE",
                             f"{q} is read; reporting it otherwise is the "
                             f"hand-written-accessor bug returning")

    def test_the_gap_list_is_an_inventory_not_a_suppression(self):
        reported = {r["quantity"] for r in self.s["rows"] if r["state"] != "LIVE"}
        stale = sorted(set(reach.KNOWN_GAPS) - reported)
        self.assertEqual(stale, [], "a closed gap must LEAVE KNOWN_GAPS")

    def test_check_passes_on_this_tree(self):
        unaccounted = sorted(
            r["quantity"] for r in self.s["rows"]
            if r["state"] != "LIVE" and r["quantity"] not in reach.KNOWN_GAPS)
        self.assertEqual(unaccounted, [])

    def test_every_staged_module_is_accounted_as_a_stage_or_not(self):
        """`STAGE_OF_FILE` is a hand list; a new module must not be silent."""
        self.assertEqual(reach.unaccounted_modules(), [],
                         "a staged module is in neither STAGE_OF_FILE nor "
                         "NOT_A_STAGE — every quantity only it reads will "
                         "report as UNREAD")



if __name__ == "__main__":
    unittest.main()
