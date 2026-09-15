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


if __name__ == "__main__":
    unittest.main()
