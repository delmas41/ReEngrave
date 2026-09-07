#!/usr/bin/env python3
"""Agent I, round 2 — a MECHANICAL census of decision points and silent deletions.

Round 1's §3.5 listed thirteen uncatalogued decision points found BY READING,
and said so: a floor, not a census. The coordinator asked for the census, and
the verifier's D2 asked for "n of m" instead of "the only". This is both.

TWO COUNTS, each with a stated mechanical definition so the number is
reproducible and arguable rather than a judgement.

1. DECISION POINTS. An AST node that selects among alternatives on a quantity:
      * an `If`/`IfExp` whose test contains a `Compare` or a `BoolOp` of them
      * a call to max / min / sorted / most_common / median / argmax / argmin
      * a filtering comprehension (a `comprehension` carrying an `if`)
   ⚠️ Bare truthiness (`if x:`, `if x is None:`) is EXCLUDED — it is control
   flow, not a decision on a measured quantity. That exclusion is the whole
   difference between this number and a `grep -c if`.

2. DISCARDING decision points — the subset where the compared quantity is
   COMPUTED INSIDE THE TEST (a Call or BinOp operand, not a bare Name or
   Attribute), so it cannot outlive the comparison. This is the mechanical
   form of the audit's central pattern.

3. SILENT-DELETION SITES. A function that removes candidates — it contains a
   `continue` inside a `for`, a `.remove(`/`.pop(`/`del`, or a filtering
   comprehension — classified by whether it ACCOUNTS for what it removed:
   does it return an int, return a tuple containing a count, or write an
   `n_*` key? ⚠️ Names and returns are read from the AST, so a function that
   counts into a caller-supplied mutable is scored as NOT accounting; those
   are listed so a reader can check them by hand.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_decision_census.py
"""
from __future__ import annotations
import ast, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ── OMR_AUDIT_GUARD ─────────────────────────────────────────────────────────
# ⚠️ A probe that prints a clean all-zero table when it means "I looked in the
# wrong place" is this audit's own recurring failure — it produced the round-2
# N4 retraction. Inputs are resolved from THIS FILE's location (never the CWD),
# `OMR_FIXTURE_ROOT` names the checkout for anything gitignored, and a missing
# or empty input set is a NON-ZERO EXIT, never a result.
import os as _os

FIXTURE_ROOT = Path(_os.environ.get(
    "OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))


def _require(paths, what):
    """Abort with exit 2 unless every named input exists and the set is non-empty."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if not paths or missing:
        print(f"FATAL: {len(missing) or 'all'} {what} missing "
              f"(set OMR_FIXTURE_ROOT if these are gitignored inputs)",
              file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        raise SystemExit(2)
    return list(paths)
# ────────────────────────────────────────────────────────────────────────────
SLICE = ["yolo_detector.py", "line_detection.py", "pitch_resolver.py",
         "rhythm.py", "voicing.py", "measure_extractor.py", "transcribe.py"]
SELECTORS = {"max", "min", "sorted", "most_common", "median", "argmax",
             "argmin", "Counter"}


def _is_computed(node) -> bool:
    """The operand was formed in this expression and cannot outlive it."""
    return isinstance(node, (ast.Call, ast.BinOp, ast.Subscript))


def _tests(node):
    if isinstance(node, ast.If):
        yield node.test
    elif isinstance(node, ast.IfExp):
        yield node.test
    elif isinstance(node, ast.comprehension):
        yield from node.ifs


def census_file(path: Path):
    tree = ast.parse(path.read_text())
    dec = disc = 0
    sel = 0
    for node in ast.walk(tree):
        for t in _tests(node):
            cmps = [n for n in ast.walk(t) if isinstance(n, ast.Compare)]
            if not cmps:
                continue
            dec += 1
            if any(_is_computed(c.left) or any(_is_computed(x) for x in c.comparators)
                   for c in cmps):
                disc += 1
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute)
                    else f.id if isinstance(f, ast.Name) else None)
            if name in SELECTORS:
                sel += 1
                dec += 1
    return dec, disc, sel


def deletion_sites(path: Path):
    """A DROP SITE reduces a collection the pipeline carries forward.

    Tightened from a first pass that scored 56 of 77 and swept in predicates
    and parsers (`_normalize_class`, `_key_sig_fifths`) that remove nothing.
    Required now: the function either
      (a) mutates a collection in place — `.remove(` / `.discard(` / `del`, or
      (b) contains a `continue` inside a `for` AND returns a list-valued name
          that is `.append`ed to inside that same loop  (the build-`kept`
          idiom this codebase uses everywhere), or
      (c) returns a comprehension carrying an `if`.
    A predicate returning bool is excluded whatever its body does.
    """
    tree = ast.parse(path.read_text())
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = list(ast.walk(fn))
        returns = [n for n in body if isinstance(n, ast.Return) and n.value is not None]
        # (a) in-place mutation
        mutates = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("remove", "discard") for n in body) or any(
            isinstance(n, ast.Delete) for n in body)
        # (c) returns a filtering comprehension
        filt_comp = any(
            isinstance(r.value, (ast.ListComp, ast.SetComp, ast.GeneratorExp))
            and any(c.ifs for c in r.value.generators) for r in returns)
        # (b) build-`kept` loop
        appended = {n.func.value.id for n in body
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "append" and isinstance(n.func.value, ast.Name)}
        returned_names = {r.value.id for r in returns if isinstance(r.value, ast.Name)}
        returned_names |= {e.id for r in returns
                           if isinstance(r.value, ast.Tuple)
                           for e in r.value.elts if isinstance(e, ast.Name)}
        build_kept = bool(appended & returned_names) and any(
            isinstance(n, ast.Continue) for n in body)
        if not (mutates or filt_comp or build_kept):
            continue
        # a predicate is not a drop site
        if all(isinstance(r.value, ast.Constant) and isinstance(r.value.value, bool)
               or isinstance(r.value, ast.Compare) for r in returns) and returns:
            continue
        counts = any(isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add)
                     for n in body)
        writes_n_key = any(
            isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.startswith("n_") for n in body)
        returns_count = any(
            "dropped" in ast.dump(r.value) or "n_drop" in ast.dump(r.value)
            or "removed" in ast.dump(r.value) for r in returns)
        out.append((fn.name, fn.lineno, counts or writes_n_key or returns_count))
    return out


def main() -> int:
    _require([ROOT / "tools/omr" / f for f in SLICE], "slice source files")
    print(f"{'file':22s}{'decisions':>11s}{'discarding':>12s}{'selectors':>11s}")
    tot = [0, 0, 0]
    for f in SLICE:
        d, x, s = census_file(ROOT / "tools/omr" / f)
        tot = [tot[0] + d, tot[1] + x, tot[2] + s]
        print(f"{f:22s}{d:11d}{x:12d}{s:11d}")
    print(f"{'TOTAL':22s}{tot[0]:11d}{tot[1]:12d}{tot[2]:11d}")
    print(f"\ndiscarding share: {tot[1]/max(1,tot[0]):.3f}")

    print("\n--- silent-deletion sites (removes candidates) ---")
    unacct = []
    n_all = 0
    for f in SLICE:
        for name, line, ok in deletion_sites(ROOT / "tools/omr" / f):
            n_all += 1
            if not ok:
                unacct.append(f"{f}:{line} {name}")
    print(f"functions that remove candidates: {n_all}")
    print(f"... of them, NO count of what they removed: {len(unacct)}"
          f"  = {len(unacct)/max(1,n_all):.3f}")
    for u in unacct:
        print(f"    {u}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
