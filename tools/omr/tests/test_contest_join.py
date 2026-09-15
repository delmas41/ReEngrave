"""The phantom-note contest join restates one constant — pin it to its source.

`benchmarks/omr-phantom-notes-2026-09/probe/contest_join.py` decides whether a
bar lies inside `adjudicate_glyph_owner`'s domain, and that domain is fixed by
`gather.CONTEST_IOU`.  The probe RESTATES the value instead of importing it,
because importing `tools.omr.staged.gather` drags in the detector and a cloud
container has no weights — so the two can drift, and a drift would silently
change which bars the probe calls UNREACHABLE.

⚠️ THE CONSTANT IS READ FROM THE SOURCE BY AST, not imported, for the same
reason the probe restates it.  `ast.literal_eval` on the assignment's value is
what makes this a check on the FILE rather than on a copy of the number written
here twice.

⚠️ A SECOND ASSERTION IS THE ONE WITH TEETH: the probe's claim about the domain
is `same smufl_name` AND `different staff` AND `iou >= CONTEST_IOU`.  A test
that only compared the float would pass while the gate itself moved, so the
three conditions are asserted against the source of the gather site too.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
GATHER = ROOT / "tools/omr/staged/gather.py"
PROBE = ROOT / "benchmarks/omr-phantom-notes-2026-09/probe/contest_join.py"


def _module_constant(path: pathlib.Path, name: str):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a module constant of {path.name}")


def _function_source(path: pathlib.Path, name: str) -> str:
    src = path.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node) or ""
    raise AssertionError(f"{name} is not a function of {path.name}")


class TestTheProbeAgreesWithTheGatherSite(unittest.TestCase):

    def test_the_restated_contest_iou_equals_gathers_own(self):
        self.assertEqual(_module_constant(PROBE, "CONTEST_IOU"),
                         _module_constant(GATHER, "CONTEST_IOU"))

    def test_the_gate_is_still_same_class_other_staff_and_iou(self):
        body = _function_source(GATHER, "gather_ownership_evidence")
        # The probe's UNREACHABLE verdict is sound only while ALL THREE hold.
        self.assertIn("gi.staff == gj.staff", body,
                      "the contest is no longer restricted to DIFFERENT staves")
        self.assertIn("di.smufl_name != dj.smufl_name", body,
                      "the contest no longer requires the SAME class -- the "
                      "probe's suffix column is now part of the domain")
        self.assertIn("_iou(bi, bj) < CONTEST_IOU", body,
                      "the contest no longer gates on CONTEST_IOU")

    def test_the_positive_control_can_fail(self):
        # Reading a constant that is not there must raise, or the first test
        # would pass vacuously on a renamed constant.
        with self.assertRaises(AssertionError):
            _module_constant(GATHER, "CONTEST_IOU_THAT_DOES_NOT_EXIST")
        with self.assertRaises(AssertionError):
            _function_source(GATHER, "a_function_that_does_not_exist")

    def test_the_reader_really_reads_the_file(self):
        """⚠️ FOUND BY A MUTATION ARM THAT SURVIVED.

        Replacing `_module_constant`'s body with `return 0.5` left the equality
        test GREEN -- both sides returned the stub, so the test agreed with
        itself and said nothing about either file.  A reader that returns one
        fixed number is caught by asking it for a constant whose value is NOT
        that number.
        """
        self.assertEqual(_module_constant(GATHER, "LEDGER_ROUND_UP"), 0.25)
        self.assertEqual(_module_constant(GATHER, "_CV_GLYPH_BASE"), 100000)
        self.assertEqual(_module_constant(GATHER, "FRAME_PAGE"), "page")


def _load_probe():
    spec = importlib.util.spec_from_file_location("_contest_join", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pair(a, b, klass_a, klass_b, iou=0.9, family="notehead_class"):
    return {"a": a, "b": b, "family": family,
            "scope": ("same_cell" if a.split("/")[1:5] == b.split("/")[1:5]
                      else "same_system_other_staff"),
            "class_a": klass_a, "class_b": klass_b,
            "same_class": klass_a == klass_b, "iou": iou}


class TestTheSplitTheJoinDependsOn(unittest.TestCase):
    """⚠️ FOUND BY A MUTATION ARM THAT SURVIVED on the real document.

    Dropping the probe's `same_class` gate moved 47 suffix-only pairs into the
    contest index and **changed no answer**, because not one of the eighteen
    print-silent bars carries a suffix-only pair.  That makes the arm an
    equivalent mutant *for this page* and a real hole *for the mechanism*, so
    the split is exercised directly instead.
    """

    def setUp(self):
        self.m = _load_probe()

    def test_a_suffix_only_pair_is_not_a_contest(self):
        pairs = [_pair("glyph/1/0/4/7/2", "glyph/1/0/5/7/9",
                       "noteheadBlackOnLine", "noteheadBlackInSpace")]
        cross, suffix, incell = self.m.index_pairs(pairs)
        self.assertEqual(cross, {})
        self.assertEqual(len(suffix[(1, 0, 4, 7)]), 1)
        self.assertEqual(len(suffix[(1, 0, 5, 7)]), 1)
        self.assertEqual(incell, {})

    def test_a_same_class_cross_staff_pair_IS_a_contest(self):
        # The positive control: without it every assertion above is satisfied
        # by an index_pairs that files nothing anywhere.
        pairs = [_pair("glyph/1/0/4/7/2", "glyph/1/0/5/7/9",
                       "noteheadBlackOnLine", "noteheadBlackOnLine")]
        cross, suffix, incell = self.m.index_pairs(pairs)
        self.assertEqual(len(cross[(1, 0, 4, 7)]), 1)
        self.assertEqual(len(cross[(1, 0, 5, 7)]), 1)
        self.assertEqual(suffix, {})

    def test_a_same_cell_pair_is_neither(self):
        pairs = [_pair("glyph/1/0/4/7/2", "glyph/1/0/4/7/9",
                       "noteheadBlackOnLine", "noteheadBlackOnLine")]
        cross, suffix, incell = self.m.index_pairs(pairs)
        self.assertEqual(cross, {})
        self.assertEqual(suffix, {})
        self.assertEqual(len(incell[(1, 0, 4, 7)]), 1)

    def test_head_base_strips_only_the_position_suffix(self):
        self.assertEqual(self.m.head_base("noteheadHalfInSpace"),
                         "noteheadHalf")
        self.assertEqual(self.m.head_base("noteheadHalfOnLine"),
                         "noteheadHalf")
        # ⚠️ A half and a black head are NOT the same ink, and folding them
        # would make the suffix column a claim about note VALUE.
        self.assertNotEqual(self.m.head_base("noteheadHalfOnLine"),
                            self.m.head_base("noteheadBlackOnLine"))


if __name__ == "__main__":
    unittest.main()
