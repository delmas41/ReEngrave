"""Which quantities does a decision's CODE actually reach?

⚠️ THIS IS THE MECHANICAL SUBSTRATE OF THE AUDIT, AND IT IS NOT THE AUDIT.
It answers a narrow, decidable question -- *which `Q.*` names appear in the
call closure of this decision's function* -- and nothing else. Whether a
`checked_by` SENTENCE is performed is a semantic judgement a human makes by
reading; this only bounds it. A quantity that never appears in the closure
CANNOT be tested by that decision; a quantity that does appear may still be
read for some other purpose.

⚠️ `adjudicate.REGISTRY` is EMPTY on a bare import -- the decisions register
by decorator -- so `tools.omr.staged.adjudicators` must be imported first.
Four people have been caught by that, including two auditors auditing
vacuity, so this module imports it explicitly and ASSERTS the registry is
non-empty rather than reporting a clean tree over nothing.

The closure is transitive over module-level helpers inside the adjudicator
package (and `adjudicate` itself), because a check implemented in a private
helper is still performed -- attributing it to the helper would report the
declaring decision as inert when it is not.

Positive control (`--check`): the probe must find (a) at least one decision
whose closure reads at least one quantity, and (b) at least one DECLARED
`wants` entry that the closure never reaches -- the shape CLAUDE.md already
records for `adjudicate_clef` / `notehead_staff_position`. A scan that finds
neither is a scan that is not looking, and exits non-zero.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

import tools.omr.staged.adjudicators  # noqa: F401  -- registers every decision
from tools.omr.staged import adjudicate

#: Modules whose functions count as "inside" the decision -- a helper here is
#: part of the decision's own code, not a separate consumer.
_PKG_PREFIXES = ("tools.omr.staged.adjudicators", "tools.omr.staged.adjudicate")


def _is_inside(mod_name: str) -> bool:
    return any(mod_name == p or mod_name.startswith(p + ".")
               for p in _PKG_PREFIXES)


def _body_only(tree: ast.AST) -> ast.AST:
    """Strip the DECORATOR LIST before looking at anything.

    ⚠️ THIS IS THE WHOLE REASON THE FIRST RUN OF THIS PROBE WAS VACUOUS, AND
    CLAUDE.md ALREADY RECORDS THE SHAPE: `inspect.getsource` returns the
    decorator too, and `wants` LIVES IN THE DECORATOR -- so every declared
    input appeared to be "read by the body" and the tool reported that no
    declared input is ever unreached. That is the identical fault the tree's
    own inert-`wants` check hit ("it reported zero, because
    `inspect.getsource` includes the decorator and `wants` lives there").
    The probe's own positive control is what caught it.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.decorator_list = []
    return tree


def _quantities_in(tree: ast.AST) -> Set[str]:
    """Every `Q.NAME` referenced in this tree, as the quantity's VALUE."""
    found: Set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "Q"):
            val = getattr(adjudicate.Q, node.attr, None)
            if isinstance(val, str):
                found.add(val)
    return found


def _called_names(tree: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _closure(fn) -> Tuple[Set[str], Set[str]]:
    """(quantities reached, function names walked) over the call closure."""
    seen_fns: Set[str] = set()
    quantities: Set[str] = set()
    frontier = [fn]
    while frontier:
        f = frontier.pop()
        key = f"{getattr(f, '__module__', '?')}.{getattr(f, '__qualname__', '?')}"
        if key in seen_fns:
            continue
        seen_fns.add(key)
        try:
            src = inspect.getsource(f)
        except (OSError, TypeError):
            continue
        tree = _body_only(ast.parse(_dedent(src)))
        quantities |= _quantities_in(tree)
        mod = sys.modules.get(getattr(f, "__module__", ""), None)
        if mod is None:
            continue
        for called in _called_names(tree):
            target = getattr(mod, called, None)
            if target is None or not callable(target):
                continue
            tmod = getattr(target, "__module__", "")
            if _is_inside(tmod):
                frontier.append(target)
    return quantities, seen_fns


def _dedent(src: str) -> str:
    lines = src.split("\n")
    pad = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return "\n".join(l[pad:] for l in lines)


def audit() -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    for quantity, spec in adjudicate.REGISTRY.items():
        reached, walked = _closure(spec.fn)
        declared = set(spec.wants)
        rows[quantity] = {
            "name": spec.name,
            "scope": getattr(spec.scope, "value", str(spec.scope)),
            "checked_by": list(spec.checked_by),
            "wants": sorted(declared),
            "reached": sorted(reached),
            "declared_but_unreached": sorted(declared - reached),
            "reached_beyond_wants": sorted(reached - declared),
            "n_functions_walked": len(walked),
        }
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero unless the positive controls fire")
    args = ap.parse_args()

    if not adjudicate.REGISTRY:
        print("REFUSED: adjudicate.REGISTRY is EMPTY. The decisions register "
              "by decorator; import tools.omr.staged.adjudicators first.",
              file=sys.stderr)
        return 2

    rows = audit()
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        print(f"decisions registered: {len(rows)}")
        declaring = {q: r for q, r in rows.items() if r["checked_by"]}
        print(f"decisions declaring checked_by: {len(declaring)}")
        print(f"checked_by statements: "
              f"{sum(len(r['checked_by']) for r in declaring.values())}")
        print()
        for q, r in sorted(rows.items()):
            if not r["checked_by"]:
                continue
            print(f"{q}  ({r['name']}, scope={r['scope']}, "
                  f"{r['n_functions_walked']} fn walked)")
            print(f"    wants   : {', '.join(r['wants']) or '-'}")
            print(f"    reached : {', '.join(r['reached']) or '-'}")
            if r["declared_but_unreached"]:
                print(f"    ⚠️ DECLARED IN wants AND NEVER REACHED: "
                      f"{', '.join(r['declared_but_unreached'])}")
            print()

    # ── positive controls ────────────────────────────────────────────────
    any_reads = any(r["reached"] for r in rows.values())
    any_unreached = any(r["declared_but_unreached"] for r in rows.values())
    if args.check:
        if not any_reads:
            print("REFUSED: no decision reaches any quantity -- the AST walk "
                  "is not looking at the right thing.", file=sys.stderr)
            return 2
        if not any_unreached:
            print("REFUSED: no declared `wants` entry is unreached anywhere. "
                  "CLAUDE.md records at least one (adjudicate_clef / "
                  "notehead_staff_position); finding none means the closure "
                  "is over-wide and this tool cannot discriminate.",
                  file=sys.stderr)
            return 2
        print("positive controls: OK "
              f"(quantities are reached; {sum(bool(r['declared_but_unreached']) for r in rows.values())} "
              "decisions carry an unreached declared input)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
