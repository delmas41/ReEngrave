"""The de-duplication's own control: the KNOWN_GAPS bookkeeping and the two
AST one-liners were defined once per check module; they are now one function
in `staged/check_helpers.py` behind thin same-named wrappers. Each wrapper must
agree with the helper (and the helper must be able to fail)."""
from __future__ import annotations

import ast
import unittest

from tools.omr.staged import (capture, check_helpers as H, gather_coverage,
                              inventory, trace, wiring)

MODULES = (capture, inventory, trace, wiring)


class GapBookkeeping(unittest.TestCase):
    def test_wrappers_agree_with_the_helper_on_their_own_table(self):
        for m in MODULES:
            keys = list(m.KNOWN_GAPS)
            self.assertTrue(keys, m.__name__)
            hit = [keys[0] + " tail", keys[-1]]
            probs = hit + ["brand new thing nobody listed"]
            with self.subTest(m.__name__):
                self.assertEqual(m._gap_key(probs[0]), H.gap_key(probs[0], keys))
                self.assertEqual(m._gap_key(probs[2]), None)
                self.assertEqual(m.unaccounted(probs), probs[2:])
                self.assertEqual(m.unaccounted(probs),
                                 H.unaccounted(probs, keys))
                self.assertEqual(sorted(m.stale_gaps(probs)),
                                 sorted(H.stale_gaps(probs, keys)))

    def test_stale_gaps_is_sorted_except_trace_which_keeps_table_order(self):
        keys = ["zeta", "alpha", "mid"]
        self.assertEqual(H.stale_gaps(["mid x"], keys), ["alpha", "zeta"])
        self.assertEqual(H.stale_gaps(["mid x"], keys, ordered=True),
                         ["zeta", "alpha"])
        self.assertEqual(trace.stale_gaps([]), list(trace.KNOWN_GAPS))
        for m in (capture, inventory, wiring):
            self.assertEqual(m.stale_gaps([]), sorted(m.KNOWN_GAPS))

    def test_the_helper_can_fail(self):
        # a problem on no entry is reported; an entry nothing reports is stale
        self.assertEqual(H.unaccounted(["x"], ["y"]), ["x"])
        self.assertEqual(H.stale_gaps([], ["y"]), ["y"])
        self.assertEqual(H.unaccounted(["y z"], ["y"]), [])
        self.assertEqual(H.stale_gaps(["y z"], ["y"]), [])

    def test_the_four_tables_report_each_other_differently(self):
        # same problem text, different tables: the wrappers must NOT share one
        k = next(iter(capture.KNOWN_GAPS))
        if not any(k.startswith(o) or o.startswith(k)
                   for o in inventory.KNOWN_GAPS):
            self.assertIsNone(inventory._gap_key(k))
            self.assertIsNotNone(capture._gap_key(k))


class AstOneLiners(unittest.TestCase):
    def test_same_answer_through_both_modules(self):
        def dotted(base, attr):
            return ast.Attribute(value=ast.Name(id=base), attr=attr)
        q = dotted("Q", "GLYPH_BOX")
        other = dotted("READERS", "DETECTOR")
        name = ast.Name(id="x")
        for node, want_q, want_tail in ((q, "GLYPH_BOX", "GLYPH_BOX"),
                                        (other, None, "DETECTOR"),
                                        (name, None, None)):
            self.assertEqual(capture._q_name(node), want_q)
            self.assertEqual(gather_coverage._q_name(node), want_q)
            self.assertEqual(capture._attr_tail(node), want_tail)
            self.assertEqual(gather_coverage._attr_tail(node), want_tail)


if __name__ == "__main__":
    unittest.main()
