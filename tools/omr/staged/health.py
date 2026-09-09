"""Per-stage "is this working" — read off the tests that already exist.

Sean, 2026-09-08:

    "The tests currently may help us with if our tools and stages are working
    but I am not worried about it looking better or worse."

So this asks one question and not the other. For every stage and every
decision: **is there a test that says it DECIDES what it can, a test that says
it ABSTAINS when it cannot, and a test that says it RECORDS both?** Those
three are the contract `adjudicate.Ruling` states, and a decision missing one
of them is untested in a way a passing suite cannot show.

    python3 -m tools.omr.staged.health              # the table
    python3 -m tools.omr.staged.health --run        # ...and run the suite
    python3 -m tools.omr.staged.health --check      # non-zero on an empty cell

⚠️ **THE SHAPE CLASSIFIER IS TEXTUAL AND WILL MISCOUNT.** It reads each test
function's own body for the words an assertion of that shape uses
(`Outcome.DECIDED`, `ABSTAIN.`, `.considered`, …). A test that asserts through
a helper, or in a style the list does not name, is undercounted. **Its job is
to point at the EMPTY cells, not to grade the full ones** — and every empty
cell it reports should be confirmed with one `grep` before it is believed.
Both zeros it found on 2026-09-09 were confirmed that way and both were real.

⚠️ **AND WHERE A TEST LIVES IS PART OF THE ANSWER.** A decision whose only
coverage comes from a DOWNSTREAM stage's tests is not tested: those tests
SUPPLY its verdict as a fixture and assert about their own stage.
`part_partition` is exactly that today — every test naming it is in
`test_staged_export.py`, which hands the join in.
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from . import adjudicate as A
from . import consequences as _consequences  # noqa: F401
from . import evaluate as E


TESTS = pathlib.Path(__file__).resolve().parent.parent / "tests"

#: Which staged module a test importing it is exercising. A test importing
#: several is attributed to all of them: `test_staged_pipeline` genuinely
#: covers the whole chain and pretending otherwise would flatter one stage.
STAGE_OF_MODULE: Dict[str, str] = {
    "gather": "GATHER",
    "adjudicate": "ADJUDICATE",
    "adjudicators": "ADJUDICATE",
    "clef": "ADJUDICATE",
    "rhythm": "ADJUDICATE",
    "evaluate": "EVALUATE",
    "consequences": "EVALUATE",
    "groups": "GROUPS",
    "record": "RECORD",
    "record_coverage": "RECORD",
    "export": "EXPORT",
    "inventory": "META",
    "pipeline": "PIPELINE",
    "legacy": "PIPELINE",
}

#: What an assertion of each shape says, in the words tests here use.
#: ⚠️ Textual, and deliberately readable rather than clever: someone reading a
#: zero has to be able to check what was looked for.
SHAPE_MARKERS: Dict[str, Tuple[str, ...]] = {
    "decides": ("Outcome.DECIDED", '"decided"', "'decided'", "DECIDED",
                "assertIsNotNone"),
    "abstains": ("Outcome.ABSTAINED", "Outcome.NARROWED", "ABSTAIN.",
                 "abstain", "margin_below_floor", ".reason", "assertIsNone"),
    "records": (".considered", ".used", ".missing", ".declined", ".excluded",
                ".correlated", ".basis", ".detail", ".candidates", "to_json",
                "coverage"),
}


def _quantities(node: ast.AST) -> Set[str]:
    return {a.attr for a in ast.walk(node)
            if isinstance(a, ast.Attribute)
            and isinstance(a.value, ast.Name) and a.value.id == "Q"}


def _calls(node: ast.AST) -> Set[str]:
    out: Set[str] = set()
    for c in ast.walk(node):
        if not isinstance(c, ast.Call):
            continue
        f = c.func
        if isinstance(f, ast.Name):
            out.add(f.id)
        elif isinstance(f, ast.Attribute):
            out.add(f.attr)
    return out


def scan() -> List[Dict[str, Any]]:
    A._ensure_decisions()
    """One row per test function, with the stages and decisions it touches."""
    rows: List[Dict[str, Any]] = []
    for path in sorted(TESTS.glob("test_staged_*.py")):
        src = path.read_text()
        tree = ast.parse(src)
        lines = src.splitlines()

        stages: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "staged" not in node.module:
                    continue
                names = [node.module.split(".")[-1]] + [a.name for a in node.names]
                for n in names:
                    if n in STAGE_OF_MODULE:
                        stages.add(STAGE_OF_MODULE[n])

        # ⚠️ Helpers are followed ONE level (and their callees one more),
        # because these suites build a `Log` in a `_note` / `_triplet` helper
        # and the quantity is named there. Without it the attribution is a
        # measure of test STYLE rather than of coverage.
        helpers = {n.name: (_quantities(n), _calls(n))
                   for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef)
                    and node.name.startswith("test")):
                continue
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            qs = _quantities(node)
            for c in _calls(node):
                if c in helpers and c != node.name:
                    hq, hc = helpers[c]
                    qs |= hq
                    for c2 in hc:
                        if c2 in helpers:
                            qs |= helpers[c2][0]
            # ⚠️ A TEST CAN NAME ITS SUBJECTS DYNAMICALLY, and a static
            # scanner cannot see it. `test_each_stub_abstains_with_...`
            # iterates `adjudicate.stubs()` and never writes `Q.ARC_OWNER`,
            # so all six stubs read as "named by no test" while one test was
            # exercising every one of them. Iterating `stubs()` IS naming
            # them, so that one iterator is resolved.
            #
            # ⚠️⚠️ AND `REGISTRY` / `ORDER` ARE DELIBERATELY *NOT* RESOLVED
            # THE SAME WAY, BECAUSE TRYING IT EMPTIED THE REPORT. The
            # discipline tests iterate the whole registry to assert
            # declaration properties, so crediting them made every decision
            # look covered in every shape and "EMPTY CELLS" went to none --
            # a check that cannot fail. `stubs()` is bounded (six decisions,
            # one asserted behaviour); the registry is not.
            if "stubs()" in body:
                qs |= {q.upper() for q in A.stubs()}
            rows.append({
                "file": path.name,
                "test": node.name,
                "stages": sorted(stages),
                "quantities": sorted(qs),
                "shapes": [s for s, keys in SHAPE_MARKERS.items()
                           if any(k in body for k in keys)],
            })
    return rows


def build() -> Dict[str, Any]:
    A._ensure_decisions()
    E._ensure_rules()
    rows = scan()

    by_stage: Dict[str, Dict[str, Any]] = collections.defaultdict(
        lambda: {"tests": 0, "files": set()})
    for r in rows:
        for s in r["stages"]:
            by_stage[s]["tests"] += 1
            by_stage[s]["files"].add(r["file"])

    per: Dict[str, Dict[str, Any]] = {}
    for quantity in A.ORDER:
        spec = A.REGISTRY[quantity]
        attr = quantity.upper()
        shapes: Dict[str, List[str]] = {s: [] for s in SHAPE_MARKERS}
        files: Set[str] = set()
        for r in rows:
            if attr not in r["quantities"]:
                continue
            files.add(r["file"])
            for s in r["shapes"]:
                shapes[s].append(f"{r['file']}::{r['test']}")
        per[quantity] = {
            "stub": spec.stub,
            "decides": len(shapes["decides"]),
            "abstains": len(shapes["abstains"]),
            "records": len(shapes["records"]),
            "files": sorted(files),
            "tests": sorted({t.split("::")[1] for v in shapes.values()
                             for t in v}),
        }

    return {
        "n_tests": len(rows),
        "by_stage": {k: {"tests": v["tests"], "files": sorted(v["files"])}
                     for k, v in sorted(by_stage.items())},
        "per_decision": per,
        "problems": _problems(per),
    }


#: ⚠️ A stub is EXPECTED to have no `decides` test — there is nothing to
#: decide — so it is exempt from that one column and from nothing else. It
#: should still have a test saying it abstains `not_implemented`, because that
#: is the behaviour `stub=True` promises.
def _problems(per: Dict[str, Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for quantity, row in per.items():
        if row["decides"] == 0 and row["abstains"] == 0 and row["records"] == 0:
            out.append(f"{quantity}: NO staged test names it at all")
            continue
        if not row["stub"] and row["decides"] == 0:
            out.append(f"{quantity}: no test asserts it DECIDES")
        if row["abstains"] == 0:
            out.append(f"{quantity}: no test asserts it ABSTAINS"
                       + (" (`stub=True` promises `not_implemented`)"
                          if row["stub"] else ""))
        if row["records"] == 0:
            out.append(f"{quantity}: no test asserts what it RECORDS "
                       f"(considered / used / missing / declined / detail)")
        # ⚠️ Coverage from a DOWNSTREAM stage is not coverage: those tests
        # hand this decision's verdict in as a fixture.
        own = [f for f in row["files"]
               if f not in ("test_staged_export.py", "test_staged_inventory.py")]
        if row["files"] and not own:
            out.append(f"{quantity}: named ONLY by downstream tests "
                       f"({', '.join(row['files'])}), which supply its verdict "
                       f"rather than exercising it")
    return out


def run_suite() -> Dict[str, Any]:
    """Run the staged tests and report per file. "Is this stage working"."""
    out: Dict[str, Any] = {}
    for path in sorted(TESTS.glob("test_staged_*.py")):
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(path), "-q"],
            capture_output=True, text=True,
            cwd=str(pathlib.Path(__file__).resolve().parents[3]))
        tail = [l for l in proc.stdout.splitlines() if "passed" in l or "failed" in l]
        out[path.name] = {"returncode": proc.returncode,
                          "summary": tail[-1] if tail else "?"}
    return out


def render(health: Dict[str, Any]) -> str:
    lines = [f"# Staged pipeline health — {health['n_tests']} test functions",
             "",
             "Derived from the tests that already exist. It asks whether each "
             "stage and decision is WORKING, never whether it scores well.",
             "",
             "## Per stage", "",
             "| stage | tests | files |", "|---|--:|---|"]
    for stage, row in health["by_stage"].items():
        lines.append(f"| {stage} | {row['tests']} | "
                     f"{', '.join(f'`{f}`' for f in row['files'])} |")
    lines += ["", "## Per decision — decides / abstains / records", "",
              "| decision | decides | abstains | records | tested in |",
              "|---|--:|--:|--:|---|"]
    for quantity, row in health["per_decision"].items():
        mark = lambda n: str(n) if n else "**0**"
        stub = " *(stub)*" if row["stub"] else ""
        lines.append(
            f"| `{quantity}`{stub} | {mark(row['decides'])} "
            f"| {mark(row['abstains'])} | {mark(row['records'])} "
            f"| {', '.join(f'`{f}`' for f in row['files']) or '—'} |")
    lines += ["", "## Consequences (EVALUATE)", "",
              "| consequence | cause → effect | state |", "|---|---|---|"]
    for r in E.RULES:
        lines.append(f"| `{r.consequence.value}` | `{r.cause}` → `{r.effect}` "
                     f"| {'STUB' if r.stub else 'real'} |")
    lines.append("")
    if health.get("suite"):
        lines += ["## The suite", "", "| file | result |", "|---|---|"]
        for name, row in health["suite"].items():
            lines.append(f"| `{name}` | {row['summary']} |")
        lines.append("")
    lines += ["## ⚠️ EMPTY CELLS", ""]
    if health["problems"]:
        lines += [f"- {p}" for p in health["problems"]]
    else:
        lines.append("none")
    lines.append("")
    lines.append("⚠️ The shape classifier is TEXTUAL and undercounts. Confirm "
                 "any zero with one `grep` before believing it.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--run", action="store_true",
                    help="also run each staged test file and report it")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    health = build()
    if args.run:
        health["suite"] = run_suite()

    text = (json.dumps(health, indent=2, default=str) if args.json
            else render(health))
    if args.out:
        pathlib.Path(args.out).write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)

    for p in health["problems"]:
        print(f"⚠️ {p}", file=sys.stderr)
    if args.check and health["problems"]:
        return 1
    if args.run and any(r["returncode"] for r in health["suite"].values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
