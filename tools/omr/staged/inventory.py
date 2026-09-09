"""A DERIVED inventory of the staged pipeline's decisions.

⚠️ **NOTHING IN THIS MODULE IS TYPED BY HAND.** Every column is read out of
the code that runs: `adjudicate.REGISTRY` (populated by the `@decision`
decorator), `adjudicate.ORDER`, `evaluate.RULES` (`@rule`), `groups`'
redundancy declarations, `legacy.EXTRACTED_QUANTITIES`, and the AST of
`gather.py`. A hand-written decisions table is exactly the shape that rots --
this repo has three that did, including the one the 2026-09-09 handoff exists
to correct -- so the inventory is a script, the way `export_coverage` is.

    python3 -m tools.omr.staged.inventory              # the table
    python3 -m tools.omr.staged.inventory --json       # the same, as JSON
    python3 -m tools.omr.staged.inventory --check      # non-zero if broken
    python3 -m tools.omr.staged.inventory --run staged.json   # fold in a run

⚠️ **`--run` IS WHAT MAKES A SILENT DECISION VISIBLE.** A decision whose
`subjects_from` domain is empty on a page runs on ZERO subjects and therefore
writes no row of any kind -- neither decided nor abstained. That is not the
same fact as "it abstained", and without asking the registry what SHOULD have
appeared there is nothing in the record to notice. `no_row_at_all` is that
column. `adjudicate.NoDecisionsRegistered` states the same principle one level
up ("a stage that produces no verdicts because nothing was loaded is
indistinguishable from one that produced no verdicts because it had nothing to
decide"); this applies it per decision.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import pathlib
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from . import adjudicate as A
from . import consequences as _consequences  # noqa: F401  (registers rules)
from . import evaluate as E
from . import groups as G
from . import legacy as L
from .record import Q


# ─────────────────────────────────────────────────────────────────────────────
# Where a MEASUREMENT comes from: the AST of gather.py
# ─────────────────────────────────────────────────────────────────────────────


def _gather_sites() -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """`({quantity: [gather fn]}, {quantity: [gather fn]})` off `gather.py`.

    The first map is the DIRECT sites -- `log.observe(subject, Q.X, ...)` with
    `Q.X` written literally at the call. The second is INDIRECT: a `Q.X` named
    anywhere inside a gather function that makes such a call at all.

    ⚠️ THE SPLIT IS NOT PEDANTRY, AND THE FIRST VERSION OF THIS CHECK WAS
    WRONG WITHOUT IT. `gather_cv_lines` observes both its quantities through
    `for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams"))`, so
    a literal-argument matcher reports `stem` as gathered by nothing and
    `duration` as unsatisfiable -- a false alarm about the one rung Phase 4f
    moved to classical CV on purpose. Indirect is weaker evidence and is
    labelled as such; absent from BOTH maps is the real finding.
    """
    path = pathlib.Path(__file__).with_name("gather.py")
    tree = ast.parse(path.read_text())
    direct: Dict[str, Set[str]] = {}
    indirect: Dict[str, Set[str]] = {}

    class V(ast.NodeVisitor):
        def __init__(self) -> None:
            self.fn: List[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.fn.append(node.name)
            names = {a.attr for a in ast.walk(node)
                     if isinstance(a, ast.Attribute)
                     and isinstance(a.value, ast.Name) and a.value.id == "Q"}
            records = any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr in ("observe", "abstain", "decline")
                for c in ast.walk(node))
            if records:
                for attr in names:
                    q = getattr(Q, attr, None)
                    if isinstance(q, str):
                        indirect.setdefault(q, set()).add(node.name)
            self.generic_visit(node)
            self.fn.pop()

        def visit_Call(self, node: ast.Call) -> None:
            f = node.func
            if (isinstance(f, ast.Attribute)
                    and f.attr in ("observe", "abstain", "decline")
                    and len(node.args) >= 2):
                q = node.args[1]
                if (isinstance(q, ast.Attribute)
                        and isinstance(q.value, ast.Name) and q.value.id == "Q"):
                    name = getattr(Q, q.attr, None)
                    if isinstance(name, str):
                        direct.setdefault(name, set()).add(
                            self.fn[0] if self.fn else "<module>")
            self.generic_visit(node)

    V().visit(tree)
    return ({k: sorted(v) for k, v in sorted(direct.items())},
            {k: sorted(v) for k, v in sorted(indirect.items())})


# ─────────────────────────────────────────────────────────────────────────────
# Which legacy module a decision replaces
# ─────────────────────────────────────────────────────────────────────────────


def _legacy_modules() -> List[str]:
    d = pathlib.Path(__file__).resolve().parent.parent      # tools/omr
    return sorted(p.stem for p in d.glob("*.py") if p.stem != "__init__")


def _legacy_for(fn: Any, mods: List[str]) -> Dict[str, List[str]]:
    """What the decision itself says about the code it stands in for.

    Three DERIVED signals, kept apart because they mean different things:

    * `imports`   -- a legacy module the decision's own body imports. A real
                     code dependency: the staged decision REUSES that rung.
    * `names`     -- a legacy module named in the decision's own source
                     (decorator, docstring or body) as `module.thing` or
                     `module.py`. What the decision says it stands in for.
    * `in_module` -- named elsewhere in the same adjudicator FILE. Context,
                     not attribution: an adjudicator file holds several
                     decisions and a name in one docstring is not evidence
                     about its neighbour.
    """
    src = inspect.getsource(fn)
    file_src = pathlib.Path(inspect.getfile(fn)).read_text()
    pat = lambda m: re.compile(r"\b" + re.escape(m) + r"\.(?:py\b|[A-Za-z_])")

    imports: Set[str] = set()
    for node in ast.walk(ast.parse(_dedent(src))):
        if isinstance(node, ast.ImportFrom) and node.module:
            head = node.module.split(".")[0]
            if head in mods:
                imports.add(head)

    own = [m for m in mods if pat(m).search(src)]
    wider = [m for m in mods if pat(m).search(file_src)]
    return {
        "imports": sorted(imports),
        "names": sorted(set(own) | imports),
        "in_module": sorted(set(wider) - set(own) - imports),
    }


def _never_read(spec) -> List[str]:
    """`wants` entries whose `Q.` name appears nowhere in the decision's body.

    Deliberately CONSERVATIVE — any mention counts as a read, including one
    inside a loop tuple — so what it reports is a declaration the code does
    not touch at all.
    """
    if spec.stub:
        return []                       # a stub reads nothing, by definition
    try:
        src = inspect.getsource(spec.fn)
    except OSError:                                          # noqa: BLE001
        return []
    # ⚠️ THE DECORATOR MUST BE EXCLUDED, AND LEAVING IT IN MADE THIS CHECK
    # REPORT ZERO. `inspect.getsource` includes decorator lines, and `wants`
    # lives there — so every declared quantity "appeared in the source" and
    # nothing could ever be flagged. A zero is a suspect, not a result.
    tree = ast.parse(_dedent(src))
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == spec.name), None)
    if fn is None:
        return []
    # ⚠️ AND THE MODULE'S OWN HELPERS COUNT AS THE DECISION READING.
    # `adjudicate_clef` asks for `clef_glyph` through `_detector_terms(ev)`;
    # a check that looked only at the decision body reported six decisions
    # reading nothing they declared, which is a measure of code STYLE, not of
    # inertness. Followed to depth 3 within the decision's own module.
    mod = ast.parse(pathlib.Path(inspect.getfile(spec.fn)).read_text())
    helpers = {n.name: n for n in ast.walk(mod)
               if isinstance(n, ast.FunctionDef)}
    names: Set[str] = set()
    seen: Set[str] = set()
    frontier = [fn]
    for _ in range(3):
        nxt: List[ast.AST] = []
        for node in frontier:
            body = node.body if isinstance(node, ast.FunctionDef) else [node]
            for stmt in body:
                for a in ast.walk(stmt):
                    if (isinstance(a, ast.Attribute)
                            and isinstance(a.value, ast.Name)
                            and a.value.id == "Q"):
                        names.add(a.attr)
                    if isinstance(a, ast.Call):
                        f = a.func
                        called = (f.id if isinstance(f, ast.Name)
                                  else f.attr if isinstance(f, ast.Attribute)
                                  else None)
                        if called in helpers and called not in seen:
                            seen.add(called)
                            nxt.append(helpers[called])
        frontier = nxt
        if not frontier:
            break
    read = {getattr(Q, n) for n in names if isinstance(getattr(Q, n, None), str)}
    return [w for w in spec.wants if w not in read]


def _dedent(src: str) -> str:
    lines = src.splitlines()
    pad = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return "\n".join(l[pad:] for l in lines)


# ─────────────────────────────────────────────────────────────────────────────
# The inventory
# ─────────────────────────────────────────────────────────────────────────────


def build() -> Dict[str, Any]:
    A._ensure_decisions()
    E._ensure_rules()
    G._ensure_declarations()

    sites, indirect = _gather_sites()
    mods = _legacy_modules()
    order = list(A.ORDER)
    rank = {q: i for i, q in enumerate(order)}

    rows: List[Dict[str, Any]] = []
    for quantity in order:
        spec = A.REGISTRY.get(quantity)
        if spec is None:                      # named in ORDER, never registered
            rows.append({"quantity": quantity, "registered": False})
            continue
        consumes = []
        for w in spec.wants:
            # ⚠️ A quantity can be BOTH, and treating them as exclusive is a
            # false alarm: `system_staff_count` is observed by
            # `gather_measures` AND decided by `adjudicate_system_staff_count`,
            # so calling it a pure verdict makes `system_membership` -- which
            # runs first and reads the OBSERVATION -- look like a dependency
            # cycle. Only a wants entry that is ONLY a later verdict is one.
            gathered = w in sites or w in indirect
            decided = w in A.REGISTRY
            kind = ("both" if gathered and decided else
                    "verdict" if decided else
                    "measurement" if gathered else "UNSATISFIABLE")
            consumes.append({
                "quantity": w,
                "kind": kind,
                "gathered_by": sites.get(w, []),
                "gathered_indirectly_by": [f for f in indirect.get(w, [])
                                           if f not in sites.get(w, [])],
            })
        rows.append({
            "quantity": quantity,
            "registered": True,
            "decision": spec.name,
            "module": inspect.getmodule(spec.fn).__name__,
            "stub": spec.stub,
            "scope": spec.scope.value if hasattr(spec.scope, "value") else str(spec.scope),
            "domain": spec.subjects_from,
            "mode": spec.mode.value if hasattr(spec.mode, "value") else str(spec.mode),
            "margin_floor": spec.margin_floor,
            "revises": spec.revises,
            "excludes_tiers": list(spec.excludes_tiers),
            "consumes": consumes,
            # ⚠️ A `wants` entry the body never mentions is INERT: the harness
            # fills `missing`/`declined` only for quantities the decision
            # actually QUERIED, so a declaration nothing reads records
            # nothing and cannot be told from one that is read and always
            # present. Found by a test that asserted the opposite and failed.
            "declared_and_never_read": _never_read(spec),
            "produces": {
                "quantity": quantity,
                "causes": [r.effect for r in E.RULES if r.cause == quantity],
                # ⚠️ self excluded: a quantity that is both observed and
                # adjudicated (`staff_ordinal`, `system_staff_count`) lists
                # itself in `wants`, which is the decision reading its own
                # MEASUREMENT, not a decision consuming its own verdict.
                "consumed_by": sorted(
                    q for q, s in A.REGISTRY.items()
                    if quantity in s.wants and q != quantity),
            },
            "reasons": list(spec.reasons),
            "checkable": spec.checkable.value,
            "checked_by": list(spec.checked_by),
            "implicates": list(spec.implicates),
            "composed_from": list(spec.composed_from),
            "readings": list(A.READINGS.get(quantity, ())),
            "legacy": _legacy_for(spec.fn, mods),
            "legacy_decides_it": quantity in L.EXTRACTED_QUANTITIES,
            "witnessed_by": sorted(
                r.name for r in G.REDUNDANCIES if r.quantity == quantity),
        })

    consequence_rows = [{
        "consequence": r.consequence.value if hasattr(r.consequence, "value")
                       else str(r.consequence),
        "cause": r.cause, "effect": r.effect,
        "scope": r.scope.value if hasattr(r.scope, "value") else str(r.scope),
        "stub": r.stub, "bound": r.bound,
    } for r in E.RULES]

    return {
        "generated_by": "python3 -m tools.omr.staged.inventory",
        "n_decisions": len(order),
        "decisions": rows,
        "consequences": consequence_rows,
        "problems": _problems(rows, order, rank, sites),
    }


def _problems(rows: List[Dict[str, Any]], order: List[str],
              rank: Dict[str, int], sites: Dict[str, List[str]]) -> List[str]:
    """The teeth. Each of these is a fact the inventory can prove wrong.

    ⚠️ These are DERIVED invariants, not style rules. Every one of them is a
    way for a decision to be silently unreachable or unsatisfiable -- the
    shape that produced `fingering3`, `dynamicLetterF` and every other
    "detected then dropped" bug this repo has paid for.
    """
    out: List[str] = []

    registered = set(A.REGISTRY)
    in_order = set(order)
    for q in sorted(registered - in_order):
        out.append(f"registered but NOT IN ORDER, so it never runs: {q}")
    for q in sorted(in_order - registered):
        out.append(f"named in ORDER but no adjudicator registered: {q}")

    for row in rows:
        if not row.get("registered"):
            continue
        q = row["quantity"]
        for c in row["consumes"]:
            if c["kind"] == "UNSATISFIABLE":
                out.append(
                    f"{q} wants {c['quantity']!r}, which no gather site "
                    f"observes and no decision produces")
            elif (c["kind"] == "verdict"
                  and rank.get(c["quantity"], -1) > rank[q]):
                out.append(
                    f"{q} wants the VERDICT {c['quantity']!r}, which ORDER "
                    f"runs AFTER it -- it will always read None")
        # ⚠️ A STUB WHOSE INPUT IS NEVER GATHERED IS TWO GAPS, NOT ONE.
        # Filling the adjudicator would still produce nothing, because the
        # measurement it decides over is not in the log. The stub declaration
        # says "this decision is not written"; it does not say "and the page
        # is never read for it either".
        if row["stub"]:
            starved = [c["quantity"] for c in row["consumes"]
                       if c["kind"] == "UNSATISFIABLE"]
            if starved:
                out.append(
                    f"{q} is a declared STUB whose input is ALSO never "
                    f"gathered ({', '.join(starved)}) -- implementing the "
                    f"adjudicator alone would still produce nothing")
        for w in row["declared_and_never_read"]:
            out.append(
                f"{q} declares {w!r} in `wants` and never reads it — the "
                f"declaration is inert: nothing records it as missing or "
                f"declined")
        d = row["domain"]
        if d and d not in sites and d not in indirect and d not in A.REGISTRY:
            out.append(
                f"{q}'s domain {d!r} is never produced, so it can never have "
                f"a subject")

    for r in E.RULES:
        if r.cause not in A.REGISTRY:
            out.append(f"consequence {r.effect} is caused by {r.cause!r}, "
                       f"which no decision produces")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Folding in a real run
# ─────────────────────────────────────────────────────────────────────────────


def with_run(inv: Dict[str, Any], run_path: str) -> Dict[str, Any]:
    """Annotate each decision with what it actually did on one page.

    ⚠️ THE COLUMN THAT MATTERS IS `no_row_at_all`. A decision with an empty
    domain writes nothing, and nothing in the run record says it was supposed
    to. Reading the registry against the record is the only way to see it.
    """
    result = json.loads(pathlib.Path(run_path).read_text())
    summary = result.get("summary", {})
    silent: List[str] = []
    for row in inv["decisions"]:
        q = row["quantity"]
        seen = summary.get(q)
        row["run"] = seen
        row["run_no_row_at_all"] = seen is None
        if seen is None:
            silent.append(q)
            row["run_domain_rows"] = (summary.get(row["domain"])
                                      if row.get("domain") else None)
    inv["run"] = {
        "path": run_path,
        "no_row_at_all": silent,
        "declared_stubs": sorted(A.stubs()),
    }
    return inv


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────


def render(inv: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# The staged pipeline's {inv['n_decisions']} decisions")
    lines.append("")
    lines.append("Generated by `python3 -m tools.omr.staged.inventory` — "
                 "every column derived from the code, none typed.")
    lines.append("")
    head = ("| # | quantity | decision | scope | domain | mode | state | "
            "consumes | produces → | legacy named | checkable |")
    lines.append(head)
    lines.append("|--:|---|---|---|---|---|---|---|---|---|---|")
    for i, row in enumerate(inv["decisions"]):
        if not row.get("registered"):
            lines.append(f"| {i} | {row['quantity']} | **NOT REGISTERED** "
                         f"| | | | | | | | |")
            continue
        state = "STUB" if row["stub"] else "real"
        if row.get("run_no_row_at_all"):
            state += " · no row"
        consumes = ", ".join(
            f"{c['quantity']}"
            f"{'*' if c['kind'] in ('verdict', 'both') else ''}"
            f"{'!' if c['kind'] == 'UNSATISFIABLE' else ''}"
            for c in row["consumes"]) or "—"
        produces = ", ".join(row["produces"]["consumed_by"]
                             + row["produces"]["causes"]) or "—"
        legacy = ", ".join(row["legacy"]["names"]) or "—"
        lines.append(
            f"| {i} | `{row['quantity']}` | `{row['decision']}` "
            f"| {row['scope']} | {row['domain'] or 'all'} | {row['mode']} "
            f"| {state} | {consumes} | {produces} | {legacy} "
            f"| {row['checkable']} |")
    lines.append("")
    lines.append("`*` = also produced as a VERDICT by another decision; "
                 "`!` = **never gathered and never decided — this input does "
                 "not exist in the log at all**; everything else is a "
                 "MEASUREMENT gathered off the page.")
    lines.append("")

    lines.append("## Consequences (EVALUATE)")
    lines.append("")
    lines.append("| consequence | cause → effect | scope | state |")
    lines.append("|---|---|---|---|")
    for c in inv["consequences"]:
        lines.append(f"| `{c['consequence']}` | `{c['cause']}` → "
                     f"`{c['effect']}` | {c['scope']} | "
                     f"{'STUB' if c['stub'] else 'real'} |")
    lines.append("")

    stubs = [r["quantity"] for r in inv["decisions"] if r.get("stub")]
    lines.append(f"## Declared stubs: {len(stubs)}")
    lines.append("")
    lines.append(", ".join(f"`{s}`" for s in stubs) or "none")
    lines.append("")

    run = inv.get("run")
    if run:
        lines.append(f"## On one real page (`{run['path']}`)")
        lines.append("")
        lines.append("⚠️ A decision that wrote **no row of any kind** is not "
                     "the same as one that abstained: an abstention says why, "
                     "and this says nothing.")
        lines.append("")
        if run["no_row_at_all"]:
            for q in run["no_row_at_all"]:
                row = next(r for r in inv["decisions"] if r["quantity"] == q)
                dom = row.get("domain")
                got = row.get("run_domain_rows")
                lines.append(
                    f"- `{q}` — domain `{dom or 'all subjects'}`, and the run "
                    f"holds {got if got is not None else 'NO'} rows of it")
        else:
            lines.append("- every decision wrote at least one row")
        lines.append("")

    if inv["problems"]:
        lines.append("## ⚠️ PROBLEMS")
        lines.append("")
        for p in inv["problems"]:
            lines.append(f"- {p}")
    else:
        lines.append("## Problems: none")
        lines.append("")
        lines.append("Checked: every registered decision is in `ORDER` and "
                     "vice versa; every `wants` entry is produced by some "
                     "gather site or some decision; every wanted VERDICT is "
                     "decided earlier in `ORDER`; every `subjects_from` domain "
                     "is produced by something; every consequence's cause is a "
                     "registered decision.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if any derived invariant is broken")
    ap.add_argument("--run", default=None,
                    help="a staged run JSON, to fold in what each decision "
                         "actually did")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    inv = build()
    if args.run:
        inv = with_run(inv, args.run)

    text = json.dumps(inv, indent=2, default=str) if args.json else render(inv)
    if args.out:
        pathlib.Path(args.out).write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)

    if inv["problems"]:
        for p in inv["problems"]:
            print(f"⚠️ {p}", file=sys.stderr)
        if args.check:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
