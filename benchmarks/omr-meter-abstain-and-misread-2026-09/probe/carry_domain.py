"""DOES `OMR_METER_CARRY` HAVE A DOMAIN ON THE BREITKOPF RECORD? — derived, no weights.

⚠️⚠️ THIS PROBE EXISTS TO CORRECT A CLAIM THIS THREAD COMMITTED. The
2026-09-16 pricing-arm write-up read Brahms 1 / Breitkopf p0-3's
`decided 7 of 7  {'voted': 2, 'change_only': 5}` and concluded **"neither flag
has a domain on this document"**, reasoning that `_meter_fallbacks` is reached
only from failure paths and nothing failed. The premise is right and the
inference is backwards: `change_only` IS a fallback rung -- the THIRD of three
-- so a `change_only` verdict is POSITIVE EVIDENCE that the fallbacks ran, and
that `_carry_meter` was called before it.

So the carry's domain on that document is not 0. It is every system whose
verdict reason is reachable only through `_meter_fallbacks`.

⚠️ WHAT THIS PROBE DOES NOT DO. It never says the carry was REFUSED, only that
it was ASKED. Distinguishing "asked and refused by the bars" from "asked and
found no source" needs the per-system reason under a default-ON tree, which no
committed artefact holds -- see FINDINGS section 12 for the arm that would get
it. Nothing here is gathered, exported or scored.

    python3 probe/carry_domain.py
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RHYTHM = ROOT / "tools" / "omr" / "staged" / "adjudicators" / "rhythm.py"
#: The shared Breitkopf record's own write-up. Its section 3 table is the only
#: committed statement of that record's per-system meter reasons -- the record
#: itself is 443 MB under the gitignored `library/`.
SHARED = (ROOT / "benchmarks" / "omr-shared-records-2026-09" / "FINDINGS.md")
#: The tools tree that produced that record. Its provenance names `e282ae0c`,
#: which a rebase orphaned; that write-up's section 8 records the tools tree as
#: IDENTICAL to this commit's, which is permanently on main.
RECORD_TOOLS_COMMIT = "da2c9c11"

FALLBACK = "_meter_fallbacks"
CARRY = "_carry_meter"


def _fn(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise SystemExit("PROBE DEAD: %s is gone from rhythm.py" % name)


def _calls(node: ast.AST) -> list[str]:
    """Names called inside `node`, in source order."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            out.append((sub.lineno, sub.func.id))
    return [n for _, n in sorted(out)]


def rung_order(tree: ast.Module) -> list[str]:
    """The fallback rungs, in the order `_meter_fallbacks` tries them."""
    fb = _fn(tree, FALLBACK)
    return [n for n in _calls(fb) if n.startswith("_") and n != FALLBACK]


def reachable_only_via_fallbacks(tree: ast.Module) -> dict[str, bool]:
    """For each rung, is EVERY call site of it inside the fallback chain?

    ⚠️ This is the load-bearing step and it is why the probe is an AST walk
    rather than a grep. `_change_only` has TWO call sites -- one in
    `_meter_fallbacks` and one inside `_meter_from_bars` -- and the inference
    only holds because `_meter_from_bars` is ITSELF called from nowhere else.
    A grep for `_change_only(` would have shown two sites and said nothing
    about whether the second one is also downstream of the carry.
    """
    owners: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for name in _calls(node):
            owners.setdefault(name, set()).add(node.name)

    chain = {FALLBACK}
    for _ in range(4):                       # fixpoint; the chain is 2 deep
        for name, callers in owners.items():
            if callers and callers <= chain:
                chain.add(name)
    return {n: (owners.get(n, set()) <= chain) for n in rung_order(tree)}


def carry_is_flag_gated(tree: ast.Module) -> bool:
    """Does `_carry_meter` return before doing anything when the flag is off?"""
    fn = _fn(tree, CARRY)
    for stmt in fn.body:
        if isinstance(stmt, ast.If) and isinstance(stmt.body[0], ast.Return):
            if "enabled" in ast.dump(stmt.test):
                return True
    return False


def flag_default(commit: str | None, flag: str) -> str | None:
    """The literal default of `flag` in a tree, or None if unreadable."""
    path = "tools/omr/staged/adjudicators/rhythm.py"
    if commit is None:
        src = RHYTHM.read_text()
    else:
        try:
            src = subprocess.run(["git", "show", "%s:%s" % (commit, path)],
                                 cwd=ROOT, capture_output=True, text=True,
                                 check=True).stdout
        except subprocess.CalledProcessError:
            return None
    m = re.search(r'environ\.get\(\s*%s_ENV\s*,\s*"([^"]*)"' % flag, src)
    if m:
        return m.group(1)
    # the deny-list form the default-ON flags use
    m = re.search(r'environ\.get\(\s*%s_ENV\s*,\s*"([^"]*)"\s*\)[^\n]*not in'
                  % flag, src)
    return m.group(1) if m else None


def record_reasons() -> dict[str, int]:
    """The per-system meter reason census, parsed from the shared write-up."""
    if not SHARED.is_file():
        return {}
    census: dict[str, int] = {}
    for line in SHARED.read_text().splitlines():
        # | p1 s1 | `4/4` | `change_only` | spurious, 1 staff, support 3.0 |
        m = re.match(r"\|\s*p\d\s*s\d\s*\|[^|]*\|\s*`([a-z_]+)`\s*\|", line)
        if m:
            census[m.group(1)] = census.get(m.group(1), 0) + 1
    return census


def main() -> int:
    tree = ast.parse(RHYTHM.read_text())

    order = rung_order(tree)
    print("RUNG ORDER in %s: %s" % (FALLBACK, " -> ".join(order)))
    if not order or order[0] != CARRY:
        print("REFUSED: the carry is no longer the first rung; the whole "
              "inference below rests on it being tried first.")
        return 2

    reach = reachable_only_via_fallbacks(tree)
    print("\nREACHABLE ONLY THROUGH THE FALLBACK CHAIN:")
    for name in order:
        print("   %-20s %s" % (name, "yes" if reach.get(name) else "NO"))
    if not reach.get("_change_only"):
        print("REFUSED: `_change_only` is now callable outside the fallback "
              "chain, so a `change_only` verdict no longer proves the carry "
              "was asked.")
        return 2

    gated = carry_is_flag_gated(tree)
    print("\n`%s` returns early when the flag is off: %s" % (CARRY, gated))
    if not gated:
        print("REFUSED: the carry is no longer gated on its flag, so the "
              "record tree's DEFAULT below says nothing about whether the "
              "carry acted in it.")
        return 2

    # ---- the two trees, and the POSITIVE CONTROL that they differ ---------
    was = flag_default(RECORD_TOOLS_COMMIT, "METER_CARRY")
    now = flag_default(None, "METER_CARRY")
    print("\nOMR_METER_CARRY default -- record tree %s: %r   today: %r"
          % (RECORD_TOOLS_COMMIT, was, now))
    if was is None:
        print("ABSTAINED: %s is not readable in this checkout, so the record's "
              "own tree cannot be characterised. Everything above still holds."
              % RECORD_TOOLS_COMMIT)
    elif was == now:
        print("⚠️ POSITIVE CONTROL FAILED: the two trees read the SAME default, "
              "so this check cannot tell a before-arm from an after-arm and "
              "its conclusion about the record would be vacuous.")
        return 2
    else:
        print("   -> the shared record is a BEFORE arm: the carry could not "
              "act in it at all.")

    census = record_reasons()
    if not census:
        print("\nABSTAINED: the shared record's reason table did not parse.")
        return 2
    fallback_reasons = {n.lstrip("_") for n in order if reach.get(n)}
    fallback_reasons.add("change_only")
    domain = sum(n for r, n in census.items() if r in fallback_reasons)
    total = sum(census.values())
    print("\nBREITKOPF BRAHMS 1 p0-3, per-system meter reasons: %s" % census)
    print("CARRY DOMAIN: %d of %d systems reach the carry rung."
          % (domain, total))
    if domain == 0:
        print("   -> a genuine reach zero.")
    else:
        print("   -> NOT a reach zero. The 2026-09-16 write-up's "
              "\"neither flag has a domain on this document\" is REFUTED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
