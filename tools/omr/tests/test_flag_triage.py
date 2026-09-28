"""Enforces the flag triage in `docs/flags-2026-09.md` (roadmap 0.2b).

The doc's own §4 states the job: *"remove the `promote — now` flags, delete
`OMR_ADJUDICATE`, introduce `OMR_RESEARCH`, and add one derived test
asserting that no module under `tools/omr/staged/` reads a flag from §2 and
that every `OMR_*` read in the tree appears in this file."* This is that
test, plus (c): no flag the doc marks REMOVED at 0.2b is still read anywhere.

⚠️⚠️ WHY THIS NEEDS ITS OWN READER RATHER THAN JUST IMPORTING
`test_flag_default_direction.default_on_flags()`. That scan answers a
narrower question — *which flags are compared with `in`/`not in` against a
literal word-set, and which way do they default* — and it is blind by
construction to two shapes this file's job needs to see:

  * an intermediate variable (`raw = os.environ.get(X, ...); return raw not
    in {...}`) splits the `.get()` call from the comparison across two
    statements, so a scan anchored on `Compare.left` being the call itself
    never reaches it. `OMR_CELL_LINE_TRACE` reads exactly this way
    (`measure_extractor.py`) and is why the 2026-09-22 audit's own table
    missed it — a code search for the boolean-comparison shape would have
    missed it too.
  * a `pydantic_settings.BaseSettings` field (`backend/core/config.py`'s
    `omr_job_budget_s`) is never an `os.environ.get` call at all; pydantic
    reads the env var from the field name.

The question here is PRESENCE — does this flag have a row anywhere in the
doc, and is a §2/REMOVED flag read where it must not be — never DIRECTION,
which stays `test_flag_default_direction.py`'s job and is not re-derived
here. The two scans are deliberately different widths for different
questions, not two copies of one.
"""

from __future__ import annotations

import ast
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "flags-2026-09.md"
STAGED_PREFIX = "tools/omr/staged/"


def _module_string_consts(tree: ast.AST) -> dict:
    """`{NAME: "literal"}` for every module-level `NAME = "literal"`."""
    consts = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            consts[node.targets[0].id] = node.value.value
    return consts


def _iter_py_files(base: str):
    for f in sorted((ROOT / base).rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if "/tests/" in rel or rel.endswith("/conftest.py"):
            continue
        yield f, rel


def flags_read(base: str):
    """Yield `(relpath, lineno, FLAG)` for every `OMR_*` flag read under
    `base` (a directory relative to ROOT), skipping test directories.

    Two shapes, deliberately wider than `default_on_flags`'s:

    1. Any `<anything>.get(<OMR_LITERAL_OR_CONST>, ...)` or
       `os.getenv(<OMR_LITERAL_OR_CONST>, ...)` call — not anchored to
       `os.environ` by name, because `key_signature_corroboration.py` and
       `absent_instrument.py` route through `(env if env is not None else
       os.environ).get(...)` for testability, which is not an `Attribute`
       named `environ` at all.
    2. A `pydantic_settings.BaseSettings` subclass's `AnnAssign` field, whose
       uppercased name is the env var pydantic reads for it.
    """
    for f, rel in _iter_py_files(base):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        consts = _module_string_consts(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_dict_get = isinstance(func, ast.Attribute) and func.attr == "get"
            is_getenv = (isinstance(func, ast.Attribute) and func.attr == "getenv"
                         and isinstance(func.value, ast.Name)
                         and func.value.id == "os")
            if not (is_dict_get or is_getenv) or not node.args:
                continue
            head = node.args[0]
            flag = None
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                flag = head.value
            elif isinstance(head, ast.Name) and head.id in consts:
                flag = consts[head.id]
            if flag and flag.startswith("OMR_"):
                yield rel, node.lineno, flag
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
                     for b in node.bases]
            if "BaseSettings" not in bases:
                continue
            for stmt in node.body:
                if (isinstance(stmt, ast.AnnAssign)
                        and isinstance(stmt.target, ast.Name)):
                    env_name = stmt.target.id.upper()
                    if env_name.startswith("OMR_"):
                        yield rel, stmt.lineno, env_name


def all_flags_read():
    """Every `(relpath, lineno, FLAG)` under `tools/` and `backend/`."""
    return list(flags_read("tools")) + list(flags_read("backend"))


# ─────────────────────────────────────────────────────────────────────────────
# The doc side
# ─────────────────────────────────────────────────────────────────────────────

_SECTION = re.compile(r"^## (\d+)\.", re.MULTILINE)


def _section(number: int) -> str:
    """The text of `## <number>. ...` up to the next `## `, exclusive."""
    text = DOC.read_text(encoding="utf-8")
    starts = [(int(m.group(1)), m.start()) for m in _SECTION.finditer(text)]
    starts.append((None, len(text)))
    for i, (n, pos) in enumerate(starts[:-1]):
        if n == number:
            return text[pos:starts[i + 1][1]]
    return ""


def doc_flags() -> set:
    """Every `OMR_[A-Z0-9_]+` token named anywhere in the doc."""
    return set(re.findall(r"OMR_[A-Z0-9_]+", DOC.read_text(encoding="utf-8")))


def frozen_flags() -> set:
    """Flags listed in §2 — "Legacy-only flags — frozen"."""
    return set(re.findall(r"`(OMR_[A-Z0-9_]+)`", _section(2)))


def removed_flags() -> set:
    """Flags whose §1 row is marked REMOVED at this roadmap item.

    ⚠️ A MARKER THIS FILE OWNS, not a re-guess at prose: a row is only
    counted once its verdict cell contains the literal substring
    `REMOVED 0.2b`, which this lane's own edits to the doc introduce for
    exactly the flags it removed (`OMR_HOLD_OUT_UNIDENTIFIED`,
    `OMR_METER_SEGMENTS`, `OMR_ADJUDICATE`). A flag promoted or deleted at a
    LATER roadmap item does not carry this marker yet and is not checked
    here until it does — this test enforces 0.2b's own removals, not the
    whole table's aspirations.
    """
    out = set()
    for line in _section(1).splitlines():
        if not line.startswith("|") or "REMOVED 0.2b" not in line:
            continue
        m = re.search(r"`(OMR_[A-Z0-9_]+)`", line)
        if m:
            out.add(m.group(1))
    return out


class TestNoStagedModuleReadsAFrozenFlag(unittest.TestCase):
    """docs/flags-2026-09.md §2: "None may be read from `tools/omr/staged/`"."""

    def test_the_frozen_list_is_real(self):
        """⚠️ The positive control — a check against an empty list passes
        vacuously."""
        self.assertGreater(len(frozen_flags()), 20)

    def test_no_staged_file_reads_one(self):
        frozen = frozen_flags()
        bad = [(rel, line, flag) for rel, line, flag in flags_read("tools")
               if rel.startswith(STAGED_PREFIX) and flag in frozen]
        self.assertEqual(bad, [],
                         "\n".join(f"{rel}:{line} reads frozen flag {flag}"
                                   for rel, line, flag in bad))

    def test_the_control_can_fail(self):
        """Plant a frozen-flag read under `tools/omr/staged/` in spirit: this
        asserts the FILTER used above actually discriminates by prefix,
        against a path that is deliberately made to look like one."""
        frozen = frozen_flags()
        flag = next(iter(frozen))
        planted = [("tools/omr/staged/_planted.py", 1, flag)]
        bad = [(rel, line, f) for rel, line, f in planted
               if rel.startswith(STAGED_PREFIX) and f in frozen]
        self.assertTrue(bad, "the staged-prefix + frozen-set filter is vacuous")


class TestEveryFlagReadHasADocRow(unittest.TestCase):
    """docs/flags-2026-09.md §4: "every `OMR_*` read in the tree appears in
    this file"."""

    def test_the_scan_finds_something(self):
        """⚠️ The positive control — an empty scan would pass this test for
        the wrong reason."""
        seen = {flag for _r, _l, flag in all_flags_read()}
        self.assertGreater(len(seen), 30)
        # Named flags this file was written FOR, so a regression in the
        # broader reader (§ above the class) that stopped seeing them would
        # be caught here rather than by a quietly-shrinking count.
        for expect in ("OMR_CELL_LINE_TRACE", "OMR_JOB_BUDGET_S",
                       "OMR_ABSENT_INSTRUMENT_VETO", "OMR_KEYSIG_CORROBORATION"):
            self.assertIn(expect, seen)

    def test_every_read_flag_is_documented(self):
        documented = doc_flags()
        missing = {}
        for rel, line, flag in all_flags_read():
            if flag not in documented:
                missing.setdefault(flag, []).append(f"{rel}:{line}")
        self.assertEqual(missing, {}, "undocumented OMR_* flag(s): " +
                         ", ".join(f"{f} ({'; '.join(locs)})"
                                   for f, locs in sorted(missing.items())))


class TestNoRemovedFlagIsStillRead(unittest.TestCase):
    """A flag this roadmap item promoted-now or deleted must not still be
    read anywhere — the doc's REMOVED 0.2b marker is a claim about the tree,
    checked here rather than trusted."""

    def test_the_removed_list_is_real(self):
        """⚠️ The positive control."""
        self.assertGreaterEqual(len(removed_flags()), 3)

    def test_none_of_them_are_read(self):
        removed = removed_flags()
        bad = [(rel, line, flag) for rel, line, flag in all_flags_read()
               if flag in removed]
        self.assertEqual(bad, [],
                         "\n".join(f"{rel}:{line} still reads removed flag "
                                   f"{flag}" for rel, line, flag in bad))


if __name__ == "__main__":
    unittest.main()
