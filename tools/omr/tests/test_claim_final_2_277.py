"""ROADMAP 2.277 -- claimed ink is final (flag `OMR_CLAIM_FINAL`, default OFF). Pure measurement, the consult, the derived check. Every control can fail."""
from __future__ import annotations

import os
import pathlib
import types
import unittest
from unittest import mock

from tools.omr.staged import claim_final as CF
from tools.omr.staged.adjudicators import claim_final as ACF

# (ordinal, share of the stroke inside the box, stroke ink, owner state, owner family)
BARLINE_SLIVER = [(0, 1.0, 10.0, "decided", "barline")]
HEAD_BESIDE_BARLINE = [(0, 1.0, 40.0, "decided", "head"), (1, 0.3, 30.0, "decided", "barline")]      # 12 / 52 held
HEAD_ON_ARC = [(0, 0.9, 40.0, "decided", "arc_trace")]
CLAIMS = ["barline", "arc_trace", "word"]


class TestMeasure(unittest.TestCase):
    def test_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(CF.ENV, None)
            self.assertFalse(CF.enabled())
        with mock.patch.dict(os.environ, {CF.ENV: "1"}):
            self.assertTrue(CF.enabled())

    def test_a_barline_sliver_is_wholly_held(self):
        total, by = CF.held_share(BARLINE_SLIVER, "head", CLAIMS)
        self.assertEqual(CF.dominant(total, by)[:2], ("barline", 1.0))

    def test_CONTROL_a_head_beside_a_barline_is_held_by_a_small_share(self):
        total, by = CF.held_share(HEAD_BESIDE_BARLINE, "head", CLAIMS)
        f, share, _ = CF.dominant(total, by)
        self.assertEqual(f, "barline")
        self.assertLess(share, CF.CUT)

    def test_CONTROL_a_stroke_the_owner_did_not_decide_is_no_witness(self):
        total, by = CF.held_share([(0, 1.0, 10.0, "contested", "barline")], "head", CLAIMS)
        self.assertEqual(by, {})

    def test_the_boxes_own_family_never_holds_it(self):
        total, by = CF.held_share([(0, 1.0, 10.0, "decided", "head")], "head", ["head", "barline"])
        self.assertEqual(by, {})

    def test_held_boxes_records_the_near_miss_and_drops_the_rest(self):
        near = [(0, 1.0, 60.0, "decided", "head"), (1, 1.0, 40.0, "decided", "barline")]          # 0.4 held: a near miss
        boxes = [("a", "head", BARLINE_SLIVER), ("b", "head", HEAD_BESIDE_BARLINE), ("n", "head", near),
                 ("c", "head", [(0, 1.0, 90.0, "decided", "head"), (1, 1.0, 10.0, "decided", "barline")])]
        held = CF.held_boxes(boxes, CLAIMS)
        self.assertEqual(held["a"]["by"], "barline")
        self.assertEqual(held["n"]["share"], 0.4)
        self.assertNotIn("b", held)                    # 12 / 52 = 0.23, under NEAR_MIN
        self.assertNotIn("c", held)

    def test_marks_are_one_head_by_ink(self):
        m = CF.marks([["g/2", "g/1"], ["g/1", "g/3"], ["g/9"]])
        self.assertEqual(set(m), {"g/1", "g/2", "g/3"})
        self.assertEqual(len(set(m.values())), 1)
        self.assertEqual(CF.distinct_heads(["g/1", "g/2", "g/3", "g/9"], m), 2)

    def test_CONTROL_two_unrelated_heads_are_two_marks(self):
        self.assertEqual(CF.marks([["g/1"], ["g/2"]]), {})
        self.assertEqual(CF.distinct_heads(["g/1", "g/2"], {}), 2)

    def test_double_marks_found(self):
        m = CF.marks([["g/1", "g/2"]])
        self.assertEqual(len(CF.double_marks(m, ["g/1", "g/2"])), 1)
        self.assertEqual(CF.double_marks(m, ["g/1"]), [])

    def test_refusal_kinds_are_the_literals_and_a_later_layer_is_generic(self):
        self.assertEqual(CF.refusal_kind("barline"), "barline")
        self.assertEqual(CF.refusal_kind("tremolo"), "page_claim")


class TestSurvivors(unittest.TestCase):
    def test_a_kept_box_on_a_barline_is_found(self):
        got = CF.survivors([("a", "mark", BARLINE_SLIVER, False)], CLAIMS)
        self.assertEqual(got[0]["by"], "barline")

    def test_CONTROL_the_same_box_refused_is_not_found(self):
        self.assertEqual(CF.survivors([("a", "mark", BARLINE_SLIVER, True)], CLAIMS), [])

    def test_CONTROL_a_head_beside_a_barline_is_not_found(self):
        self.assertEqual(CF.survivors([("b", "head", HEAD_BESIDE_BARLINE, False)], CLAIMS), [])

    def test_CONTROL_arc_trace_is_mark_only_and_consulted_elsewhere_owners_are_left_to_the_consult(self):
        self.assertEqual(CF.survivors([("a", "head", HEAD_ON_ARC, False)], CLAIMS), [])
        self.assertEqual(CF.survivors([("a", "head", [(0, 1.0, 10.0, "decided", "word")], False)], CLAIMS), [])


class _Sub:
    def __init__(self, key):
        self.key = key

    def at(self, kind):
        return object()

    def to_key(self):
        return self.key


def _ev(held, owns=()):
    v = types.SimpleNamespace(id="vrd:1", detail={"claim_final": {"held": held}, "box_owns": list(owns)})
    return types.SimpleNamespace(subject=_Sub("glyph/1/0/0/0/5"), verdict=lambda q, subject=None: v)


class TestConsult(unittest.TestCase):
    ROW = types.SimpleNamespace(id="obs:1")

    def _find(self, held, owns=()):
        with mock.patch.dict(os.environ, {CF.ENV: "1"}):
            return ACF.finding(_ev(held, owns), self.ROW)

    def test_barline_held_box_is_refused_by_the_claim(self):
        f = self._find({"glyph/1/0/0/0/5": {"by": "barline", "share": 1.0, "strokes": [0]}})
        self.assertEqual((f.kind, f.by), ("barline", "barline"))

    def test_a_later_layer_is_consumed_with_no_code(self):
        f = self._find({"glyph/1/0/0/0/5": {"by": "tremolo", "share": 0.9, "strokes": [0]}})
        self.assertEqual(f.kind, "page_claim")

    def test_CONTROL_arc_and_hairpin_traces_only_mark(self):
        for by in ("arc_trace", "hairpin_trace"):
            self.assertIsNone(self._find({"glyph/1/0/0/0/5": {"by": by, "share": 0.9, "strokes": [0]}}))

    def test_CONTROL_the_owners_the_register_consult_judges_are_left_to_it(self):
        for by in sorted(CF.CONSULTED_ELSEWHERE):
            self.assertIsNone(self._find({"glyph/1/0/0/0/5": {"by": by, "share": 0.9, "strokes": [0]}}))

    def test_CONTROL_a_near_miss_below_the_cut_is_not_refused(self):
        self.assertIsNone(self._find({"glyph/1/0/0/0/5": {"by": "barline", "share": 0.4, "strokes": [0]}}))

    def test_CONTROL_a_box_that_owns_a_stroke_is_not_refused(self):
        self.assertIsNone(self._find({"glyph/1/0/0/0/5": {"by": "barline", "share": 0.9, "strokes": [0]}}, owns=["glyph/1/0/0/0/5"]))

    def test_CONTROL_flag_off_is_silent(self):
        with mock.patch.dict(os.environ, {CF.ENV: "0"}):
            self.assertIsNone(ACF.finding(_ev({"glyph/1/0/0/0/5": {"by": "barline", "share": 1.0, "strokes": [0]}}), self.ROW))


class TestStaticCheck(unittest.TestCase):
    STAGED = pathlib.Path(CF.__file__).resolve().parent

    def test_this_tree_closes_barline_and_keeps_arc_and_hairpin_as_marks(self):
        f = CF.static_wiring()
        self.assertFalse([x for x in f if x["claim"] == "barline"], f)
        self.assertEqual({x["claim"] for x in f}, {"arc_trace", "hairpin_trace"})

    def test_CONTROL_the_check_can_fail_a_tree_whose_readers_never_consult(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "staged"
            (root / "adjudicators").mkdir(parents=True)
            shutil.copy(self.STAGED / "stroke_owner.py", root)
            shutil.copy(self.STAGED / "adjudicators" / "claimed_by.py", root / "adjudicators")
            for rel in CF.CONSUMER_DECIDERS.values():
                text = (self.STAGED / rel).read_text().replace("_claim_final.finding(", "_nothing(")
                (root / rel).write_text(text)
            f = CF.static_wiring(root)
            self.assertIn("barline", {x["claim"] for x in f})
            self.assertEqual(len(f), 6)


if __name__ == "__main__":
    unittest.main()
