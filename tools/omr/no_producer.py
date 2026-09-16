"""A parameter threaded end to end with NO PRODUCER.

⚠️ The fault this looks for, stated once: a function argument that every layer
dutifully declares and forwards, and that **nothing anywhere actually
supplies**. It is not a dead parameter (nothing reads it) and not an unused
one (nobody passes it) — it is READ, it is PASSED, and every value passed is
itself another unsupplied parameter one layer up. The chain bottoms out at
`None`, the consumer takes its "I have nothing" branch, and the abstention it
files reads exactly like an honest one.

Found twice in two days, both times by accident:

1. `pdf_path` — `pipeline.run_staged` took it, rasterised with it and DROPPED
   it, so `gather_margin_labels` filed `not_implemented: "no pdf_path supplied
   to gather()"` on 75 of 75 staves on every staged run this repo had ever
   made. Five links later: 12 staff-systems joined to the wrong instrument.
   Fixed in `3a725f07`.
2. `roster` — `pipeline.py` threads it through both entry points and
   `staged/__main__.py` has no roster argument at all, so nothing can supply
   one.

⚠️⚠️ **THIS IS DERIVED FROM THE AST AND MUST STAY THAT WAY.** A hand-written
list of parameters to watch is what `export_coverage.VISIBLE` was (19 names,
reported 5, blind to 15) and what `ARITY_FIELDS` was (incomplete the day it
landed). The walk below knows no parameter names; both known instances are
found without a hint, and the test suite asserts exactly that.

Run it:

    python3 -m tools.omr.no_producer            # the funnel and the findings
    python3 -m tools.omr.no_producer --check    # non-zero on an unrecorded finding
    python3 -m tools.omr.no_producer --json

⚠️ **How it differs from the two instruments that already exist.**
`staged/inventory.py --check` and `staged/gather_coverage.py` ask about the
STAGED DECISION REGISTRY: a quantity a decision declares in `wants` and never
reads, or a quantity no gatherer observes. Both are questions about one
registry's own declarations, and neither can see a plain Python parameter.
This asks about the CALL GRAPH, over the whole of `tools/`, and knows nothing
about the registry. `pdf_path` was invisible to both — `gather_margin_labels`
was reading its input and reporting honestly; the value never arrived.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

# A node in the supply graph: one PARAMETER NAME on one FUNCTION NAME.
#
# ⚠️ Keyed by NAME, not by a resolved definition, and the direction of that
# imprecision is the reason it is acceptable: two functions sharing a name
# have their producers POOLED, so a collision can only mark a node supplied
# that is not — it can HIDE a finding, never invent one. A check whose
# imprecision runs toward silence is one whose findings can be trusted.
ParamKey = Tuple[str, str]  # (function name, parameter name)

_SKIP_DIR_PARTS = {
    "data", "node_modules", ".venv-surya", ".venv-omrned", ".git",
    "__pycache__", "fixtures", "out",
}


def _is_test_path(path: Path) -> bool:
    return "tests" in path.parts or path.name.startswith("test_")


@dataclass
class ParamDef:
    """One declaration of a parameter."""
    path: Path
    lineno: int
    func: str
    param: str
    defaults_to_none: bool
    has_default: bool


@dataclass
class Supply:
    """One call site that passes something for a parameter."""
    path: Path
    lineno: int
    func: str          # callee name
    param: str
    how: str           # "keyword" | "positional"
    forwarded_from: Optional[ParamKey]  # set iff the value is a bare enclosing param
    expr: str          # a short rendering, for the report


@dataclass
class Finding:
    """One CHAIN: a set of parameter nodes joined by forwarding, none supplied.

    ⚠️ The chain is the unit, not the parameter, because the fault is about a
    value travelling: `run_staged(roster)` on its own is an ordinary optional
    argument, and `gather_external(roster)` on its own is a function with a
    sensible default. What makes it a finding is that one hands to the other
    and NOBODY starts the chain.
    """
    keys: List[ParamKey]
    defs: Dict[ParamKey, List[ParamDef]]
    edges: List[Supply]
    guards: Dict[ParamKey, List[str]] = field(default_factory=dict)
    test_only_supplies: List[Supply] = field(default_factory=list)

    @property
    def param(self) -> str:
        return self.keys[0][1]

    @property
    def name(self) -> str:
        return f"{self.param}: " + " -> ".join(f"{f}()" for f, _ in self.keys)

    @property
    def ident(self) -> str:
        """A stable key for the inventory: the parameter and its chain's root."""
        return f"{self.keys[0][0]}.{self.param}"


def _local_packages(roots: Sequence[Path]) -> Set[str]:
    """Top-level import names that live INSIDE the scan.

    ⚠️ Needed because the call graph is keyed by NAME: `asyncio.gather(*tasks)`
    in `backend/modules/claude_vision.py` matched `staged.gather` by its last
    segment and its `*tasks` splat marked every one of that function's
    parameters supplied — silencing BOTH live findings. Measured, not
    imagined: adding `backend/` to the scan took the report from 2 to 0 before
    this existed. A name bound by importing a module we do not scan is not our
    function.
    """
    names: Set[str] = set()
    for root in roots:
        base = root if root.is_dir() else root.parent
        names.add(base.name)
        for child in (base.iterdir() if base.is_dir() else []):
            if child.is_dir() and (child / "__init__.py").exists():
                names.add(child.name)
            elif child.suffix == ".py":
                names.add(child.stem)
    return names


class _Walker(ast.NodeVisitor):
    def __init__(self, path: Path, local_packages: Optional[Set[str]] = None) -> None:
        self.path = path
        self._local = local_packages or set()
        self._foreign: Set[str] = set()
        self.defs: List[ParamDef] = []
        self.supplies: List[Supply] = []
        self.guards: List[Tuple[ParamKey, str]] = []
        # stack of (function name, set of its parameter names)
        self._stack: List[Tuple[str, Set[str]]] = []

    def visit(self, node):  # type: ignore[override]
        if isinstance(node, ast.Module):
            self._collect_foreign(node)
        return super().visit(node)

    def _collect_foreign(self, tree: ast.Module) -> None:
        """Names in this file that refer to code OUTSIDE the scan."""
        for sub in ast.walk(tree):
            if isinstance(sub, ast.Import):
                for a in sub.names:
                    top = a.name.split(".")[0]
                    if top not in self._local:
                        self._foreign.add(a.asname or top)
            elif isinstance(sub, ast.ImportFrom):
                top = (sub.module or "").split(".")[0]
                if sub.level == 0 and top and top not in self._local:
                    for a in sub.names:
                        self._foreign.add(a.asname or a.name)

    # -- declarations ----------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        a = node.args
        positional = list(a.posonlyargs) + list(a.args)
        ordered = positional + list(a.kwonlyargs)
        defaults: Dict[str, Optional[ast.expr]] = {}
        if a.defaults:
            for arg, d in zip(positional[len(positional) - len(a.defaults):], a.defaults):
                defaults[arg.arg] = d
        for arg, d in zip(a.kwonlyargs, a.kw_defaults):
            if d is not None:
                defaults[arg.arg] = d
        for arg in ordered:
            d = defaults.get(arg.arg)
            self.defs.append(ParamDef(
                path=self.path, lineno=node.lineno, func=node.name, param=arg.arg,
                defaults_to_none=isinstance(d, ast.Constant) and d.value is None,
                has_default=arg.arg in defaults,
            ))
        names = {arg.arg for arg in ordered}
        if a.vararg:
            names.add(a.vararg.arg)
        if a.kwarg:
            names.add(a.kwarg.arg)
        # ⚠️ DECORATORS ARE VISITED IN THE OUTER SCOPE, NOT THIS FUNCTION'S.
        # A decorator is evaluated where the `def` stands, so a name inside
        # `@decide(wants=(...))` is not this function's parameter — treating it
        # as one would manufacture a forwarding edge out of a declaration.
        # (The repo's own lesson, from the other side: a very similar check
        # once reported ZERO because `inspect.getsource` DOES include the
        # decorator and the walk did not look there. Both halves are wrong in
        # their own direction; an AST walk has to place the decorator itself.)
        for dec in node.decorator_list:
            self.visit(dec)
        self._stack.append((node.name, names))
        self._scan_guards(node)
        for field_name, value in ast.iter_fields(node):
            if field_name == "decorator_list":
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    # -- the guard discriminator ----------------------------------------
    def _scan_guards(self, node: ast.FunctionDef) -> None:
        """Does the body branch on this parameter being absent?

        ⚠️ This is the discriminator that separates *an optional argument
        working as designed* from *a value the code is waiting for*. A guard
        is `if p is None:` / `if not p:` whose body ABSTAINS — returns, raises,
        or files a reason string. An optional argument that merely defaults
        (`p = p or 4`) is not a guard and is not reported.
        """
        params = {arg.arg for arg in
                  list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)}
        for sub in ast.walk(node):
            if not isinstance(sub, ast.If):
                continue
            named = _absence_test(sub.test, params)
            if not named:
                continue
            body_kinds = {type(s) for s in ast.walk(ast.Module(body=sub.body, type_ignores=[]))}
            abstains = bool(body_kinds & {ast.Return, ast.Raise})
            # or it RECORDS an abstention — a call whose arguments carry a
            # reason string. The staged pipeline's whole idiom.
            if not abstains:
                for s in ast.walk(ast.Module(body=sub.body, type_ignores=[])):
                    if isinstance(s, ast.Call):
                        for arg in list(s.args) + [k.value for k in s.keywords]:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                abstains = True
                                break
                    if abstains:
                        break
            if abstains:
                for p in named:
                    self.guards.append(((node.name, p), f"{self.path.name}:{sub.lineno}"))

    # -- call sites ------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        callee: Optional[str]
        if isinstance(func, ast.Name):
            callee = None if func.id in self._foreign else func.id
        elif isinstance(func, ast.Attribute):
            base = func.value
            if isinstance(base, ast.Name) and base.id in self._foreign:
                callee = None          # `asyncio.gather(...)` is not ours
            else:
                callee = func.attr
        else:
            callee = None
        if callee:
            enclosing_name, enclosing_params = self._stack[-1] if self._stack else (None, set())
            for kw in node.keywords:
                if kw.arg is None:
                    # `f(**opts)` — we cannot tell what it supplies, so treat
                    # it as supplying EVERYTHING. ⚠️ Conservative on purpose:
                    # a splat we cannot read must not produce a finding.
                    self.supplies.append(Supply(
                        self.path, node.lineno, callee, "**", "keyword", None, "**splat"))
                    continue
                self.supplies.append(Supply(
                    self.path, node.lineno, callee, kw.arg, "keyword",
                    (enclosing_name, kw.value.id)
                    if (isinstance(kw.value, ast.Name)
                        and kw.value.id in enclosing_params
                        and enclosing_name) else None,
                    _render(kw.value),
                ))
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.Starred):
                    self.supplies.append(Supply(
                        self.path, node.lineno, callee, "*", "positional", None, "*splat"))
                    continue
                self.supplies.append(Supply(
                    self.path, node.lineno, callee, f"#{i}", "positional",
                    (enclosing_name, arg.id)
                    if (isinstance(arg, ast.Name)
                        and arg.id in enclosing_params
                        and enclosing_name) else None,
                    _render(arg),
                ))
        self.generic_visit(node)


def _absence_test(test: ast.expr, params: Set[str]) -> List[str]:
    """Names of parameters this test asserts are ABSENT."""
    out: List[str] = []
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left, op, right = test.left, test.ops[0], test.comparators[0]
        if isinstance(op, ast.Is) and isinstance(right, ast.Constant) and right.value is None:
            if isinstance(left, ast.Name) and left.id in params:
                out.append(left.id)
    elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        if isinstance(test.operand, ast.Name) and test.operand.id in params:
            out.append(test.operand.id)
    elif isinstance(test, ast.BoolOp):
        for v in test.values:
            out.extend(_absence_test(v, params))
    return out


def _render(node: ast.expr) -> str:
    try:
        return ast.unparse(node)[:60]
    except Exception:  # pragma: no cover - py<3.9
        return type(node).__name__


# ---------------------------------------------------------------------------


def _rel(path: Path) -> str:
    """Paths in the report are relative, so two runs of two trees compare."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


@dataclass
class Report:
    files_scanned: int
    test_files_scanned: int
    tests_note: str
    total_params: int          # D0  every parameter declared
    none_defaulted: int        # D1  ...whose default is None
    threaded: int              # D2  ...that a forwarding edge touches
    unsupplied: int            # D3  ...with no producer at the fixpoint
    chains: int                # D4  ...grouped into chains of >= 2 layers
    guarded_chains: int        # D5  ...one of whose nodes abstains on absence
    findings: List[Finding]
    unguarded: List[Finding]

    def funnel(self) -> List[Tuple[str, int]]:
        return [
            ("parameters declared in scan (D0)", self.total_params),
            ("...defaulting to None (D1)", self.none_defaulted),
            ("...touched by a forwarding edge (D2)", self.threaded),
            ("...with no producer anywhere (D3)", self.unsupplied),
            ("...as chains crossing >= 2 layers (D4)", self.chains),
            ("...whose absence changes behaviour (D5)", self.guarded_chains),
        ]


def python_files(roots: Sequence[Path]) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            out.append(root)
            continue
        for p in sorted(root.rglob("*.py")):
            if _SKIP_DIR_PARTS & set(p.parts):
                continue
            out.append(p)
    return out


def scan(roots: Sequence[Path], *, tests_produce: bool = False,
         require_guard: bool = True) -> Report:
    """Walk the tree and find parameters with no producer.

    `tests_produce=False` is the default and is a MEASURED choice, not a
    convenience: a parameter only ever supplied by a test fixture has no
    PRODUCTION producer, and `pdf_path` is exactly that shape — the gather
    tests passed it, so counting them would have hidden the fault that cost
    12 staff-systems their instrument. The arm is switchable so the cost of
    the choice can be reported rather than assumed.
    """
    files = python_files(roots)
    local = _local_packages(roots)
    defs: Dict[ParamKey, List[ParamDef]] = defaultdict(list)
    supplies: List[Tuple[Path, Supply]] = []
    guards: Dict[ParamKey, List[str]] = defaultdict(list)
    n_tests = 0
    for path in files:
        if _is_test_path(path):
            n_tests += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        w = _Walker(path, local)
        w.visit(tree)
        for d in w.defs:
            defs[(d.func, d.param)].append(d)
        for s in w.supplies:
            supplies.append((path, s))
        for key, where in w.guards:
            guards[key].append(where)

    # Positional supplies need a parameter NAME. Resolve them against every
    # declaration of that function name; a position naming different
    # parameters under different declarations marks ALL of them — again
    # conservative, since it can only ADD supply and therefore only hide a
    # finding.
    order: Dict[Tuple[Path, int], List[str]] = defaultdict(list)
    for key, ds in defs.items():
        for d in ds:
            order[(d.path, d.lineno)].append(d.param)
    func_orders: Dict[str, List[List[str]]] = defaultdict(list)
    seen_sites: Set[Tuple[Path, int]] = set()
    for key, ds in defs.items():
        for d in ds:
            site = (d.path, d.lineno)
            if site in seen_sites:
                continue
            seen_sites.add(site)
            func_orders[d.func].append(order[site])

    splat_functions: Set[str] = set()
    direct: Dict[ParamKey, List[Supply]] = defaultdict(list)
    forwards: Dict[ParamKey, List[Supply]] = defaultdict(list)
    test_supplies: Dict[ParamKey, List[Supply]] = defaultdict(list)

    for path, s in supplies:
        is_test = _is_test_path(path) and not tests_produce
        if s.param in ("**", "*"):
            # `f(**opts)` — we cannot tell what it supplies, so it supplies
            # EVERYTHING. ⚠️ A splat inside a test is still only a test.
            if not is_test:
                splat_functions.add(s.func)
            continue
        names: List[str]
        if s.how == "positional":
            idx = int(s.param[1:])
            names = []
            for ordered in func_orders.get(s.func, []):
                # a bound method's `self` is not passed at the call site
                offset = 1 if ordered and ordered[0] in ("self", "cls") else 0
                if idx + offset < len(ordered):
                    names.append(ordered[idx + offset])
        else:
            names = [s.param]
        for name in names:
            key = (s.func, name)
            if key not in defs:
                continue
            if is_test:
                test_supplies[key].append(s)
                continue
            if s.forwarded_from and s.forwarded_from in defs:
                forwards[key].append(s)
            else:
                direct[key].append(s)

    # THE FIXPOINT. A node is SUPPLIED if it has a direct producer, or a
    # forward from a node that is itself SUPPLIED, or belongs to a function
    # somebody splats into. Everything else is a value nothing ever starts.
    supplied: Set[ParamKey] = {k for k, v in direct.items() if v}
    for key in defs:
        if key[0] in splat_functions:
            supplied.add(key)
    changed = True
    while changed:
        changed = False
        for key, fs in forwards.items():
            if key in supplied:
                continue
            if any(s.forwarded_from in supplied for s in fs):
                supplied.add(key)
                changed = True

    total = sum(len(v) for v in defs.values())
    d1 = {k for k, ds in defs.items() if any(d.defaults_to_none for d in ds)}
    # D2 is symmetric: a node is "threaded" if a forwarding edge TOUCHES it,
    # as source or as target. The source end matters — `run_staged(roster)` is
    # the ROOT of the chain and has no forward into it, so a target-only test
    # would report every chain without its head.
    edges: List[Tuple[ParamKey, ParamKey, Supply]] = []
    for dst, fs in forwards.items():
        for s in fs:
            if s.forwarded_from:
                edges.append((s.forwarded_from, dst, s))
    d2 = {k for a, b, _ in edges for k in (a, b) if k in d1}
    d3 = {k for k in d2 if k not in supplied}

    # Group the survivors into CHAINS (weakly connected components).
    parent: Dict[ParamKey, ParamKey] = {k: k for k in d3}

    def find(x: ParamKey) -> ParamKey:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    chain_edges: Dict[ParamKey, List[Supply]] = defaultdict(list)
    for a, b, s in edges:
        if a in d3 and b in d3:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
    groups: Dict[ParamKey, List[ParamKey]] = defaultdict(list)
    for k in sorted(d3):
        groups[find(k)].append(k)
    for a, b, s in edges:
        if a in d3 and b in d3:
            chain_edges[find(a)].append(s)

    def order_chain(keys: List[ParamKey]) -> List[ParamKey]:
        """Head first, then breadth-first along the forwarding edges.

        The printed order IS the route the value would take, so a reader can
        see which layer never starts it.
        """
        member = set(keys)
        out_edges: Dict[ParamKey, List[ParamKey]] = defaultdict(list)
        targets: Set[ParamKey] = set()
        for a, b, _ in edges:
            if a in member and b in member:
                out_edges[a].append(b)
                targets.add(b)
        ordered = [k for k in keys if k not in targets]
        if not ordered:              # a cycle: start anywhere, deterministically
            ordered = [keys[0]]
        seen = set(ordered)
        queue = list(ordered)
        while queue:
            k = queue.pop(0)
            for nxt in sorted(out_edges.get(k, [])):
                if nxt not in seen:
                    seen.add(nxt)
                    ordered.append(nxt)
                    queue.append(nxt)
        ordered.extend(k for k in keys if k not in seen)
        return ordered

    findings: List[Finding] = []
    for root, keys in groups.items():
        if len(keys) < 2:
            continue  # one node is not a chain; it is an optional argument
        ordered = order_chain(keys)
        findings.append(Finding(
            keys=ordered,
            defs={k: defs[k] for k in ordered},
            edges=chain_edges[root],
            guards={k: guards[k] for k in ordered if guards.get(k)},
            test_only_supplies=[s for k in ordered for s in test_supplies.get(k, [])],
        ))
    findings.sort(key=lambda f: f.ident)
    guarded = [f for f in findings if f.guards]
    unguarded = [f for f in findings if not f.guards]

    return Report(
        files_scanned=len(files), test_files_scanned=n_tests,
        tests_note=("which DO count as producers" if tests_produce
                    else "which do NOT count as producers"),
        total_params=total, none_defaulted=len(d1), threaded=len(d2),
        unsupplied=len(d3), chains=len(findings), guarded_chains=len(guarded),
        findings=guarded if require_guard else findings,
        unguarded=unguarded,
    )


# ---------------------------------------------------------------------------
# The inventory. ⚠️ NOT a suppression list: every entry carries a REASON, and
# `test_no_producer.py` fails on an entry that no longer fires — the
# `KNOWN_GAPS` rule, so the list describes the tree and never its history.

RECORDED: Dict[str, str] = {
    # ⚠️ `run_staged.roster` LEFT THIS LIST 2026-09-15, THE SAME DAY IT
    # ARRIVED, and its own entry said to: "REMOVE THIS ENTRY the day a
    # producer lands". `staged/__main__.py` gained `--work-id` / `--no-roster`
    # and `adjudicate_instrument` now READS the row (at
    # `Scope.SELF_AND_ANCESTORS` — it is filed on the DOCUMENT and the
    # decision runs at STAFF, which is a second fault this chain could not
    # see). Measured: the label `Basso.` on Litolff Beethoven 5 goes
    # `Bass voice` -> `Contrabass`. See `benchmarks/omr-producer-consumer-
    # 2026-09/FINDINGS.md`. The stale-entry test is what made it leave.
    "run_staged.dossier": (
        "OPEN FINDING, NOT EXCUSED — recorded 2026-09-15, same chain, same "
        "shape, found by this check rather than by accident. `--dossier` "
        "exists on `tools.omr.transcribe` and NOT on `staged/__main__.py`, so "
        "Q.DOSSIER_FACT abstains on every staged run. REMOVE THIS ENTRY the "
        "day a producer lands."
    ),
}


def format_report(report: Report) -> str:
    lines = ["THE FUNNEL", ""]
    for label, n in report.funnel():
        lines.append(f"  {n:6d}  {label}")
    lines.append("")
    lines.append(f"  {report.files_scanned} files scanned "
                 f"({report.test_files_scanned} of them tests, {report.tests_note})")
    lines.append("")
    lines.append(f"FINDINGS — {len(report.findings)} parameter(s) threaded with no producer")
    lines.append("")
    for f in report.findings:
        recorded = RECORDED.get(f.ident)
        lines.append(f"  {f.name}"
                     + ("   [RECORDED: " + recorded + "]" if recorded else ""))
        for k in f.keys:
            for d in f.defs[k]:
                lines.append(f"      declared  {d.func}({d.param})  {_rel(d.path)}:{d.lineno}")
        for s in sorted(f.edges, key=lambda s: (str(s.path), s.lineno)):
            src = f"{s.forwarded_from[0]}({s.forwarded_from[1]})" if s.forwarded_from else "?"
            lines.append(f"      forwarded {src} -> {s.func}({s.param})"
                         f"  {_rel(s.path)}:{s.lineno}")
        for k, gs in f.guards.items():
            for g in gs:
                lines.append(f"      ABSENCE CHANGES BEHAVIOUR in {k[0]}() at {g}")
        if f.test_only_supplies:
            ex = f.test_only_supplies[0]
            lines.append(f"      supplied ONLY by tests, {len(f.test_only_supplies)} site(s)"
                         f" — e.g. {ex.func}({ex.param}) {_rel(ex.path)}:{ex.lineno}")
        lines.append("")
    if report.unguarded:
        lines.append(f"NOT REPORTED — {len(report.unguarded)} chain(s) with no producer and no "
                     f"absence branch (an ordinary optional argument threaded for convenience):")
        for f in report.unguarded:
            lines.append("    " + f.name)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None,
                    help="repo root (default: this file's repo)")
    ap.add_argument("--scan", action="append", default=None,
                    help="directory to scan, repeatable (default: tools/)")
    ap.add_argument("--tests-produce", action="store_true",
                    help="count a test call site as a producer (measures the cost of not doing so)")
    ap.add_argument("--no-guard-filter", action="store_true",
                    help="report every unsupplied threaded parameter, guarded or not")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero on a finding that is not in RECORDED")
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    roots = [Path(s) for s in args.scan] if args.scan else [root / "tools"]
    report = scan(roots, tests_produce=args.tests_produce,
                  require_guard=not args.no_guard_filter)

    if args.json:
        print(json.dumps({
            "funnel": report.funnel(),
            "findings": [{
                "parameter": f.param,
                "chain": [list(k) for k in f.keys],
                "declared": [f"{_rel(d.path)}:{d.lineno}" for k in f.keys for d in f.defs[k]],
                "guards": {f"{k[0]}.{k[1]}": v for k, v in f.guards.items()},
                "recorded": RECORDED.get(f.ident),
            } for f in report.findings],
        }, indent=2))
    else:
        print(format_report(report))

    if args.check:
        unrecorded = [f for f in report.findings if f.ident not in RECORDED]
        if unrecorded:
            print("\nFAIL: parameter(s) threaded with no producer: "
                  + ", ".join(f.name for f in unrecorded), file=sys.stderr)
            return 1
        print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
