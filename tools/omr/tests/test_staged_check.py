"""Tests for `tools.omr.staged.check` -- the derived-check roll-up.

Plan §5 Phase 0 item 0.4b (`docs/plan-2026-09-22-from-here-to-a-finished-
score.md`): one command folding the eleven derived self-checks into one
open-findings number, with three exit states so a check that cannot run is
never read as one that ran clean.

Kept fast on purpose: every real sub-check here only introspects the tree
(AST walks over committed `.py` files, reading committed JSON/markdown) --
none needs a PDF, OMR weights or a staged record, so this file belongs in
the fast tier.
"""
from __future__ import annotations

import functools
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.omr.staged import check as CK


def _fake_check(name, open_=0, broken=False, error=None):
    """One (name, fn) pair for an INJECTED check list -- never the real one."""
    def fn():
        return CK.CheckResult(name=name, open=open_, broken=broken, error=error)
    return (name, fn)


@functools.lru_cache(maxsize=1)
def _real_results():
    """`run_all()` over the REAL checks, computed once for the whole module.

    Every real check here only introspects the tree, so it is deterministic
    within one process -- caching it is what keeps this file fast even
    though several tests below want to look at the real result.
    """
    return CK.run_all()


class TestEveryRealCheckRunsAndReportsOk(unittest.TestCase):
    """(1) the command runs in-process and every listed check is `ok` today."""

    @classmethod
    def setUpClass(cls):
        cls.results = _real_results()

    def test_every_declared_check_ran(self):
        names = {r.name for r in self.results}
        declared = {name for name, _ in CK.CHECKS}
        self.assertEqual(names, declared)

    def test_none_of_the_eleven_derived_checks_is_broken(self):
        broken = [(r.name, r.error, r.note) for r in self.results
                  if r.broken or r.error]
        self.assertEqual(broken, [],
                          f"a derived check reports BROKEN on the current "
                          f"tree: {broken}. Either the tree really is broken "
                          f"(fix it) or this check's wiring to the module's "
                          f"own API has drifted (fix check.py).")

    def test_every_open_count_is_a_non_negative_int(self):
        for r in self.results:
            self.assertIsInstance(r.open, int, r.name)
            self.assertGreaterEqual(r.open, 0, r.name)

    def test_render_and_json_do_not_crash_and_mention_every_check(self):
        text = CK.render(self.results)
        payload = CK.as_json(self.results)
        for r in self.results:
            self.assertIn(r.name, text)
            self.assertIn(r.name, payload["checks"])


class TestTheTotalIsTheSumOfTheParts(unittest.TestCase):
    """(2) the total equals the sum of the parts, on real and fake lists."""

    def test_total_open_on_the_real_checks(self):
        results = _real_results()
        self.assertEqual(CK.total_open(results), sum(r.open for r in results))

    def test_total_open_on_an_injected_list(self):
        checks = [_fake_check("a", 3), _fake_check("b", 5), _fake_check("c", 0)]
        results = CK.run_all(checks)
        self.assertEqual(CK.total_open(results), 8)

    def test_rendered_total_line_matches(self):
        checks = [_fake_check("a", 3), _fake_check("b", 5)]
        results = CK.run_all(checks)
        last_line = CK.render(results).splitlines()[-1]
        self.assertTrue(last_line.startswith("TOTAL"))
        self.assertIn("open=8", last_line)

    def test_json_total_matches_the_sum_of_its_own_checks(self):
        checks = [_fake_check("a", 3), _fake_check("b", 5)]
        results = CK.run_all(checks)
        payload = CK.as_json(results)
        self.assertEqual(payload["total"], 8)
        self.assertEqual(sum(v["open"] for v in payload["checks"].values()),
                          payload["total"])


class TestExitCodeMapping(unittest.TestCase):
    """(3) BROKEN(2) / OPEN(1) / CLEAN(0), using an INJECTED fake check list
    so this suite never depends on today's real open-findings count."""

    def test_clean_when_everything_is_zero_and_not_broken(self):
        results = CK.run_all([_fake_check("a", 0), _fake_check("b", 0)])
        self.assertEqual(CK.exit_code(results), 0)
        self.assertFalse(CK.any_broken(results))

    def test_open_when_a_check_has_findings(self):
        results = CK.run_all([_fake_check("a", 0), _fake_check("b", 3)])
        self.assertEqual(CK.exit_code(results), 1)

    def test_broken_when_a_check_reports_broken_even_at_zero_open(self):
        results = CK.run_all([_fake_check("a", 0, broken=True),
                               _fake_check("b", 0)])
        self.assertEqual(CK.exit_code(results), 2)

    def test_broken_outranks_open(self):
        results = CK.run_all([_fake_check("a", 5),
                               _fake_check("b", 0, broken=True)])
        self.assertEqual(CK.exit_code(results), 2)

    def test_a_crashing_check_is_broken_not_silently_dropped(self):
        def _boom():
            raise ValueError("synthetic failure for this test")
        results = CK.run_all([("c", _boom), _fake_check("ok", 0)])
        self.assertEqual(len(results), 2)
        crashed = next(r for r in results if r.name == "c")
        self.assertTrue(crashed.broken)
        self.assertIn("synthetic failure", crashed.error)
        self.assertEqual(CK.exit_code(results), 2)

    def test_main_returns_the_exit_code_run_all_and_exit_code_would_give(self):
        # `main()` has no injection point on the CLI itself, so this pins the
        # mapping is consistent (main() must not compute its own separate
        # rule) rather than re-asserting the real tree's own open count.
        fixed = CK.run_all([_fake_check("a", 2)])
        with mock.patch.object(CK, "run_all", return_value=fixed):
            code = CK.main(["--json"])
        self.assertEqual(code, CK.exit_code(fixed))
        self.assertEqual(code, 1)


class TestTheWriterRefusesADirtyTree(unittest.TestCase):
    """(4) `write_report` / `--write` refuses to write on a dirty tree unless
    `force=True`, and never touches the real repo tree here."""

    @staticmethod
    def _results():
        return [CK.CheckResult(name="x", open=2, broken=False)]

    def test_refuses_and_writes_nothing_when_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with mock.patch.object(
                    CK, "_git", side_effect=["deadbeef00", " M some/file.py\n"]):
                with self.assertRaises(RuntimeError) as ctx:
                    CK.write_report(self._results(), force=False, out_dir=out_dir)
            self.assertIn("DIRTY", str(ctx.exception))
            self.assertEqual(list(out_dir.glob("*")), [],
                              "a refused write must leave no file behind")

    def test_force_writes_on_a_dirty_tree_and_records_dirty_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with mock.patch.object(
                    CK, "_git", side_effect=["deadbeef00", " M some/file.py\n"]):
                path = CK.write_report(self._results(), force=True, out_dir=out_dir)
            payload = json.loads(path.read_text())
            self.assertTrue(payload["dirty"])
            self.assertEqual(payload["tree"], "deadbeef00")
            self.assertEqual(payload["total"], 2)

    def test_writes_without_force_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with mock.patch.object(CK, "_git", side_effect=["deadbeef00", ""]):
                path = CK.write_report(self._results(), force=False, out_dir=out_dir)
            payload = json.loads(path.read_text())
            self.assertFalse(payload["dirty"])
            self.assertEqual(path, out_dir / "open-findings.json")


if __name__ == "__main__":
    unittest.main()
