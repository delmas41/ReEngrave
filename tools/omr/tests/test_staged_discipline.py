"""Discipline checks over the staged package — the ones a null could hide.

⚠️ THIS FILE EXISTS BECAUSE OF A REAL BUG WITH A GREEN SUITE. The first cut
of `adjudicators/identity.py` contained

    from ...omr.instruments import lookup

inside a function body. That resolves to `tools.omr.omr.instruments`, which
does not exist. **Every test passed**, because the decision was a stub at the
time and the import never executed. It was caught by reading, not by running.

That is the seventh instance this week of *a null that reads as a pass*, and
the first inside the new architecture — so it gets a check rather than a
lesson.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
import unittest
from pathlib import Path

import tools.omr.staged as staged
from tools.omr.staged import adjudicate, evaluate
from tools.omr.staged import adjudicators, consequences  # noqa: F401

STAGED_DIR = Path(staged.__file__).parent


def _modules():
    """Every module in the staged package, including the adjudicators.

    Yields `(module_name, path, is_package)`. ⚠️ The third element matters:
    a relative import inside `__init__.py` resolves against the PACKAGE
    ITSELF, not against the package's parent, so a resolver that treats a
    package like an ordinary module reports a false failure on every
    `from .record import ...` -- which is exactly what the first cut of this
    file did.
    """
    for path in sorted(STAGED_DIR.rglob("*.py")):
        rel = path.relative_to(STAGED_DIR.parent.parent.parent)
        is_package = path.name == "__init__.py"
        name = ".".join(rel.with_suffix("").parts)
        if is_package:
            name = name[: -len(".__init__")]
        yield name, path, is_package


def _resolve(node: ast.ImportFrom, module_name: str, is_package: bool) -> str:
    """Turn a possibly-relative `from X import Y` into an absolute module."""
    if not node.level:
        return node.module or ""
    parts = module_name.split(".")
    # For an ordinary module, level 1 means "my package" = parts[:-1].
    # For a package's __init__, level 1 means "me".
    strip = node.level - 1 if is_package else node.level
    base = parts[: len(parts) - strip] if strip else parts
    return ".".join(base + ([node.module] if node.module else []))


class TestEveryImportIsReachable(unittest.TestCase):
    """⚠️ Including imports inside function bodies, which is where the bug was.

    A lazy import is the normal way to break a cycle in this package
    (`evaluate._ensure_rules`, `consequences.restate_pitch`), so they are
    common here — and each one is a line that no test may ever execute.
    """

    def test_every_from_import_resolves(self):
        failures = []
        for module_name, path, is_pkg in _modules():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                target = _resolve(node, module_name, is_pkg)
                if not target:
                    continue
                try:
                    importlib.import_module(target)
                except Exception as exc:            # noqa: BLE001
                    failures.append(
                        f"{module_name}:{node.lineno} -> {target!r} "
                        f"({type(exc).__name__})")
        self.assertEqual(failures, [], "unreachable imports:\n  " +
                         "\n  ".join(failures))

    def test_every_imported_name_exists(self):
        """A module that imports fine can still name something it does not
        have -- and a lazily-imported missing NAME fails at exactly the same
        never-executed line."""
        failures = []
        for module_name, path, is_pkg in _modules():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                target = _resolve(node, module_name, is_pkg)
                if not target:
                    continue
                try:
                    mod = importlib.import_module(target)
                except Exception:                   # noqa: BLE001
                    continue                        # the other test owns this
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if hasattr(mod, alias.name):
                        continue
                    # ⚠️ `from . import gather` names a SUBMODULE, and a
                    # package has no attribute for one until it is imported.
                    # Absence of the attribute is therefore not evidence.
                    try:
                        importlib.import_module(f"{target}.{alias.name}")
                        continue
                    except Exception:               # noqa: BLE001
                        pass
                    failures.append(
                        f"{module_name}:{node.lineno} -> "
                        f"{target}.{alias.name}")
        self.assertEqual(failures, [], "missing names:\n  " +
                         "\n  ".join(failures))


class TestEveryDecisionIsCallable(unittest.TestCase):
    """A declared stub must still be a working function, not a placeholder
    that would explode the first time someone un-stubs it."""

    def test_every_registered_decision_has_a_live_function(self):
        for quantity, spec in adjudicate.REGISTRY.items():
            self.assertTrue(callable(spec.fn), quantity)

    def test_every_stub_declares_itself(self):
        """⚠️ A stub is fine; a decision that merely always abstains without
        SAYING it is a stub is not -- the two are indistinguishable from the
        output, which is the whole failure family this package is about."""
        for quantity in adjudicate.stubs():
            self.assertTrue(adjudicate.REGISTRY[quantity].stub)

    def test_every_ordered_quantity_has_an_owner(self):
        self.assertEqual([q for q in adjudicate.ORDER
                          if q not in adjudicate.REGISTRY], [])


class TestEveryConsequenceDeclaresABound(unittest.TestCase):
    """⚠️ `bound` is prose and required. Every propagation in the tree that
    works is bounded, and a rule that cannot state its bound in one sentence
    has not been thought through."""

    def test_bounds_are_present_and_substantive(self):
        for r in evaluate.RULES:
            with self.subTest(rule=r.consequence.value):
                self.assertTrue(r.bound.strip())
                self.assertGreater(len(r.bound), 40, "a bound must say what "
                                   "stops the rule running away")

    def test_every_rule_is_downhill(self):
        for r in evaluate.RULES:
            evaluate.check_downhill(r.cause, r.effect)


class TestVocabulariesAreClosed(unittest.TestCase):
    def test_no_adjudicator_invents_an_abstention_reason(self):
        """Every `reason` a decision can return is declared, so a reason that
        does not exist is a startup failure and not a mystery string in a
        report."""
        from tools.omr.staged.record import ABSTAIN
        for quantity, spec in adjudicate.REGISTRY.items():
            self.assertIn(ABSTAIN.NOT_IMPLEMENTED, spec.reasons, quantity)


if __name__ == "__main__":
    unittest.main()
