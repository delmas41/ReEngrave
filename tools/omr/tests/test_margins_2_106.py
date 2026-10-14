"""ROADMAP 2.106 step 1 -- every threshold refusal says how close it came.

Bookkeeping, not a decision: a margin, an axis, a band and the would-be value
are filed on the verdict; nothing about outcome, value or reason moves. Tests
named `*_RED` fail on the unrepaired tree (no `margins` module, margin `None`).

Controls that can FAIL: `unmarked_sites` is run on a source in which one wrap
is removed (it must count exactly that one) and on the tree (it must count
zero); `audit` is handed margin-less verdicts (it must count them) and
margin-carrying ones (it must not).
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, margins as M
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged.record import Log, Outcome, Q

from tools.omr.tests import test_staged_notehead_precision as NP
from tools.omr.tests import test_staged_unboxed_rest_2_99 as UR
from tools.omr.tests import test_staged_narrow_rest_2_80b as NR


class TestSlack(unittest.TestCase):
    def test_signed_distance(self):
        self.assertAlmostEqual(M.slack(1.3, 1.1, 1.6), 0.2)       # inside
        self.assertAlmostEqual(M.slack(1.0, 1.1, 1.6), -0.1)      # under
        self.assertAlmostEqual(M.slack(2.0, 1.1, 1.6), -0.4)      # over
        self.assertIsNone(M.slack(None, 1.1, 1.6))                # unknown

    def test_attach_never_changes_the_answer(self):
        r = adjudicate.Ruling(value="eighth", reason="rest8th_shape",
                              used=("x",), detail={"a": 1})
        out = M.attach(r, margin=0.123456, axis="a", unit="u",
                       band={"a": (1, 2)}, would_choose=("eighth",))
        self.assertEqual((out.value, out.reason, out.used, out.candidates),
                         (r.value, r.reason, r.used, r.candidates))
        self.assertEqual(out.margin, 0.1235)
        self.assertEqual(out.detail["band"], {"a": [1.0, 2.0]})
        self.assertEqual(out.detail["a"], 1)

    def test_attach_does_not_replace_a_contests_margin(self):
        r = adjudicate.Ruling(value=1, reason="r", margin=7.0)
        self.assertEqual(M.attach(r, margin=0.1, axis="a", unit="u").margin,
                         7.0)


class TestUnboxedRest(unittest.TestCase):

    def test_a_decided_eighth_cleared_its_windows_RED(self):
        _l, v = UR._case(UR.EIGHTH)
        self.assertEqual(v.value, "eighth")
        self.assertGreater(v.margin, 0.0)
        self.assertEqual(v.detail["would_choose"], ["eighth"])
        self.assertIsNotNone(v.detail["margin_axis"])
        self.assertIn("width_spaces/eighth", v.detail["band"])

    def test_a_near_miss_abstains_with_a_small_negative_margin_RED(self):
        # width 1.05: 0.05 under the eighth window's 1.1 floor
        _l, near = UR._case(UR.EIGHTH, w=1.05)
        self.assertIs(near.outcome, Outcome.ABSTAINED)
        self.assertEqual(near.reason, "shape_cannot_tell")
        self.assertEqual(near.detail["margin_axis"], "width_spaces")
        self.assertAlmostEqual(near.margin, -0.05, places=3)
        self.assertEqual(near.detail["would_choose"], ["eighth"])
        # an ABSTAINED verdict carries no candidates (record invariant): the
        # would-be value lives in detail, not in a narrowing.
        self.assertEqual(near.candidates, ())

    def test_a_mile_miss_is_further_than_a_near_miss_POSITIVE_CONTROL(self):
        _l, near = UR._case(UR.EIGHTH, w=1.05)
        _l, far = UR._case(UR.EIGHTH, w=3.0)
        self.assertEqual(far.reason, "shape_cannot_tell")
        self.assertLess(far.margin, near.margin)

    def test_the_outcome_is_what_it_was_without_the_margin(self):
        for base, kw, value, reason in (
                (UR.EIGHTH, {}, "eighth", "rest8th_shape"),
                (UR.QUARTER, {}, "quarter", "restQuarter_shape"),
                (UR.FLAT, {}, False, "stem_stroke_not_a_rest"),
                (UR.EIGHTH, {"cover": 0.7}, False, "already_read_as_a_glyph"),
                (UR.EIGHTH, {"cover": 0.3}, None, "claimed_by_another_class"),
                (UR.EIGHTH, {"col": 0.3}, False, "thin_stroke_not_a_rest")):
            _l, v = UR._case(base, **kw)
            self.assertEqual((v.value, v.reason), (value, reason))
            self.assertIsNotNone(v.margin, reason)

    def test_coverage_margin_is_signed_from_the_cut(self):
        _l, read = UR._case(UR.EIGHTH, cover=0.7)
        self.assertAlmostEqual(read.margin, 0.2, places=3)       # cleared 0.5
        _l, mid = UR._case(UR.EIGHTH, cover=0.45)
        self.assertAlmostEqual(mid.margin, -0.05, places=3)      # 0.05 short
        self.assertEqual(mid.detail["would_choose"], [False])

    def test_a_cut_with_no_declared_band_says_so(self):
        _l, v = UR._case(UR.EIGHTH, col=0.3)
        self.assertEqual(v.reason, "thin_stroke_not_a_rest")
        self.assertIn("band", v.detail)
        self.assertIsNone(v.detail["band"])

    def test_structural_refusals_need_no_margin(self):
        _l, v = UR._case(UR.EIGHTH, left=True)
        self.assertEqual(v.reason, "in_the_header")
        self.assertIsNone(v.margin)
        self.assertEqual(
            M.COVERED["adjudicate_unboxed_ink_is_a_rest"]["in_the_header"]
            in (M.THRESHOLD,), False)


class TestNarrowRest(unittest.TestCase):

    def test_decided_and_refused_both_carry_a_margin_RED(self):
        _l, _g, yes = NR._case()
        self.assertIs(yes.value, True)
        self.assertGreater(yes.margin, 0.0)
        _l, _g, no = NR._case(w=0.3)               # decisively not a rest
        self.assertEqual(no.reason, "not_rest_shaped")
        self.assertGreater(no.margin, 0.0)         # refused by this much
        _l, _g, near = NR._case(w=0.8)             # between the two windows
        self.assertEqual(near.reason, "shape_cannot_tell")
        self.assertAlmostEqual(near.margin, -0.1, places=3)
        self.assertEqual(near.detail["margin_axis"], "width_spaces")
        self.assertEqual(near.detail["would_choose"], [True])


class TestTooNarrow(unittest.TestCase):

    def test_the_width_floor_margin_RED(self):
        log = Log()
        NP._cell_geometry(log)
        g = NP._notehead(log, 0, cls="noteheadBlackInSpace", w_c=80.0,
                         h_c=100.0, pos_float=4.0)
        v = NP._verdict(NP._run(log), g)
        self.assertEqual(v.reason, "too_narrow")
        self.assertAlmostEqual(v.margin, 0.2, places=3)     # 1.0 - 0.8
        self.assertEqual(v.detail["margin_axis"], "width_spaces")
        self.assertEqual(v.detail["would_choose"], [True])
        self.assertIsNone(v.detail["band"])


class TestHollowGate(unittest.TestCase):

    @staticmethod
    def _ink(raw=(0.4, 0.7), net=(0.4, 0.7), off=(0.4, 0.7)):
        mk = lambda c: {"windows": {"center": c[0], "ring": c[1]}}
        return {"ink_raw": mk(raw), "ink_net": mk(net), "ink_off_line": mk(off)}

    def test_a_firm_hollow_head_clears_the_gate(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        axis, m = RH._hollow_margin(self._ink())
        self.assertGreaterEqual(m, 0.0)

    def test_a_blank_centre_is_short_by_how_much(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        # centre 0.07: 0.13 under the 0.2 raw floor (Sean's tile 10)
        axis, m = RH._hollow_margin(self._ink(raw=(0.07, 0.6)))
        self.assertEqual(axis, "raw.center")
        self.assertAlmostEqual(m, -0.13, places=3)

    def test_a_thin_ring_gap_names_its_axis(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        axis, m = RH._hollow_margin(self._ink(raw=(0.4, 0.537)))
        self.assertEqual(axis, "raw.ring_gap")
        self.assertAlmostEqual(m, -0.013, places=3)

    def test_the_wrapper_keeps_the_ruling_whole(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        r = adjudicate.Ruling(value={"head_fill": "half"},
                              reason="hollow_head_bare_stem", used=("a",))
        out = RH._with_hollow_margin(r, self._ink())
        self.assertEqual((out.value, out.reason, out.used),
                         (r.value, r.reason, r.used))
        self.assertEqual(out.detail["would_choose"], ["half"])


class TestTheCheckPart(unittest.TestCase):

    def test_the_tree_has_no_unmarked_threshold_return(self):
        self.assertEqual(M.unmarked_sites(), [])

    def test_the_tree_has_no_unclassified_reason(self):
        problems, _notes = M.check_margins()
        self.assertEqual(problems, [])

    def test_removing_one_wrap_is_counted_RED(self):
        """The control can FAIL: strip ONE margin call and exactly that site
        is reported; the untouched source reports none."""
        text = M.decider_source("unboxed_rest")
        self.assertEqual(
            M.unmarked_sites({"unboxed_rest.py": text}), [])
        needle = ("        return _margin(\n"
                  "            Ruling(value=False, reason=\"thin_stroke_not_a_rest\",")
        self.assertIn(needle, text)
        broken = text.replace(
            needle, "        return (\n"
                    "            Ruling(value=False, reason=\"thin_stroke_not_a_rest\",", 1)
        got = M.unmarked_sites({"unboxed_rest.py": broken})
        self.assertEqual([(d, r) for d, r, _ in got],
                         [("adjudicate_unboxed_ink_is_a_rest",
                           "thin_stroke_not_a_rest")])

    def test_a_structural_return_is_not_counted(self):
        text = M.decider_source("unboxed_rest")
        self.assertIn('Ruling.abstain("in_the_header"', text)
        self.assertEqual(M.unmarked_sites({"unboxed_rest.py": text}), [])

    def test_every_pre_change_site_is_found_in_the_old_shape(self):
        """Run on the unwrapped spelling of every wrapped site: the count is
        the number of threshold returns, not zero."""
        text = M.decider_source("unboxed_rest")
        for w in ("return _margin(", "return _shape_refusal("):
            text = text.replace(w, "return _nomargin(")
        self.assertGreaterEqual(
            len(M.unmarked_sites({"unboxed_rest.py": text})), 8)

    def test_audit_counts_marginless_threshold_verdicts_RED(self):
        old = [{"decider": "adjudicate_unboxed_ink_is_a_rest",
                "reason": "shape_cannot_tell", "margin": None},
               {"decider": "adjudicate_unboxed_ink_is_a_rest",
                "reason": "in_the_header", "margin": None},       # structural
               {"decider": "adjudicate_clef", "reason": "x", "margin": None}]
        rep = M.audit(old)
        self.assertEqual(rep["threshold_verdicts"], 1)
        self.assertEqual(rep["without_margin"], 1)
        new = [dict(old[0], margin=-0.05)]
        self.assertEqual(M.audit(new)["without_margin"], 0)
        self.assertEqual(M.audit(new)["with_margin"], 1)

    def test_check_part_is_wired_into_the_roll_up(self):
        from tools.omr.staged import check
        names = [n for n, _ in check.CHECKS]
        self.assertIn("staged.margins", names)
        res = check._check_margins()
        self.assertEqual(res.open, 0)
        self.assertFalse(res.broken)


if __name__ == "__main__":
    unittest.main()
