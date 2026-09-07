#!/usr/bin/env python3
"""Static check: no probe in this directory may lie about where it looked.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/check_probe_hygiene.py

Exits non-zero on any violation. Cheap (a source scan, no fixtures, no imports),
so it is safe to run anywhere — including a worktree with no fixtures at all,
which is exactly the environment the defects it looks for hide in.

⚠️ **Why this exists.** VERIFICATION.md §D16 records the same fault being
introduced TWICE by the audit's own agents, in mirror-image forms, after it had
already been written down once:

  · round 1 — six probes hard-code `/Users/seanjohnson/Desktop/ReEngrave`, so
    committed into the audit tree they silently measure a DIFFERENT tree;
  · round 2 — seven probes went CWD-relative instead, so from anywhere but the
    main checkout they print a clean all-zero table and **exit 0**.

Round 2 is the worse of the two, and a review caught neither. A prose warning
did not stop the second instance; a check that fails does.

THREE RULES, and each maps to an observed failure rather than to a style
preference:

  R1  no hard-coded `/Users/...` outside the declared default constants
      → "measured a different tree" (M4)
  R2  no bare CWD-relative `benchmarks/...` glob
      → "found nothing, exited 0" (D16)
  R3  every glob routed through must_glob/fixture_glob/repo_glob, or carrying
      its own explicit empty-guard
      → the actual bug: emptiness indistinguishable from a negative result
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELF = {"fixture_root.py", "check_probe_hygiene.py"}

#: Constants that are ALLOWED to hold an absolute default, because the path
#: names a gitignored tree that genuinely cannot be found relatively. Each must
#: go through `env_path()`, so the pin is nameable and overridable.
ENV_PATH_OK = re.compile(r'env_path\(\s*"[A-Z_]+"\s*,')

#: A probe may keep its own guard instead of ours, as long as it FAILS.
OWN_GUARD = re.compile(
    r"if not files:.{0,200}?return 1|if not files:.{0,200}?SystemExit|"
    r"if not files:.{0,200}?sys\.exit", re.S)

ROUTED = ("must_glob", "fixture_glob", "repo_glob")


def sources() -> list[Path]:
    out = [p for p in sorted(HERE.glob("*.py")) if p.name not in SELF]
    out += sorted((HERE / "verify").glob("*.py"))
    return out


def check(path: Path) -> list[str]:
    src = path.read_text()
    bad: list[str] = []

    for i, line in enumerate(src.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("#:"):
            continue

        # R1 — a hard-coded checkout, not wrapped in env_path()
        if "/Users/" in line and not ENV_PATH_OK.search(line):
            # the continuation line of a multi-line env_path(...) call
            ctx = "\n".join(src.split("\n")[max(0, i - 4):i])
            if not ENV_PATH_OK.search(ctx):
                bad.append(f"R1 {path.name}:{i} hard-coded checkout — "
                           f"use fixture_root()/repo_root(), or env_path() for a "
                           f"deliberate pin\n     {stripped[:100]}")

        # R2 — a bare CWD-relative benchmarks/ glob
        if re.search(r"""glob\.glob\(\s*['"]benchmarks/""", line):
            bad.append(f"R2 {path.name}:{i} CWD-relative glob — finds nothing "
                       f"and exits 0 from any other cwd\n     {stripped[:100]}")

    # R3 — every glob call routed, or self-guarded
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = (fn.attr if isinstance(fn, ast.Attribute) else
                fn.id if isinstance(fn, ast.Name) else None)
        if name not in ("glob", "rglob", "iglob"):
            continue
        line = src.split("\n")[node.lineno - 1].strip()
        if any(r in line for r in ROUTED):
            continue
        if OWN_GUARD.search(src):
            continue
        bad.append(f"R3 {path.name}:{node.lineno} unguarded glob — an empty "
                   f"match must EXIT, not report zero\n     {line[:100]}")
    return bad


def main() -> int:
    findings: list[str] = []
    files = sources()
    for p in files:
        findings += check(p)

    print(f"probe hygiene: {len(files)} files checked")
    if not findings:
        print("  clean — every probe names the tree it reads and fails on an "
              "empty glob")
        return 0
    print(f"  {len(findings)} violation(s):\n")
    for f in findings:
        print("  " + f)
    print("\n  See fixture_root.py for the two-root design and why "
          '"just make the paths relative" is the wrong fix.')
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
