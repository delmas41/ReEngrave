"""Tests for `staged/meaning.py` — the measurement-meaning check.

⚠️ Every test here pins either a POSITIVE CONTROL or one of the two traps
this module's own first runs fell into. A structural check compared against
structure passes vacuously with alarming ease, so the emphasis is on
*can this question fail at all*.
"""
from __future__ import annotations

import ast
import pathlib
import unittest

from tools.omr.staged import meaning


class TestTheDerivationRan(unittest.TestCase):
    """The positive controls. A zero in any of these makes the rest vacuous."""

    @classmethod
    def setUpClass(cls):
        cls.s = meaning.survey()

    def test_it_walks_the_tree(self):
        self.assertGreater(self.s["files_walked"], 10)

    def test_it_finds_writers_and_readers(self):
        self.assertGreater(self.s["n_written"], 30)
        self.assertGreater(self.s["n_read"], 30)

    def test_the_registry_is_populated(self):
        """⚠️ THE TRAP THIS MODULE'S FIRST RUN FELL INTO.

        `adjudicate.REGISTRY` is filled by the `@decision` decorator, which
        runs only when the `adjudicators` package is imported. Imported bare
        it is EMPTY, and section 3 then iterates nothing and prints a
        confident `0` that reads exactly like "no decision pools across
        frames".
        """
        self.assertGreater(self.s["n_decisions"], 20)

    def test_section_three_is_not_empty(self):
        """If the registry import ever regresses, this is what goes red."""
        self.assertTrue(self.s["scope_vs_frame"],
                        "section 3 is empty; either the registry did not "
                        "populate or FRAME_EXTENT stopped placing frames")


class TestTheUpdateSpellingIsResolved(unittest.TestCase):
    """⚠️ THE SECOND TRAP, and the one that reported the question CLEAN.

    `capture.py` documents `**common` bound to `dict(...)`. The dominant
    spelling in `gather.py` is `box_detail.update(k=v)` then `**box_detail`,
    and resolving only `dict(...)` yields 12 unit-declaring keys and ZERO
    frame disagreements — a green answer produced by not asking.
    """

    @classmethod
    def setUpClass(cls):
        cls.s = meaning.survey()

    def test_it_finds_far_more_than_the_dict_only_spelling(self):
        self.assertGreater(
            self.s["n_unit_keys"], 30,
            "only ~12 unit-declaring keys are reachable through `dict(...)` "
            "alone; a low number here means the `.update()` half regressed")

    def test_the_mixed_detail_population_is_not_empty(self):
        self.assertTrue(
            self.s["mixed_detail"],
            "zero frame disagreements is what the dict-only resolver "
            "reported; it is not the truth")

    def test_glyph_box_is_among_them(self):
        """The canonical case: filed at `cell:*`, carries page pixels."""
        qs = {q for q, *_ in self.s["mixed_detail"]}
        self.assertIn("glyph_box", qs)

    def test_update_is_actually_collected(self):
        src = "\n".join([
            "def f(log, sub):",
            "    d = dict(reader=R, frame=frame_cell(1))",
            "    d.update(bbox_page_px=[0, 0, 1, 1])",
            "    log.observe(sub, Q.X, v, **d)",
        ])
        tree = ast.parse(src)
        got = meaning._dict_kwargs(tree)
        self.assertIn("bbox_page_px", got["d"])
        self.assertIn("frame", got["d"])


class TestEveryFrameIsPlaced(unittest.TestCase):
    """A frame token the check cannot place is one it cannot reason about."""

    def test_no_unresolved_frame_tokens(self):
        s = meaning.survey()
        self.assertEqual(
            s["unknown_frames"], [],
            "an unplaced or unresolved frame token: add it to FRAME_EXTENT "
            "or fix the site. ⚠️ `frame = frame_cell(...)` then "
            "`frame=frame` needs `_local_frames`; without it THIRTEEN "
            "quantities read as unresolved.")

    def test_local_frame_variable_resolves(self):
        src = "\n".join([
            "def f(log, sub, c):",
            "    frame = frame_cell(c.measure_index)",
            "    log.observe(sub, Q.X, v, reader=R, frame=frame)",
        ])
        fn = ast.parse(src).body[0]
        self.assertEqual(meaning._local_frames(fn).get("frame"), "cell:*")


class TestTheCalibrationPoint(unittest.TestCase):
    """`onset_column` is the repaired case and must stay visible as exempt."""

    @classmethod
    def setUpClass(cls):
        cls.s = meaning.survey()

    def test_onset_column_is_flagged(self):
        rows = [r for r in self.s["scope_vs_frame"]
                if r[0] == "onset_column" and r[2] == "glyph_box"]
        self.assertTrue(rows, "onset_column/glyph_box left section 3; the "
                              "check's only calibration point is gone")

    def test_onset_column_is_the_exempt_one(self):
        """It reads a page-frame key; that is what makes it safe."""
        rows = [r for r in self.s["scope_vs_frame"]
                if r[0] == "onset_column" and r[2] == "glyph_box"]
        self.assertTrue(rows[0][5],
                        "onset_column no longer reads a page-frame key — "
                        "either the repair was reverted or PAGE_FRAME_KEYS "
                        "stopped matching it")

    def test_it_is_the_only_exempt_row(self):
        """⚠️ If this ever fails it is INFORMATION, not necessarily a fault:
        another decision started reading a page-frame key. Update the
        expectation deliberately."""
        exempt = [r for r in self.s["scope_vs_frame"] if r[5]]
        self.assertEqual([r[0] for r in exempt], ["onset_column"])


class TestItCanFail(unittest.TestCase):
    """A check that cannot fail is not a check."""

    def test_an_unplaced_frame_fails_the_check(self):
        s = meaning.survey()
        s = dict(s, unknown_frames=["<unresolved:whatever>"])
        self.assertEqual(meaning.check(s), 1)

    def test_an_unaccounted_finding_fails_the_check(self):
        s = meaning.survey()
        s = dict(s, multi_frame=dict(s["multi_frame"],
                                     not_a_real_quantity=["page", "cell:*"]))
        self.assertEqual(meaning.check(s), 1)

    def test_a_stale_gap_entry_fails_the_check(self):
        s = meaning.survey()
        original = dict(meaning.KNOWN_GAPS)
        meaning.KNOWN_GAPS["a_gap_nothing_reports"] = "stale on purpose"
        try:
            self.assertEqual(meaning.check(s), 1)
        finally:
            meaning.KNOWN_GAPS.clear()
            meaning.KNOWN_GAPS.update(original)

    def test_a_dead_control_fails_the_check(self):
        """The vacuous-registry case, asserted through `check` itself."""
        s = meaning.survey()
        self.assertEqual(meaning.check(dict(s, n_decisions=0)), 1)

    def test_the_real_tree_passes(self):
        """…and the accounted tier is at zero unaccounted today."""
        self.assertEqual(meaning.check(meaning.survey()), 0)


class TestItIsADerivedCheckAndSaysSo(unittest.TestCase):
    """⚠️ MEASURED, not assumed: without the marker, this module's mention of
    `staff_bottom_line_page` closes a LIVE `wiring` DETAIL gap
    (`Q.WEDGE_BOX.staff_bottom_line_page`) and `wiring --check` fails STALE.
    That is `capture.py`'s recorded hazard, reproduced.
    """

    def test_the_marker_is_a_module_level_assignment(self):
        self.assertTrue(meaning.DERIVED_CHECK)
        src = pathlib.Path(meaning.__file__).read_text()
        tree = ast.parse(src)
        found = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "DERIVED_CHECK"
                    for t in n.targets)
            for n in tree.body)
        self.assertTrue(found, "the marker must be a MODULE-LEVEL assignment; "
                              "`wiring` reads it from the AST so that a "
                              "comment cannot opt a real consumer out")

    def test_it_names_a_key_that_wiring_reports(self):
        """The mention that makes the marker necessary."""
        self.assertIn("staff_bottom_line_page", meaning.PAGE_FRAME_KEYS)


class TestItDoesNotGate(unittest.TestCase):
    """`A-INK-4`: a factor CONTRIBUTES, it does not decide."""

    def test_no_pipeline_module_imports_it(self):
        root = pathlib.Path(meaning.__file__).resolve().parent
        offenders = []
        for p in sorted(root.rglob("*.py")):
            if p.name in ("meaning.py",) or p.name.startswith("test_"):
                continue
            txt = p.read_text()
            if "import meaning" in txt or "from .meaning" in txt:
                offenders.append(p.name)
        self.assertEqual(offenders, [],
                         "this is an AUDIT: nothing in the pipeline may read "
                         "it, or it has started gating behaviour")


if __name__ == "__main__":
    unittest.main()
