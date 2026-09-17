#!/usr/bin/env python3
"""Derive the raw material for docs/map-flags-gates-and-guards-2026-09-16.md.

Sean's question: "Do we have a single place where all gates, guards, default
settings or anything that could be flipped is stored?" The answer was half —
`tools/omr/tests/test_flag_default_direction.py` already derives every simple
`os.environ.get(FLAG, default)` site compared inline to a literal word set,
and CLAUDE.md has prose tables with the measured evidence. Neither is a full
inventory: the AST scan in that test module misses two patterns that are
common in this codebase (verified by reading the source, see the markdown
doc's disagreements section) —

  1. the two-statement form:  raw = os.environ.get(FLAG, default)
                              return raw in {...}        # separate statement
  2. the "environ or an injected dict" form:
       raw = (env if env is not None else os.environ).get(FLAG, default)

This script does NOT replace that test or re-implement its inline scan (the
task instructions say not to). It runs alongside it, imports its
`default_on_flags()` for the sites it already covers, and adds:

  * every `os.environ.get(...)` / `os.getenv(...)` call site anywhere under
    tools/ or backend/ (excluding tests) whose flag name is an OMR_* or
    MAESTRO_* literal (or a module-level string constant), with its default
    literal where the default itself is a literal — this is the master
    ENV-FLAG site list, deduplicated by flag name;
  * every module-level ALL-CAPS constant assigned a plain numeric literal
    anywhere under tools/omr/ (excluding tests) — the master NUMERIC-GUARD
    list;
  * for both lists, whether the flag/constant NAME is mentioned anywhere in
    CLAUDE.md (a mechanical presence check only — it does not attempt to
    read the surrounding prose, which is why the markdown doc quotes CLAUDE.md
    by hand for the MEASURED/ASSERTED judgement and says so).

Run:
    python3 benchmarks/omr-flags-map-2026-09/derive_map.py

Prints three sections to stdout: env-flag sites, numeric-guard constants, and
a disagreements scan (code vs CLAUDE.md name sets). No behaviour anywhere is
touched; this only reads.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_MD = ROOT / "CLAUDE.md"

# Reuse the existing derived scan rather than re-implement it.
sys.path.insert(0, str(ROOT / "tools" / "omr" / "tests"))
import test_flag_default_direction as existing  # noqa: E402


def _iter_py_files(*roots):
    for root in roots:
        for f in sorted((ROOT / root).rglob("*.py")):
            rel = str(f.relative_to(ROOT))
            if "/tests/" in rel or rel.startswith("tests/") or "/test_" in rel:
                continue
            if f.name.startswith("test_"):
                continue
            yield f


def _module_string_consts(tree) -> dict:
    consts = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            consts[node.targets[0].id] = node.value.value
    return consts


def _is_environ_like(node) -> bool:
    """True for `os.environ`, or an `X if Y else os.environ` / `os.environ if
    Y else X` conditional (the `(env if env is not None else os.environ)`
    shape used by key_signature_corroboration.py, absent_instrument.py,
    offroster_name.py)."""
    if isinstance(node, ast.Attribute) and node.attr == "environ":
        return True
    if isinstance(node, ast.IfExp):
        return _is_environ_like(node.body) or _is_environ_like(node.orelse)
    return False


def _literal_or_none(node):
    if isinstance(node, ast.Constant):
        return node.value
    return None


def env_flag_sites():
    """Every `os.environ.get(...)` / `os.getenv(...)` call naming an OMR_* or
    MAESTRO_* flag, anywhere under tools/ or backend/ (non-test code).

    Yields dicts: file, line, flag, default, assigned_to (the Name the
    result is bound to, if any — None for an inline comparison), func
    (enclosing function name, for locating direction evidence).
    """
    for f in _iter_py_files("tools", "backend"):
        try:
            src = f.read_text()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        consts = _module_string_consts(tree)
        # map id(node) -> enclosing function name, and id(node) -> assigned var
        func_of = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(fn):
                    func_of[id(child)] = fn.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            is_getenv = (isinstance(node.func, ast.Attribute)
                         and node.func.attr == "getenv"
                         and isinstance(node.func.value, ast.Name)
                         and node.func.value.id == "os")
            is_environ_get = (isinstance(node.func, ast.Attribute)
                              and node.func.attr == "get"
                              and _is_environ_like(node.func.value))
            if not (is_getenv or is_environ_get):
                continue
            if not node.args:
                continue
            head = node.args[0]
            flag = None
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                flag = head.value
            elif isinstance(head, ast.Name) and head.id in consts:
                flag = consts[head.id]
            if not flag or not (flag.startswith("OMR_") or flag.startswith("MAESTRO_")):
                continue
            default = None
            if len(node.args) > 1:
                default = _literal_or_none(node.args[1])
            yield {
                "file": str(f.relative_to(ROOT)),
                "line": node.lineno,
                "flag": flag,
                "default": default,
                "func": func_of.get(id(node)),
                "kind": "getenv" if is_getenv else "environ.get",
            }


def numeric_guard_constants():
    """Every MODULE-LEVEL ALL-CAPS constant assigned a plain int/float
    literal under tools/omr/ (non-test code). Class-level and function-local
    constants are deliberately excluded — the ones CLAUDE.md discusses as
    "guards" are the module-level thresholds/floors read by an adjudicator or
    a detector, not incidental local numbers."""
    name_re = re.compile(r"^[A-Z][A-Z0-9_]*$")
    for f in _iter_py_files("tools/omr"):
        try:
            src = f.read_text()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:  # module level only
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            name = node.targets[0].id
            if not name_re.match(name):
                continue
            if not (isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, (int, float))
                    and not isinstance(node.value.value, bool)):
                continue
            yield {
                "file": str(f.relative_to(ROOT)),
                "line": node.lineno,
                "name": name,
                "value": node.value.value,
            }


def claude_md_text() -> str:
    return CLAUDE_MD.read_text() if CLAUDE_MD.is_file() else ""


def names_in_claude_md(names, text=None):
    text = text if text is not None else claude_md_text()
    return {n for n in names if n in text}


def main():
    text = claude_md_text()

    flag_sites = list(env_flag_sites())
    flags = sorted({s["flag"] for s in flag_sites})
    derived_direction = {}
    for path, line, flag, default, op, members, on in existing.default_on_flags():
        derived_direction.setdefault(flag, set()).add(on)

    claude_flag_names = sorted(set(re.findall(r"`(OMR_[A-Z_]+)`", text))
                                | set(re.findall(r"`(MAESTRO_[A-Z_]+)`", text)))

    guards = list(numeric_guard_constants())
    guard_names = sorted({g["name"] for g in guards})

    result = {
        "env_flag_sites": flag_sites,
        "env_flags_unique": flags,
        "env_flags_with_derived_direction": {
            k: sorted(v) for k, v in derived_direction.items()
        },
        "claude_md_flag_mentions": claude_flag_names,
        "flags_in_code_not_in_claude_md": sorted(set(flags) - set(claude_flag_names)),
        "flags_in_claude_md_not_in_code": sorted(set(claude_flag_names) - set(flags)),
        "numeric_guards": guards,
        "numeric_guard_names_unique": guard_names,
        "guards_mentioned_in_claude_md": sorted(names_in_claude_md(guard_names, text)),
        "guards_not_mentioned_in_claude_md": sorted(set(guard_names) - names_in_claude_md(guard_names, text)),
    }

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
