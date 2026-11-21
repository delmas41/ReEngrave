"""THE DATA-FLOW MAP, GENERATED FROM THE CODE (ROADMAP 2.331 step 3). PATH: STAGED, tooling only -- no stage, no row, no decision.

    python3 -m tools.omr.staged.flow_map                    # write docs/data-flow.md
    python3 -m tools.omr.staged.flow_map --check            # exit 1 if docs/data-flow.md is stale
    python3 -m tools.omr.staged.flow_map --mark clef        # one mark's block, the same rows as the page
    python3 -m tools.omr.staged.flow_map --quantity Q.CLEF  # one fact's block (a `Q.` name or its value)
    python3 -m tools.omr.staged.flow_map --consumer export  # every "read by" row naming a stage, a file or a function
    python3 -m tools.omr.staged.flow_map --gaps             # PART 3 only

Sean, 2026-11-21: "Generate the map and include information that makes it possible for any agent or human to get a quick answer about the
current state of data flow."

WHAT IS DERIVED (never typed here): every `observe` / `abstain` / read call on the record (`reach._accessors()`, the same accessor set the
derived checks use) with its file, function and stage; whether each site is LIVE under the default flags (every `OMR_*` predicate the code
defines is CALLED with no `OMR_*` variable set, and its value is carried through the `if` tests, early returns and call sites that lead to the
site); the verdict producers (`adjudicate.REGISTRY`, `evaluate.RULES`, `infer.RULES`); the claims register (`stroke_owner.TIERS`,
`claim_order.LAYERS`, `claimed_by._ORDER`, `claim_final.mark_only()` CALLED under the defaults, and every `Q.CLAIMED_AREA` filing site with the
`owner` it files); the reason words a decider can return against the literal reason words consumers test; the detail keys read against the
detail keys filed anywhere.

WHAT IS DECLARED (ONE table, `MARKS`, below): the musician's name and one line for each mark, whether it is found from ink or from a detector
box, which functions read it (new and old), and what the file writes. The table cannot rot: `table_problems()` fails the build when a function
the code has that files a row is in no mark, when a registered decision is in no mark, or when a mark names a function that no longer exists.

CONVENTION ASSUMED: a site is DEAD under the defaults only where a flag predicate (or an `OMR_*` environment test) decides the branch; data-flow
deadness (a variable set False on the default branch) is not seen. WHAT WOULD FALSIFY IT: a row the page calls LIVE that a default run never
files, or one it calls behind an off flag that a default run files. NOT CONFIRMED on a run: this reads the code, never a record.
"""
from __future__ import annotations

import argparse
import ast
import collections
import contextlib
import importlib
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

DERIVED_CHECK = True

STAGED = pathlib.Path(__file__).resolve().parent
ROOT = STAGED.parents[2]
PAGE = ROOT / "docs" / "data-flow.md"
BASE_PKG = "tools.omr.staged"
STAGES = ("GATHER", "ADJUDICATE", "EVALUATE", "INFER", "EXPORT", "HARNESS", "tools")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 0. the default environment
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
@contextlib.contextmanager
def default_env():
    """Every `OMR_*` variable removed for the duration: the flags as the code resolves them today."""
    saved = {k: v for k, v in os.environ.items() if k.startswith("OMR_")}
    for k in saved:
        del os.environ[k]
    try:
        yield
    finally:
        for k in [k for k in os.environ if k.startswith("OMR_")]:
            del os.environ[k]
        os.environ.update(saved)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. the files, their imports and their constants
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
UNK = object()          # a value the static evaluator cannot know


@dataclass
class Module:
    rel: str                                # path relative to the staged dir (or `../x.py` for a shared reader outside it)
    name: str                               # dotted module name
    tree: ast.Module
    stage: Optional[str]                    # GATHER ... EXPORT / HARNESS / tools; None = not walked for sites
    aliases: Dict[str, str] = field(default_factory=dict)            # local name -> dotted module
    from_names: Dict[str, Tuple[str, str]] = field(default_factory=dict)   # local name -> (dotted module, attr)
    consts: Dict[str, ast.AST] = field(default_factory=dict)        # module-level NAME = expr (assigned once)
    funcs: Dict[str, List[ast.AST]] = field(default_factory=dict)   # bare name -> defs (any nesting)
    top_funcs: Dict[str, ast.AST] = field(default_factory=dict)
    derived_check: bool = False
    helper: bool = False                    # a pure helper a stage imports (its words are a stage's words)


def _stage_of(rel: str, stage_of_file: Dict[str, str], not_a_stage: Iterable[str]) -> Optional[str]:
    p = pathlib.PurePosixPath(rel)
    if p.parent.name == "adjudicators":
        return "ADJUDICATE"
    if p.name in stage_of_file:
        return stage_of_file[p.name]
    if p.name in set(not_a_stage) or p.parent.name == "review":
        return "tools"
    return "tools"


def _resolve_relative(pkg: str, level: int, mod: Optional[str]) -> str:
    parts = pkg.split(".")
    if level > 1:
        parts = parts[: len(parts) - (level - 1)]
    base = ".".join(parts)
    return f"{base}.{mod}" if mod else base


def _load(path: pathlib.Path, rel: str, name: str, stage: Optional[str]) -> Module:
    tree = ast.parse(path.read_text())
    m = Module(rel=rel, name=name, tree=tree, stage=stage)
    pkg = name.rsplit(".", 1)[0] if not path.name == "__init__.py" else name
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    m.aliases[a.asname] = a.name
                else:
                    m.aliases[a.name.split(".")[0]] = a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            src = _resolve_relative(pkg, node.level, node.module) if node.level else (node.module or "")
            for a in node.names:
                local = a.asname or a.name
                # `from . import x` names a MODULE; `from .x import f` names an attribute (or a submodule: both are tried at use)
                m.aliases.setdefault(local, f"{src}.{a.name}")
                m.from_names[local] = (src, a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            m.funcs.setdefault(node.name, []).append(node)
    counts = collections.Counter()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    counts[t.id] += 1
                    m.consts[t.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            counts[node.target.id] += 1
            m.consts[node.target.id] = node.value
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            m.top_funcs[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:          # class-level string constants (`ABSTAIN.NO_INK`, `READERS.X`) resolve as `Class.NAME`
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            m.consts[f"{node.name}.{t.id}"] = sub.value
    for k, n in counts.items():
        if n > 1:
            m.consts.pop(k, None)
    m.derived_check = any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DERIVED_CHECK" for t in n.targets)
                          and isinstance(n.value, ast.Constant) and n.value.value is True for n in tree.body)
    return m


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. the static evaluator (three-valued: a value, or UNK)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
_ENV = object()          # `os.environ`


def _truthy(v):
    return UNK if v is UNK else bool(v)


class Ctx:
    def __init__(self, an: "Analysis", mod: Module, local: Optional[Dict[str, ast.AST]] = None):
        self.an, self.mod, self.local = an, mod, local or {}
        self.memo: Dict[str, Any] = {}
        self.busy: Set[str] = set()
        self.flags_seen: Set[str] = set()      # OMR_* names this evaluation touched
        self.preds_seen: Set[str] = set()      # predicate functions it called
        self.known: Dict[str, Tuple[Any, Tuple[str, ...]]] = {}   # a parameter every caller passes None-by-default


def _name_value(name: str, ctx: Ctx):
    if name in ctx.known:
        v, fl = ctx.known[name]
        ctx.flags_seen |= set(fl)
        ctx.preds_seen.add(f"{name} (None by default)")
        return v
    if name in ctx.memo:
        return ctx.memo[name]
    if name in ctx.busy:
        return UNK
    src = ctx.local.get(name)
    mod_ctx = ctx
    if src is None:
        src = ctx.mod.consts.get(name)
    if src is None:
        return UNK
    ctx.busy.add(name)
    try:
        v = ev(src, mod_ctx)
    finally:
        ctx.busy.discard(name)
    ctx.memo[name] = v
    return v


def _module_const(dotted: str, attr: str, ctx: Ctx):
    m = ctx.an.module(dotted)
    if m is None or attr not in m.consts:
        return UNK
    sub = Ctx(ctx.an, m)
    v = ev(m.consts[attr], sub)
    ctx.flags_seen |= sub.flags_seen
    return v


def _is_environ(node: ast.AST, ctx: Ctx) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name) and ctx.mod.aliases.get(node.value.id) == "os":
        return True
    if isinstance(node, ast.Name) and ctx.mod.from_names.get(node.id) == ("os", "environ"):
        return True
    return False


def resolve_callable(func: ast.AST, mod: Module, an: "Analysis") -> Optional[Tuple[str, str]]:
    """`(dotted module, function name)` a call names, or None (a method on an object, a builtin)."""
    if isinstance(func, ast.Name):
        if func.id in mod.from_names:
            src, attr = mod.from_names[func.id]
            return (src, attr)
        if func.id in mod.funcs:
            return (mod.name, func.id)
        return None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        alias = func.value.id
        if alias in mod.aliases:
            dotted = mod.aliases[alias]
            if an.module(dotted) is not None:
                return (dotted, func.attr)
            if alias in mod.from_names:           # `from .x import Y` where Y is a class: Y.method
                src, attr = mod.from_names[alias]
                if an.module(src) is not None:
                    return (src, f"{attr}.{func.attr}")
    return None


def ev(node: ast.AST, ctx: Ctx):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return _name_value(node.id, ctx)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        vals = [ev(e, ctx) for e in node.elts]
        if any(v is UNK for v in vals):
            return UNK
        return tuple(vals) if not isinstance(node, ast.Set) else frozenset(vals)
    if isinstance(node, ast.Attribute):
        if _is_environ(node, ctx):
            return _ENV
        if isinstance(node.value, ast.Name):
            a = node.value.id
            if a in ctx.mod.aliases and ctx.an.module(ctx.mod.aliases[a]) is not None:
                return _module_const(ctx.mod.aliases[a], node.attr, ctx)
            key = f"{a}.{node.attr}"
            if key in ctx.mod.consts:
                return _name_value(key, ctx)
        return UNK
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        v = ev(node.operand, ctx)
        return UNK if v is UNK else (not v)
    if isinstance(node, ast.BoolOp):
        unknown = False
        last = None
        for sub in node.values:
            v = ev(sub, ctx)
            if v is UNK:
                unknown = True
                continue
            if isinstance(node.op, ast.And) and not v:
                return v
            if isinstance(node.op, ast.Or) and v:
                return v
            last = v
        return UNK if unknown else last
    if isinstance(node, ast.IfExp):
        t = _truthy(ev(node.test, ctx))
        if t is UNK:
            return UNK
        return ev(node.body if t else node.orelse, ctx)
    if isinstance(node, ast.Compare):
        left = ev(node.left, ctx)
        if left is UNK:
            return UNK
        for op, comp in zip(node.ops, node.comparators):
            right = ev(comp, ctx)
            if right is UNK:
                return UNK
            try:
                if right is _ENV and isinstance(op, (ast.In, ast.NotIn)) and isinstance(left, str):
                    if not left.startswith("OMR_"):
                        return UNK
                    ctx.flags_seen.add(left)
                    ok = isinstance(op, ast.NotIn)
                elif isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                elif isinstance(op, ast.In):
                    ok = left in right
                elif isinstance(op, ast.NotIn):
                    ok = left not in right
                elif isinstance(op, ast.Is):
                    ok = left is right
                elif isinstance(op, ast.IsNot):
                    ok = left is not right
                else:
                    return UNK
            except TypeError:
                return UNK
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        f = node.func
        # os.environ.get(K, D) / os.getenv(K, D): only an OMR_* key is known (absent under the defaults)
        if isinstance(f, ast.Attribute) and f.attr in ("get",) and _is_environ(f.value, ctx) or (
                isinstance(f, ast.Attribute) and f.attr == "getenv" and isinstance(f.value, ast.Name) and ctx.mod.aliases.get(f.value.id) == "os"):
            if not node.args:
                return UNK
            key = ev(node.args[0], ctx)
            if not isinstance(key, str) or not key.startswith("OMR_"):
                return UNK
            ctx.flags_seen.add(key)
            if len(node.args) > 1:
                return ev(node.args[1], ctx)
            return None
        if isinstance(f, ast.Attribute) and f.attr in ("strip", "lower", "upper", "casefold") and not node.args:
            v = ev(f.value, ctx)
            if isinstance(v, str):
                return getattr(v, f.attr)()
            return UNK
        if isinstance(f, ast.Name) and f.id == "bool" and len(node.args) == 1:
            return _truthy(ev(node.args[0], ctx))
        target = resolve_callable(f, ctx.mod, ctx.an)
        if target is None:
            return UNK
        nf = ctx.an.none_fn(*target)
        if nf is not None:
            ctx.flags_seen |= set(nf)
            ctx.preds_seen.add(f"{target[1]} (None by default)")
            return None
        if node.args or node.keywords:
            return UNK
        p = ctx.an.predicate(*target)
        if p is None:
            return UNK
        ctx.flags_seen |= set(p.flags)
        ctx.preds_seen.add(p.label)
        return p.default
    return UNK


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. flag predicates: every zero-argument function that reads an OMR_* variable, CALLED under the defaults
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Predicate:
    module: str
    name: str
    default: Any
    flags: Tuple[str, ...]
    how: str                     # "called" (imported and called under the defaults) or "static"

    @property
    def label(self) -> str:
        return f"{self.module.rsplit('.', 1)[-1]}.{self.name}"


def _required_args(fn: ast.AST) -> int:
    a = fn.args
    pos = len(a.posonlyargs) + len(a.args)
    return (pos - len(a.defaults)) + sum(1 for d in a.kw_defaults if d is None)


def _mentions_env(fn: ast.AST, mod: Module, an: "Analysis", depth: int = 0) -> bool:
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"OMR_[A-Z0-9_]+", n.value):
            return True
        if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv"):
            return True
        if isinstance(n, ast.Name) and n.id in mod.consts:
            c = mod.consts[n.id]
            if isinstance(c, ast.Constant) and isinstance(c.value, str) and re.fullmatch(r"OMR_[A-Z0-9_]+", c.value):
                return True
        if depth < 3 and isinstance(n, ast.Call) and not n.args and not n.keywords:
            t = resolve_callable(n.func, mod, an)
            if t is not None and (t[0], t[1]) != (mod.name, getattr(fn, "name", "")):
                m2 = an.module(t[0])
                f2 = m2.top_funcs.get(t[1]) if m2 else None
                if f2 is not None and _required_args(f2) == 0 and _mentions_env(f2, m2, an, depth + 1):
                    return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. the sites
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Site:
    rel: str
    func: str                    # enclosing function (dotted for nesting), "<module>" at top level
    line: int
    stage: str
    kind: str                    # observe / abstain / read
    quantity: str
    accessor: str
    live_local: bool             # live inside its own function under the defaults
    why: str = ""                # the test that kills it, when it is dead
    flags: Tuple[str, ...] = ()  # the OMR_* flags on its path
    keys: Tuple[str, ...] = ()   # detail keys filed (observe / abstain kwargs)
    owner: Optional[str] = None  # the `owner` a Q.CLAIMED_AREA row files, where it is a literal

    @property
    def where(self) -> str:
        return f"{self.rel}:{self.func}"


@dataclass
class FnInfo:
    rel: str
    qual: str
    name: str
    node: ast.AST
    call_sites: List[Tuple[str, bool, str]] = field(default_factory=list)   # (caller fn key, live_local, why)
    referenced: bool = False
    dead: bool = False
    why: str = ""
    flags: Set[str] = field(default_factory=set)

    @property
    def key(self) -> str:
        return f"{self.rel}:{self.qual}"


_DETAIL_KW_SKIP = {"reader", "frame", "score", "derived_from"}
_ROW_NAMES = ("detail",)


class Analysis:
    """Everything derived from one staged/ tree. `root` and `q_values` may be a throwaway tree (the control in the tests)."""

    def __init__(self, root: pathlib.Path = STAGED, q_values: Optional[Dict[str, str]] = None,
                 accessors: Optional[Tuple[Dict[str, int], Dict[str, int]]] = None, registry: bool = True,
                 stage_of_file: Optional[Dict[str, str]] = None, not_a_stage: Optional[Iterable[str]] = None):
        from . import reach as _R
        self.root = pathlib.Path(root).resolve()
        self.real = self.root == STAGED
        if q_values is None:
            from .record import Q
            q_values = {k: v for k, v in vars(Q).items() if isinstance(v, str) and not k.startswith("_")}
        self.q_attr = dict(q_values)                       # attr -> value
        self.q_vals = set(self.q_attr.values())
        self.q_name = {v: k for k, v in self.q_attr.items()}
        self.read_at, self.write_at = accessors or _R._accessors()
        self.stage_of_file = stage_of_file if stage_of_file is not None else _R.STAGE_OF_FILE
        self.not_a_stage = set(not_a_stage) if not_a_stage is not None else set(_R.NOT_A_STAGE)
        self.registry = registry
        self.modules: Dict[str, Module] = {}
        self.by_rel: Dict[str, Module] = {}
        self._preds: Dict[Tuple[str, str], Optional[Predicate]] = {}
        self.funcs: Dict[str, FnInfo] = {}
        self._node_qual: Dict[int, str] = {}
        self._cw: Dict[str, Dict[str, List[str]]] = {}
        self._skip_lit: Dict[int, bool] = {}
        #: functions that return None under the defaults (their value-returning path is behind an off flag): (dotted, name) -> flags
        self._none_fns: Dict[Tuple[str, str], Tuple[str, ...]] = {}
        #: parameters every live caller passes None-by-default: fn key -> {param: flags}
        self._param_none: Dict[str, Dict[str, Tuple[str, ...]]] = {}
        self._load_tree()
        self._mark_helpers()
        self._index_funcs()
        for m in list(self.by_rel.values()):
            self._const_words(m)
        # a value that is None because a flag is off travels: a function returning None by default, the variable it is stored in, the
        # parameter it is passed to. Each pass learns the next link; it stops when nothing new is learned (at most four passes).
        for _ in range(4):
            self._reset()
            self._walk_all()
            self._resolve_pending()
            self._propagate()
            nf, pn = self._derive_none()
            if nf == self._none_fns and pn == self._param_none:
                break
            self._none_fns, self._param_none = nf, pn

    def _reset(self) -> None:
        self.sites: List[Site] = []
        self.reason_tests: List[Tuple[str, str, int, str, str]] = []      # (word, rel:func, line, stage, how)
        self.reason_makes: Dict[str, List[Tuple[str, int, bool, str]]] = collections.defaultdict(list)  # word -> (rel:func, line, live, stage)
        self.reason_prefixes: List[Tuple[str, str, bool]] = []           # f-string reasons: (prefix, rel:func, live)
        self.detail_read: Dict[str, Set[str]] = collections.defaultdict(set)
        self.detail_filed: Dict[str, Set[str]] = collections.defaultdict(set)
        self.unresolved: List[str] = []
        self._refs: Dict[str, int] = {}
        self._attr_calls: Dict[str, List[Tuple[str, bool, str]]] = {}
        self._call_flags: Dict[str, Set[str]] = collections.defaultdict(set)    # fn key -> flags / predicates on the paths that call it
        self._consumed_lits: Set[int] = set()
        self._rets: Dict[str, List[Tuple[bool, bool]]] = collections.defaultdict(list)   # fn key -> (live, returns None)
        self._killed: Dict[str, Set[str]] = collections.defaultdict(set)                 # fn key -> flags that killed code in it
        self._callargs: Dict[str, List[Dict[Any, Tuple[str, ...]]]] = collections.defaultdict(list)
        self._pending: List[Tuple] = []
        self._q_args: Dict[str, List[Tuple]] = collections.defaultdict(list)
        for fi in self.funcs.values():
            fi.call_sites, fi.dead, fi.why = [], False, ""

    def _mark_helpers(self) -> None:
        """A module outside the stage list that a STAGE module imports is a pure helper of that stage (`beam_strokes`, `stem_strokes`): the
        reason words it returns are the stage's. A module no stage imports is an instrument (a report, a check) and produces nothing."""
        imported: Set[str] = set()
        for m in self.by_rel.values():
            if m.stage in (None, "tools"):
                continue
            imported |= set(m.aliases.values())
            imported |= {src for src, _a in m.from_names.values()} | {f"{src}.{a}" for src, a in m.from_names.values()}
        for m in self.by_rel.values():
            if m.stage == "tools" and m.name in imported and not m.derived_check:
                m.helper = True

    def _resolve_pending(self) -> None:
        """A record call whose quantity is a PARAMETER of its function (`_observe_band(log, g, quantity, ...)`): each caller that passes a
        quantity there is the producer (or reader), filed at the caller's call line."""
        for fkey, pname, pidx, kind, acc, live, why, flags, keys, at in self._pending:
            hit = False
            for mod, fqual, line, clive, cwhy, cflags, qa in self._q_args.get(fkey, []):
                qs = qa.get(pidx, qa.get(pname))
                if not qs:
                    continue
                hit = True
                for q in qs:
                    self.sites.append(Site(mod.rel, fqual, line, mod.stage or "tools", kind, q, acc, live and clive, why or cwhy,
                                           tuple(sorted(set(flags) | set(cflags))), keys, None))
            if not hit:
                self.unresolved.append(f"{at} .{acc}(<parameter {pname}>)")

    def none_fn(self, dotted: str, name: str) -> Optional[Tuple[str, ...]]:
        return self._none_fns.get((dotted, name))

    def _ctx(self, mod: Module, local, fqual: str) -> "Ctx":
        c = Ctx(self, mod, local)
        kn = self._param_none.get(f"{mod.rel}:{fqual}")
        if kn:
            c.known = {k: (None, v) for k, v in kn.items()}
        return c

    def _derive_none(self):
        nf: Dict[Tuple[str, str], Tuple[str, ...]] = {}
        for key, rets in self._rets.items():
            if key not in self._killed or key not in self.funcs:
                continue
            live = [r for r in rets if r[0]]
            if live and all(r[1] for r in live) and any((not r[0]) and (not r[1]) for r in rets):
                fi = self.funcs[key]
                mod = self.by_rel[fi.rel]
                if "." not in fi.qual:
                    nf[(mod.name, fi.name)] = tuple(sorted(f for f in self._killed[key] if f.startswith("OMR_")))
        pn: Dict[str, Dict[str, Tuple[str, ...]]] = {}
        for key, calls in self._callargs.items():
            fi = self.funcs.get(key)
            if fi is None or not calls:
                continue
            a = fi.node.args
            params = [x.arg for x in a.posonlyargs + a.args]
            got: Dict[str, Tuple[str, ...]] = {}
            for i, pname in enumerate(params):
                fl: Set[str] = set()
                ok = True
                for c in calls:
                    v = c.get(i, c.get(pname))
                    if v is None:
                        ok = False
                        break
                    fl |= set(v)
                if ok:
                    got[pname] = tuple(sorted(fl))
            for k in a.kwonlyargs:
                fl = set()
                ok = True
                for c in calls:
                    v = c.get(k.arg)
                    if v is None:
                        ok = False
                        break
                    fl |= set(v)
                if ok:
                    got[k.arg] = tuple(sorted(fl))
            if got:
                pn[key] = got
        return nf, pn

    # ── loading ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def _load_tree(self) -> None:
        for p in sorted(self.root.rglob("*.py")):
            if p.name.startswith("test_") or "__pycache__" in p.parts:
                continue
            rel = str(p.relative_to(self.root))
            dotted = BASE_PKG + "." + rel[:-3].replace("/", ".")
            if dotted.endswith(".__init__"):
                dotted = dotted[: -len(".__init__")]
            m = _load(p, rel, dotted, _stage_of(rel, self.stage_of_file, self.not_a_stage))
            self.modules[dotted] = m
            self.by_rel[rel] = m

    def module(self, dotted: str) -> Optional[Module]:
        """A parsed module by dotted name: the staged tree, or (real tree only) a shared reader under tools/ it imports."""
        if dotted in self.modules:
            return self.modules[dotted]
        if not self.real or not dotted.startswith("tools."):
            return None
        rel = dotted.replace(".", "/")
        for cand in (ROOT / (rel + ".py"), ROOT / rel / "__init__.py"):
            if cand.is_file():
                m = _load(cand, "../" + str(cand.relative_to(ROOT / "tools" / "omr")), dotted, None)
                self.modules[dotted] = m
                return m
        self.modules[dotted] = None            # type: ignore[assignment]
        return None

    # ── predicates ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def predicate(self, dotted: str, name: str) -> Optional[Predicate]:
        key = (dotted, name)
        if key in self._preds:
            return self._preds[key]
        self._preds[key] = None                # recursion guard
        m = self.module(dotted)
        fn = m.top_funcs.get(name) if m else None
        if fn is None or _required_args(fn) != 0 or sum(isinstance(n, ast.stmt) for n in ast.walk(fn)) > 30:
            return None
        if not _mentions_env(fn, m, self):
            return None
        ctx = Ctx(self, m)
        val: Any = UNK
        how = "static"
        if self.real:
            try:
                with default_env():
                    mod = importlib.import_module(dotted)
                    val = getattr(mod, name)()
                how = "called"
            except Exception:                              # noqa: BLE001 -- a predicate that cannot be called falls back to the static read
                val = UNK
        # the flags it reads, statically (and its value, where it could not be called)
        rets = [n for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None]
        local = {t.id: n.value for n in ast.walk(fn) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        ctx.local = local
        svals = [ev(r.value, ctx) for r in rets]
        if val is UNK and how == "static":
            if len(svals) == 1 and svals[0] is not UNK:
                val = svals[0]
        for n in ast.walk(fn):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"OMR_[A-Z0-9_]+", n.value):
                ctx.flags_seen.add(n.value)
            if isinstance(n, ast.Name) and n.id in m.consts:
                c = m.consts[n.id]
                if isinstance(c, ast.Constant) and isinstance(c.value, str) and re.fullmatch(r"OMR_[A-Z0-9_]+", c.value):
                    ctx.flags_seen.add(c.value)
        if val is UNK or not isinstance(val, (bool, str, int, type(None))):
            return None
        p = Predicate(dotted, name, val, tuple(sorted(ctx.flags_seen)), how)
        self._preds[key] = p
        return p

    def predicates(self) -> List[Predicate]:
        return sorted((p for p in self._preds.values() if p is not None), key=lambda p: (p.module, p.name))

    # ── the walk ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def _qnames(self, node: ast.AST, ctx_fn_loops: Dict[str, List[str]], mod: Module) -> List[str]:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Q" and node.attr in self.q_attr:
            return [self.q_attr[node.attr]]
        if isinstance(node, ast.Constant) and node.value in self.q_vals:
            return [node.value]
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            out = []
            for e in node.elts:
                out += self._qnames(e, ctx_fn_loops, mod)
            return out
        if isinstance(node, ast.IfExp):
            return self._qnames(node.body, ctx_fn_loops, mod) + self._qnames(node.orelse, ctx_fn_loops, mod)
        if isinstance(node, ast.Name):
            if node.id in ctx_fn_loops:
                return ctx_fn_loops[node.id]
            if node.id in mod.consts:
                return self._qnames(mod.consts[node.id], {}, mod)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in mod.aliases:
            m2 = self.module(mod.aliases[node.value.id])
            if m2 is not None and node.attr in m2.consts:
                return self._qnames(m2.consts[node.attr], {}, m2)
        return []

    def _iter_qs(self, it: ast.AST, mod: Module, loops: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:
        """(the Qs a `for` iterable names at the first and at the second position of its items)."""
        base = it
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr in ("items", "keys", "values"):
            base = it.func.value
        node = base
        if isinstance(node, ast.Name) and node.id in mod.consts:
            node = mod.consts[node.id]
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in mod.aliases:
            m2 = self.module(mod.aliases[node.value.id])
            if m2 is not None and node.attr in m2.consts:
                node = m2.consts[node.attr]
                mod = m2
        first: List[str] = []
        second: List[str] = []
        if isinstance(node, ast.Dict):
            keys = [k for k in node.keys if k is not None]
            for k in keys:
                first += self._qnames(k, {}, mod)
            for v in node.values:
                second += self._qnames(v, {}, mod)
            if isinstance(it, ast.Call) and it.func.attr == "values":
                first, second = second, []
        elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for e in node.elts:
                if isinstance(e, (ast.Tuple, ast.List)) and e.elts:
                    first += self._qnames(e.elts[0], {}, mod)
                    if len(e.elts) > 1:
                        second += self._qnames(e.elts[1], {}, mod)
                else:
                    first += self._qnames(e, {}, mod)
        return first, second

    def _index_funcs(self) -> None:
        """Every function of the tree (nested too) with its qualified name, before any call site is read."""
        for rel, mod in sorted(self.by_rel.items()):
            def visit(node, prefix):
                for st in ast.iter_child_nodes(node):
                    if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        q = f"{prefix}{st.name}"
                        self._node_qual[id(st)] = q
                        fi = FnInfo(mod.rel, q, st.name, st)
                        self.funcs.setdefault(fi.key, fi)
                        visit(st, q + ".")
                    elif isinstance(st, ast.ClassDef):
                        visit(st, f"{prefix}{st.name}.")
                    else:
                        visit(st, prefix)
            visit(mod.tree, "")

    def _walk_all(self) -> None:
        for rel, mod in sorted(self.by_rel.items()):
            self._walk_body(mod, mod.tree.body, "<module>", {}, True, "", (), None, None)

    def _walk_body(self, mod, stmts, fqual, local, live, why, flags, parents, qual_of, loops=None):
        loops = dict(loops or {})
        for st in stmts:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = self._node_qual.get(id(st), st.name)
                loc = {}
                cnt = collections.Counter()
                for n in ast.walk(st):
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            if isinstance(t, ast.Name):
                                cnt[t.id] += 1
                                loc[t.id] = n.value
                    elif isinstance(n, (ast.AugAssign, ast.AnnAssign)) and isinstance(n.target, ast.Name):
                        cnt[n.target.id] += 2
                for k, c in cnt.items():
                    if c > 1:
                        loc.pop(k, None)
                for a in st.args.args + st.args.kwonlyargs:
                    loc.pop(a.arg, None)
                qv: Dict[str, List[str]] = {}
                for n in ast.walk(st):
                    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                        got = self._qnames(n.value, {}, mod)
                        if got:
                            qv.setdefault(n.targets[0].id, [])
                            qv[n.targets[0].id] += [x for x in got if x not in qv[n.targets[0].id]]
                if self._walk_body(mod, st.body, q, loc, True, "", (), parents, qual_of, qv):
                    self._rets[f"{mod.rel}:{q}"].append((True, True))      # falls off the end: returns None
                # decorators and defaults run where the def stands
                for d in st.decorator_list:
                    self._visit_expr(mod, d, fqual, local, live, why, flags, loops)
                continue
            if isinstance(st, ast.ClassDef):
                self._walk_body(mod, st.body, fqual if fqual != "<module>" else "<module>", local, live, why, flags, parents, qual_of, loops)
                continue
            if isinstance(st, ast.If):
                ctx = self._ctx(mod, local, fqual)
                t = _truthy(ev(st.test, ctx))
                if not (ctx.flags_seen or ctx.preds_seen):
                    t = UNK            # only a FLAG decides a branch here; a test of plain data is never "dead by default"
                fl = tuple(sorted(set(flags) | ctx.flags_seen | {f"pred:{p}" for p in ctx.preds_seen}))
                txt = ast.unparse(st.test)[:90]
                if live and t is not UNK:
                    self._killed[f"{mod.rel}:{fqual}"] |= ctx.flags_seen
                self._visit_expr(mod, st.test, fqual, local, live, why, flags, loops)
                b_live = live and t is not False
                o_live = live and t is not True
                self._walk_body(mod, st.body, fqual, local, b_live, why if not (live and t is False) else f"if {txt} is False by default",
                                fl if t is not UNK else flags, parents, qual_of, loops)
                self._walk_body(mod, st.orelse, fqual, local, o_live, why if not (live and t is True) else f"else of `if {txt}` (True by default)",
                                fl if t is not UNK else flags, parents, qual_of, loops)
                if live and t is True and _terminates(st.body):
                    live, why, flags = False, f"after `if {txt}: return` (True by default)", fl
                elif live and t is False and st.orelse and _terminates(st.orelse):
                    live, why, flags = False, f"after `if {txt}` returns in its else (False by default)", fl
                elif t is not UNK and ctx.flags_seen:
                    flags = fl if (t is True and _terminates(st.body)) else flags
                continue
            if isinstance(st, (ast.For, ast.AsyncFor)):
                self._visit_expr(mod, st.iter, fqual, local, live, why, flags, loops)
                lp = dict(loops)
                f, s = self._iter_qs(st.iter, mod, loops)
                tgt = st.target
                if isinstance(tgt, ast.Name) and f:
                    lp[tgt.id] = f
                elif isinstance(tgt, ast.Tuple) and tgt.elts:
                    if isinstance(tgt.elts[0], ast.Name) and f:
                        lp[tgt.elts[0].id] = f
                    if len(tgt.elts) > 1 and isinstance(tgt.elts[1], ast.Name) and s:
                        lp[tgt.elts[1].id] = s
                self._walk_body(mod, st.body, fqual, local, live, why, flags, parents, qual_of, lp)
                self._walk_body(mod, st.orelse, fqual, local, live, why, flags, parents, qual_of, loops)
                continue
            if isinstance(st, (ast.While,)):
                self._visit_expr(mod, st.test, fqual, local, live, why, flags, loops)
                self._walk_body(mod, st.body, fqual, local, live, why, flags, parents, qual_of, loops)
                self._walk_body(mod, st.orelse, fqual, local, live, why, flags, parents, qual_of, loops)
                continue
            if isinstance(st, (ast.With, ast.AsyncWith)):
                for it in st.items:
                    self._visit_expr(mod, it.context_expr, fqual, local, live, why, flags, loops)
                self._walk_body(mod, st.body, fqual, local, live, why, flags, parents, qual_of, loops)
                continue
            if isinstance(st, ast.Try) or type(st).__name__ == "TryStar":
                self._walk_body(mod, st.body, fqual, local, live, why, flags, parents, qual_of, loops)
                for h in st.handlers:
                    self._walk_body(mod, h.body, fqual, local, live, why, flags, parents, qual_of, loops)
                self._walk_body(mod, st.orelse, fqual, local, live, why, flags, parents, qual_of, loops)
                self._walk_body(mod, st.finalbody, fqual, local, live, why, flags, parents, qual_of, loops)
                continue
            if isinstance(st, ast.Match) if hasattr(ast, "Match") else False:
                self._visit_expr(mod, st.subject, fqual, local, live, why, flags, loops)
                for c in st.cases:
                    self._walk_body(mod, c.body, fqual, local, live, why, flags, parents, qual_of, loops)
                continue
            # a simple statement: every expression in it
            # a loop-variable assignment `q = Q.A if x else Q.B` binds a quantity name
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                qs = self._qnames(st.value, loops, mod)
                if qs:
                    loops = dict(loops)
                    loops[st.targets[0].id] = qs
            self._visit_expr(mod, st, fqual, local, live, why, flags, loops)
            if isinstance(st, ast.Return):
                v = st.value
                self._rets[f"{mod.rel}:{fqual}"].append((live, v is None or (isinstance(v, ast.Constant) and v.value is None)))
            if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                # code after a plain return is unreachable whatever the flags; it is not a flag finding. A raise is not a return value.
                return False
        return live

    # ── one statement's expressions ───────────────────────────────────────────────────────────────────────────────────────────────────
    def _visit_expr(self, mod, node, fqual, local, live, why, flags, loops):
        fkey = f"{mod.rel}:{fqual}"
        stack = [(node, live, why)]
        while stack:
            n, lv, wy = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) and n is not node:
                if isinstance(n, ast.Lambda):
                    stack.append((n.body, lv, wy))
                continue
            if isinstance(n, ast.IfExp):
                c0 = self._ctx(mod, local, fqual)
                t = _truthy(ev(n.test, c0))
                if not (c0.flags_seen or c0.preds_seen):
                    t = UNK
                stack.append((n.test, lv, wy))
                stack.append((n.body, lv and t is not False, wy or (f"`{ast.unparse(n.test)[:60]}` False by default" if t is False else "")))
                stack.append((n.orelse, lv and t is not True, wy or (f"`{ast.unparse(n.test)[:60]}` True by default" if t is True else "")))
                continue
            if isinstance(n, ast.Call):
                self._call(mod, n, fqual, fkey, local, lv, wy, flags, loops)
            if id(n) not in self._consumed_lits and (mod.stage not in (None, "tools") or mod.helper) and not self._skip_lit.get(id(n)):
                for w in self._made_words(mod, n):
                    self.reason_makes[w].append((fkey, getattr(n, "lineno", 0), lv, mod.stage))
                if isinstance(n, ast.JoinedStr) and n.values and isinstance(n.values[0], ast.Constant) and isinstance(n.values[0].value, str):
                    self.reason_prefixes.append((n.values[0].value, fkey, lv))
            if isinstance(n, (ast.Name, ast.Attribute)) and not isinstance(getattr(n, "ctx", None), ast.Store):
                nm = n.id if isinstance(n, ast.Name) else n.attr
                self._refs.setdefault(nm, 0)
                self._refs[nm] += 1
            for c in ast.iter_child_nodes(n):
                stack.append((c, lv, wy))
            if isinstance(n, ast.Compare):
                self._reason_compare(mod, n, fkey, lv)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "startswith":
                if self._is_reason_expr(n.func.value):
                    for a in n.args:
                        for w in self._lits(a, mod):
                            self.reason_tests.append((w + "*", fkey, n.lineno, mod.stage or "tools", "startswith"))
                        self._consumed_lits.update(id(x) for x in ast.walk(a))
            self._detail_read(mod, n, fkey)

    def _call(self, mod, n, fqual, fkey, local, live, why, flags, loops):
        f = n.func
        # a call to a function in the tree: a call site (for function liveness)
        tgt = resolve_callable(f, mod, self)
        names = []
        if tgt is not None:
            m2 = self.module(tgt[0])
            if m2 is not None and tgt[1] in m2.funcs:
                for d in m2.funcs[tgt[1]]:
                    names.append(f"{m2.rel}:{self._qual(m2, d)}")
        elif isinstance(f, ast.Attribute):
            self._attr_calls.setdefault(f.attr, []).append((fkey, live, why))
        for k in names:
            fi = self.funcs.get(k)
            if fi is not None:
                fi.call_sites.append((fkey, live, why))
                self._call_flags[k] |= {x for x in flags}
                if live:
                    got: Dict[Any, Tuple[str, ...]] = {}
                    for i, arg in enumerate(n.args):
                        if isinstance(arg, ast.Starred):
                            break
                        c = self._ctx(mod, local, fqual)
                        if ev(arg, c) is None and c.flags_seen:
                            got[i] = tuple(sorted(c.flags_seen))
                    for kw in n.keywords:
                        if kw.arg:
                            c = self._ctx(mod, local, fqual)
                            if ev(kw.value, c) is None and c.flags_seen:
                                got[kw.arg] = tuple(sorted(c.flags_seen))
                    self._callargs[k].append(got)
                qa: Dict[Any, List[str]] = {}
                for i, arg in enumerate(n.args):
                    if isinstance(arg, ast.Starred):
                        break
                    got_q = self._qnames(arg, loops, mod)
                    if got_q:
                        qa[i] = got_q
                for kw in n.keywords:
                    if kw.arg:
                        got_q = self._qnames(kw.value, loops, mod)
                        if got_q:
                            qa[kw.arg] = got_q
                if qa:
                    self._q_args[k].append((mod, fqual, n.lineno, live, why, tuple(flags), qa))
        # record accessors
        if isinstance(f, ast.Attribute):
            a = f.attr
            table = self.write_at if a in self.write_at else (self.read_at if a in self.read_at else None)
            if table is not None:
                idx = table[a]
                arg = n.args[idx] if len(n.args) > idx else next((k.value for k in n.keywords if k.arg == "quantity"), None)
                if arg is None:
                    return
                qs = self._qnames(arg, loops, mod)
                kind = "observe" if a == "observe" else ("abstain" if a == "abstain" else "read")
                if not qs:
                    fi0 = self.funcs.get(fkey)
                    params = [x.arg for x in (fi0.node.args.posonlyargs + fi0.node.args.args + fi0.node.args.kwonlyargs)] if fi0 else []
                    if isinstance(arg, ast.Name) and arg.id in params:
                        keys0 = tuple(sorted(k.arg for k in n.keywords if k.arg and k.arg not in _DETAIL_KW_SKIP)) if kind != "read" else ()
                        self._pending.append((fkey, arg.id, params.index(arg.id), kind, a, live, why, tuple(flags), keys0, fkey))
                    else:
                        self.unresolved.append(f"{fkey} .{a}")
                    return
                keys = tuple(sorted(k.arg for k in n.keywords if k.arg and k.arg not in _DETAIL_KW_SKIP)) if kind != "read" else ()
                owner = None
                for k in n.keywords:
                    if k.arg == "owner":
                        v = ev(k.value, self._ctx(mod, local, fqual))
                        owner = v if isinstance(v, str) else "<computed>"
                for q in qs:
                    self.sites.append(Site(mod.rel, fqual, n.lineno, mod.stage or "tools", kind, q, a, live, why, tuple(flags), keys, owner))
                for k in keys:
                    self.detail_filed[k].add(fkey)
                return
            # a Ruling / Verdict constructor or any call passing `reason=` or a reason-word first argument
        for k in n.keywords:
            if k.arg and k.arg not in _DETAIL_KW_SKIP and _is_ruling_call(f):
                self.detail_filed[k.arg].add(fkey)

    def _const_words(self, mod: Module) -> Dict[str, List[str]]:
        """{module constant name: the reason-shaped words its value holds} (a string, or a tuple / set / frozenset of strings)."""
        got = self._cw.get(mod.name)
        if got is not None:
            return got
        got = {}
        for k, v in mod.consts.items():
            words = []
            node = v
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("frozenset", "set", "tuple") and node.args:
                node = node.args[0]
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _REASON.fullmatch(node.value):
                words = [node.value]
            elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                words = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str) and _REASON.fullmatch(e.value)]
            if words:
                got[k] = words
                for x in ast.walk(v):
                    self._skip_lit[id(x)] = True        # the constant's own literal is neither a test nor a return: its USES are
        self._cw[mod.name] = got
        return got

    def _made_words(self, mod: Module, n: ast.AST) -> List[str]:
        """The reason-shaped words a node PRODUCES where it stands (a literal, or a use of a module constant holding them)."""
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and _REASON.fullmatch(n.value):
            return [n.value]
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            return self._const_words(mod).get(n.id, [])
        if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load) and isinstance(n.value, ast.Name):
            a = n.value.id
            if a in mod.aliases and self.module(mod.aliases[a]) is not None:
                return self._const_words(self.module(mod.aliases[a])).get(n.attr, [])
            if a in mod.from_names:
                src, attr = mod.from_names[a]
                m2 = self.module(src)
                if m2 is not None:
                    return self._const_words(m2).get(f"{attr}.{n.attr}", [])
            return self._const_words(mod).get(f"{a}.{n.attr}", [])
        return []

    def _qual(self, m2: Module, d: ast.AST) -> str:
        return self._node_qual.get(id(d), d.name)

    # ── reason words ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _is_reason_expr(n: ast.AST) -> bool:
        if isinstance(n, ast.Attribute) and n.attr == "reason":
            return True
        if isinstance(n, ast.Name) and n.id in ("reason", "why_reason", "rsn"):
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args and \
                isinstance(n.args[0], ast.Constant) and n.args[0].value == "reason":
            return True
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value == "reason":
            return True
        if isinstance(n, ast.BoolOp):
            return any(Analysis._is_reason_expr(v) for v in n.values)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("str", "getattr") and n.args:
            return Analysis._is_reason_expr(n.args[0]) or (n.func.id == "getattr" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant)
                                                           and n.args[1].value == "reason")
        return False

    def _lits(self, node: ast.AST, mod: Module) -> List[str]:
        """The reason-shaped string literals an expression names (a literal, a tuple / set of them, or a module constant holding them)."""
        out: List[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value] if _REASON.fullmatch(node.value) else []
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for e in node.elts:
                out += self._lits(e, mod)
            return out
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("frozenset", "set", "tuple") and node.args:
            return self._lits(node.args[0], mod)
        if isinstance(node, (ast.Name, ast.Attribute)):
            w = self._made_words(mod, node)
            if w:
                return w
        v = ev(node, Ctx(self, mod)) if isinstance(node, (ast.Name, ast.Attribute)) else UNK
        if isinstance(v, str):
            return [v] if _REASON.fullmatch(v) else []
        if isinstance(v, (tuple, frozenset)):
            return [x for x in v if isinstance(x, str) and _REASON.fullmatch(x)]
        return out

    def _reason_compare(self, mod, n: ast.Compare, fkey: str, live: bool) -> None:
        sides = [n.left] + list(n.comparators)
        if not any(self._is_reason_expr(s) for s in sides):
            return
        for s in sides:
            if self._is_reason_expr(s):
                continue
            for w in self._lits(s, mod):
                self.reason_tests.append((w, fkey, n.lineno, mod.stage or "tools", "compare"))
            self._consumed_lits.update(id(x) for x in ast.walk(s))

    def _reason_make(self, mod, n: ast.Call, fkey: str, live: bool) -> None:
        """A reason a producer can return: the `reason=` keyword, or the first / second positional string of a Ruling / Verdict constructor."""
        cands: List[ast.AST] = [k.value for k in n.keywords if k.arg == "reason"]
        f = n.func
        nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        if _is_ruling_call(f):
            if nm == "abstain" and n.args:
                cands.append(n.args[0])
            elif nm == "narrow" and len(n.args) > 1:
                cands.append(n.args[1])
            elif nm in ("decide", "decided") and len(n.args) > 1:
                cands.append(n.args[1])
        for c in cands:
            for sub in ast.walk(c):
                if isinstance(sub, ast.JoinedStr):
                    head = sub.values[0] if sub.values else None
                    if isinstance(head, ast.Constant) and isinstance(head.value, str) and head.value:
                        self.reason_prefixes.append((head.value, fkey, live))
                elif isinstance(sub, ast.Constant) and isinstance(sub.value, str) and _REASON.fullmatch(sub.value):
                    self.reason_makes[sub.value].append((fkey, n.lineno, live, mod.stage or "tools"))
                elif isinstance(sub, (ast.Name, ast.Attribute)):
                    for w in self._lits(sub, mod):
                        self.reason_makes[w].append((fkey, n.lineno, live, mod.stage or "tools"))

    # ── detail keys read ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def _detail_read(self, mod, n, fkey):
        # x.detail.get("k") / x.detail["k"] / (x.detail or {}).get("k")
        def is_detail(e):
            if isinstance(e, ast.Attribute) and e.attr == "detail":
                return True
            if isinstance(e, ast.BoolOp):
                return any(is_detail(v) for v in e.values)
            if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id in ("dict",) and e.args:
                return is_detail(e.args[0])
            return False
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args and \
                isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str) and is_detail(n.func.value):
            self.detail_read[n.args[0].value].add(fkey)
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str) and is_detail(n.value) \
                and isinstance(n.ctx, ast.Load):
            self.detail_read[n.slice.value].add(fkey)

    # ── function liveness, to a fixed point ───────────────────────────────────────────────────────────────────────────────────────────
    def _propagate(self) -> None:
        refs = self._refs
        attr_calls = self._attr_calls
        call_names = collections.Counter()
        for fi in self.funcs.values():
            call_names[fi.name] += 0
        # a function named somewhere OTHER than as a direct call (a callback, a table, a decorator's registry) is kept live
        noncall: Set[str] = set()
        for rel, mod in self.by_rel.items():
            called = set()
            for n in ast.walk(mod.tree):
                if isinstance(n, ast.Call):
                    called.add(id(n.func))
            for n in ast.walk(mod.tree):
                if id(n) in called:
                    continue
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    noncall.add(n.id)
                elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                    noncall.add(n.attr)
            for n in ast.walk(mod.tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.decorator_list:
                    noncall.add(n.name)
        changed = True
        while changed:
            changed = False
            for fi in self.funcs.values():
                if fi.dead:
                    continue
                if fi.name in noncall or fi.name.startswith("__"):
                    continue
                sites = list(fi.call_sites) + list(attr_calls.get(fi.name, ()))
                if not sites:
                    continue
                alive = [s for s in sites if s[1] and not (s[0] in self.funcs and self.funcs[s[0]].dead)]
                if alive:
                    continue
                fi.dead = True
                s0 = sites[0]
                if s0[1]:
                    fi.why = f"called only from {s0[0]}, itself not run by default" + (f" ({self.funcs[s0[0]].why})" if s0[0] in self.funcs and
                                                                                         self.funcs[s0[0]].why else "")
                else:
                    fi.why = f"called only from {s0[0]} where {s0[2]}"
                changed = True

    # ── answers ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def fn_dead(self, fkey: str) -> bool:
        fi = self.funcs.get(fkey)
        if fi is None:
            return False
        if fi.dead:
            return True
        # a nested function dies with its outer function
        if "." in fi.qual:
            outer = f"{fi.rel}:{fi.qual.rsplit('.', 1)[0]}"
            if outer in self.funcs and self.fn_dead(outer):
                return True
        return False

    def site_live(self, s: Site) -> bool:
        return s.live_local and not self.fn_dead(s.where)

    def site_why(self, s: Site) -> str:
        if not s.live_local:
            return s.why
        fi = self.funcs.get(s.where)
        while fi is not None:
            if fi.dead:
                return fi.why
            if "." not in fi.qual:
                break
            fi = self.funcs.get(f"{fi.rel}:{fi.qual.rsplit('.', 1)[0]}")
        return ""

    def fn_exists(self, rel: str, qual: str) -> bool:
        return f"{rel}:{qual}" in self.funcs

    def fn_live(self, rel: str, qual: str) -> bool:
        return self.fn_exists(rel, qual) and not self.fn_dead(f"{rel}:{qual}")

    def fn_gates(self, key: str) -> List[str]:
        """The flag predicates on the paths that call the function and on the paths inside it to its record calls, as `label=value`."""
        labels: Set[str] = set()
        for f in self._call_flags.get(key, ()):
            if f.startswith("pred:"):
                labels.add(f[5:])
        for s in self.sites:
            if s.where == key:
                labels |= {f[5:] for f in s.flags if f.startswith("pred:")}
        by = {p.label: p for p in self.predicates()}
        out = []
        for lb in sorted(labels):
            p = by.get(lb)
            if p is not None:
                out.append(f"{lb}()={_onoff(p.default)}")
            elif lb.endswith("(None by default)"):
                out.append(lb)
        return out


_REASON = re.compile(r"[a-z][a-z0-9]*(?:[_:][a-z0-9]+)+")


def _is_ruling_call(f: ast.AST) -> bool:
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("Ruling", "Verdict", "_Ruling"):
        return True
    if isinstance(f, ast.Name) and f.id in ("Ruling", "Verdict"):
        return True
    return False


def _terminates(stmts: Sequence[ast.stmt]) -> bool:
    return bool(stmts) and isinstance(stmts[-1], (ast.Return, ast.Raise, ast.Continue, ast.Break))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. per FACT (quantity): producers, consumers, status
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
LIVE = "LIVE"
READ_NEVER_FILED = "READ-BUT-NEVER-FILED"
FILED_NEVER_READ = "FILED-BUT-NEVER-READ"
OFF_FLAG = "ONLY-BEHIND-AN-OFF-FLAG"
GATHER_ONLY = "READ-ONLY-INSIDE-GATHER"
OUTSIDE = "FILED-ONLY-OUTSIDE-THE-PIPELINE"
UNUSED = "NOT-IN-USE"
STATUS_HELP = {
    LIVE: "filed by a live producer and read by a later stage",
    READ_NEVER_FILED: "a stage reads it and nothing files it (an abstention or a `wants` line is not a producer)",
    OFF_FLAG: "a stage reads it, and every row that would file it is behind a flag that is off by default",
    FILED_NEVER_READ: "filed, and read by no stage (only a tool, a human or nobody reads it)",
    GATHER_ONLY: "filed and read only inside GATHER: no later stage sees it",
    OUTSIDE: "filed only by a human reader outside the pipeline (`producers.OUT_OF_PIPELINE`), read by a stage",
    UNUSED: "named in `Q`; nothing files it and nothing reads it under the default flags",
}
_PIPE = ("GATHER", "ADJUDICATE", "EVALUATE", "INFER", "EXPORT")
STARVED = (READ_NEVER_FILED, OFF_FLAG)


def is_starved(f: "Fact") -> bool:
    """A stage reads it and no live producer files it."""
    return f.status in STARVED and bool(f.pipe_read_stages())


@dataclass
class Fact:
    q: str
    attr: str
    observe_live: List[Site] = field(default_factory=list)
    observe_dead: List[Site] = field(default_factory=list)
    abstain: List[Site] = field(default_factory=list)
    reads_live: List[Site] = field(default_factory=list)
    reads_dead: List[Site] = field(default_factory=list)
    verdict_by: List[str] = field(default_factory=list)       # "adjudicators/clef.py:adjudicate_clef"
    effect_of: List[str] = field(default_factory=list)        # "restate_pitch"
    infer_reads: List[str] = field(default_factory=list)
    infer_writes: List[str] = field(default_factory=list)
    wants: List[str] = field(default_factory=list)            # decisions that DECLARE it (a declaration, not a read)
    outside: Optional[str] = None
    status: str = UNUSED

    def has_live_producer(self) -> bool:
        return bool(self.observe_live or self.verdict_by or self.effect_of or self.infer_writes)

    def pipe_read_stages(self) -> Set[str]:
        return {s.stage for s in self.reads_live if s.stage in _PIPE} | ({"INFER"} if self.infer_reads else set())


def _rel_of_fn(fn) -> str:
    f = pathlib.Path(fn.__code__.co_filename).resolve()
    try:
        return str(f.relative_to(STAGED))
    except ValueError:
        return f.name


def _infer_rule_on(r) -> bool:
    sw = getattr(r, "switch", None)
    if sw is None:
        return True
    try:
        with default_env():
            return bool(sw())
    except Exception:                                       # noqa: BLE001
        return True


def facts(an: Analysis) -> Dict[str, Fact]:
    out: Dict[str, Fact] = {q: Fact(q, an.q_name[q]) for q in sorted(an.q_vals)}
    for s in an.sites:
        f = out.get(s.quantity)
        if f is None:
            continue
        live = an.site_live(s)
        if s.kind == "observe":
            (f.observe_live if live else f.observe_dead).append(s)
        elif s.kind == "abstain":
            f.abstain.append(s)
        else:
            (f.reads_live if live else f.reads_dead).append(s)
    if an.registry and an.real:
        from . import adjudicate, evaluate, infer
        for m in ("adjudicators", "consequences", "inferences"):
            importlib.import_module(f"{BASE_PKG}.{m}")
        for q, spec in adjudicate.REGISTRY.items():
            if q in out and not getattr(spec, "stub", False):
                out[q].verdict_by.append(f"{_rel_of_fn(spec.fn)}:{spec.fn.__name__}")
            for w in spec.wants:
                if w in out:
                    out[w].wants.append(spec.fn.__name__)
        for r in evaluate.RULES:
            if not getattr(r, "stub", False) and r.effect in out:
                out[r.effect].effect_of.append(r.consequence.value)
        for r in getattr(infer, "RULES", []):
            if not _infer_rule_on(r):
                continue
            name = getattr(r.fn, "__name__", str(getattr(r, "inference", "?")))
            for q in getattr(r, "reads", ()):
                if q in out:
                    out[q].infer_reads.append(name)
            tq = getattr(r, "target", None)
            if tq in out and not getattr(r, "stub", False):
                out[tq].infer_writes.append(name)
        try:
            from . import producers as _OOP
            for q, rel in _OOP.all_filed().items():
                if q in out:
                    out[q].outside = rel
        except Exception:                                   # noqa: BLE001 -- `staged.producers` owns that failure
            pass
    for f in out.values():
        stages = f.pipe_read_stages()
        if stages:
            if f.has_live_producer():
                f.status = GATHER_ONLY if stages == {"GATHER"} and not (f.verdict_by or f.effect_of) else LIVE
            elif f.outside:
                f.status = OUTSIDE
            elif f.observe_dead:
                f.status = OFF_FLAG
            else:
                f.status = READ_NEVER_FILED
        elif f.has_live_producer():
            f.status = FILED_NEVER_READ
        elif f.observe_dead:
            f.status = OFF_FLAG
        else:
            f.status = UNUSED
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 6. reason words: what consumers test against what deciders can still return
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class ReasonGap:
    word: str
    tested_at: List[str]          # "rel:func:line"
    kind: str                     # "never returned" / "returned only behind an off flag"
    made_at: List[str]


def reason_gaps(an: Analysis) -> List[ReasonGap]:
    """Every literal reason word a live consumer tests that no stage can return (or returns only in code off by default)."""
    skip = {m.rel for m in an.by_rel.values() if m.derived_check} | {"flow_map.py", "reach.py"}
    by_word: Dict[str, List[str]] = collections.defaultdict(list)
    for w, fkey, line, stage, how in an.reason_tests:
        if fkey.split(":")[0] in skip or an.fn_dead(fkey):
            continue
        by_word[w].append(fkey)
    out = []
    for w, at in sorted(by_word.items()):
        if w.endswith("*"):
            pre = w[:-1]
            made = [x for k, v in an.reason_makes.items() if k.startswith(pre) for x in v]
            pref = [p for p in an.reason_prefixes if p[0].startswith(pre) or pre.startswith(p[0])]
            if any(x[2] and not an.fn_dead(x[0]) for x in made) or any(p[2] and not an.fn_dead(p[1]) for p in pref):
                continue
        else:
            made = an.reason_makes.get(w, [])
            pref = [p for p in an.reason_prefixes if w.startswith(p[0]) and len(p[0]) >= 4]
            if any(x[2] and not an.fn_dead(x[0]) for x in made) or any(p[2] and not an.fn_dead(p[1]) for p in pref):
                continue
        kind = "returned only behind an off flag" if made else "returned by nothing"
        out.append(ReasonGap(w.rstrip("*") + ("*" if w.endswith("*") else ""), sorted(set(at)), kind,
                             sorted({x[0] for x in made})))
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. detail keys: read against filed
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
def detail_gaps(an: Analysis) -> List[Tuple[str, List[str]]]:
    """Detail keys a live stage reads off a row's `detail` that no code anywhere files under that name (a kwarg of `observe`/`abstain`/a
    Ruling, or any dict key or subscript store in a stage module). Bare-name matching, so this can only UNDER-report."""
    filed: Set[str] = set(an.detail_filed)
    for m in an.by_rel.values():
        if m.stage in (None, "tools"):
            continue
        for n in ast.walk(m.tree):
            if isinstance(n, ast.Dict):
                for k in n.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        filed.add(k.value)
            elif isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store) and isinstance(n.slice, ast.Constant):
                filed.add(str(n.slice.value))
            elif isinstance(n, ast.Call):
                for k in n.keywords:
                    if k.arg:
                        filed.add(k.arg)
                if isinstance(n.func, ast.Attribute) and n.func.attr in ("setdefault", "update", "__setitem__") and n.args and \
                        isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                    filed.add(n.args[0].value)
    skip = {m.rel for m in an.by_rel.values() if m.derived_check}
    out = []
    for k, where in sorted(an.detail_read.items()):
        live = sorted(w for w in where if w.split(":")[0] not in skip and not an.fn_dead(w) and an.by_rel[w.split(":")[0]].stage in _PIPE)
        if live and k not in filed:
            out.append((k, live))
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. THE ONE DECLARED TABLE: what only a person can say about each mark
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#: how a reader finds its mark. `ink` = the page or cell raster itself; `box` = a detector box (a box the detector never drew has no subject);
#: `box+ink` = a detector box measured against its own ink; `text` = OCR; `catalog` = a fact not read off this raster; `record` = bookkeeping on
#: rows already filed.
FOUND = ("ink", "box", "box+ink", "text", "catalog", "record")


@dataclass(frozen=True)
class Mark:
    key: str                                  # `--mark KEY`
    name: str
    plain: str                                # one line a musician can follow
    readers: Dict[str, str]                   # "file:function" -> FOUND (":only=q1,q2" limits a shared reader to those facts)
    deciders: Tuple[str, ...] = ()            # registered ADJUDICATE decisions (function names)
    claims: Tuple[str, ...] = ()              # claim families (stroke_owner TIERS / CONSUMERS, claim_order LAYERS)
    old: Tuple[str, ...] = ()                 # old readers still in the tree beside the new one ("file:function" or a decision name)
    written: str = ""                         # what the file shows, and how uncertainty shows
    new: Tuple[str, ...] = ()                 # the reader that replaced the old ones (for the double-feed question)


G = "gather.py:"
MARKS: Tuple[Mark, ...] = (
    Mark("clef", "Clef", "The sign at a staff's start (and where it changes) that says which line is which note.",
         {G + "gather_clef_pagewide": "ink", G + "_gather_clef_header_by_ink": "ink", G + "gather_clef_slot_claim": "ink",
          G + "gather_clef_seed": "catalog"},
         ("adjudicate_clef",), ("clef",), (),
         "`<clef>` at the start and at each change; a clef it cannot read leaves its bars red and their heads unwritten."),
    Mark("key", "Key signature", "The sharps or flats after the clef, in their fixed order.",
         {G + "gather_key_signature": "box", G + "_gather_keysig_markers": "box", G + "_gather_keysig_template": "ink",
          G + "gather_key_signature_claim": "box+ink", G + "gather_key_object": "ink"},
         ("adjudicate_key_signature", "adjudicate_system_key", "adjudicate_part_key", "adjudicate_keysig_marker_is_not_a_marker"),
         ("key_signature",), (), "`<key>`; the sounding `<alter>` of every note follows it."),
    Mark("meter", "Time signature", "The two numbers (or C) that say how long a bar is.",
         {G + "gather_meter": "ink", G + "gather_meter_at_bars": "ink", G + "_gather_meter_glyphs": "box",
          G + "_gather_meter_ocr_header": "text", G + "gather_meter_ocr_at_bars": "text", G + "gather_meter_object": "ink",
          "positions.py:gather_meter_positions": "box"},
         ("adjudicate_meter",), ("meter",), (), "`<time>`; a change holds until the printed return."),
    Mark("header", "Header column", "The clef-key-meter block at the start of each staff, claimed as one area.",
         {G + "gather_claimed_register": "ink"}, (), ("leading_column",), (), "nothing of its own: it keeps other readers off the header's ink."),
    Mark("notehead", "Notehead", "The oval of a note; the line or space it sits on is the pitch.",
         {G + "gather_notehead_positions": "box+ink", G + "gather_notehead_recentre": "box+ink", G + "gather_head_line_cut": "box+ink",
          G + "gather_notehead_ink": "box+ink", G + "gather_head_ink": "box+ink", G + "gather_head_oval": "box+ink",
          G + "gather_stacked_head_fit": "box+ink", G + "gather_narrow_box_shape": "box+ink", G + "gather_notehead_letter_ink": "box+ink",
          G + "gather_notehead_stem_cross_ink": "box+ink", G + "gather_head_stem_reach": "box+ink", G + "_file_mark_groups": "record",
          "page_heads.py:file_one_claims": "ink", "page_heads.py:file_page_heads": "ink", G + "gather_lowconf_rescue": "box",
          G + "_lowconf_rescue_witnesses": "record", G + "gather_detector_views": "box", G + "gather_dyad_head_rescue": "box",
          G + "gather_stem_end_heads": "box", G + "_stem_end_head_ink": "ink", G + "gather_second_hollow": "box",
          G + "gather_ownership_evidence": "box+ink", G + "_gather_owner_candidates": "box+ink"},
         ("adjudicate_notehead_is_not_a_notehead", "adjudicate_notehead_position", "adjudicate_glyph_owner", "adjudicate_event",
          "adjudicate_onset_column"),
         ("head",), (G + "cluster_marks", "page_marks.py:link"),
         "one `<note>` per head: plain when READ, blue when GUESSED; a bar it cannot read is marked red and nothing is invented."),
    Mark("ledger", "Ledger line", "The short line above or below the staff that names a far note's pitch.",
         {G + "_file_far_head_reading": "box+ink", G + "_file_owner_ledger_readings": "box+ink", G + "gather_ledger_ink": "box+ink",
          G + "_observe_ledger_rung_ink": "ink", G + "_observe_ledger_owner_density": "ink", G + "_observe_ladder": "box"},
         ("adjudicate_ledger_is_not_a_ledger",), ("ledger",), (),
         "no element of its own: it places a far head (plain where the count decides, blue where it abstains)."),
    Mark("stem", "Stem", "The vertical line on a head; up on the right, down on the left.",
         {G + "gather_cv_lines": "ink:only=stem,vertical_run", G + "_stub_cv_lines": "record:only=stem", G + "_observe_stem_tip_ink": "ink",
          G + "_emit_vertical_runs": "ink"},
         ("adjudicate_stem_direction", "adjudicate_stem_head_contact", "adjudicate_head_stem", "adjudicate_stem_value"),
         ("stem",), (), "`<stem>` direction; every note on one stem shares one value."),
    Mark("beam", "Beam", "The thick bar joining stems; each beam halves the value.",
         {G + "gather_cv_lines": "ink:only=beam_stroke", G + "_stub_cv_lines": "record:only=beam_stroke", G + "gather_detector_beams": "box",
          G + "gather_beam_stem_levels": "ink", G + "gather_beam_stroke_ink": "ink", G + "_observe_beam_stem_join": "ink",
          "page_beams.py:gather_page_beams": "ink", "page_beams.py:gather_page_beam_views": "ink"},
         ("adjudicate_duration",), ("beam",), ("adjudicators/rhythm.py:_beam_levels", "adjudicators/rhythm.py:_stem_tip_strokes"),
         "`<beam>` groups and the note values; a note the count cannot settle is narrowed and marked."),
    Mark("flag", "Flag", "The hook on a lone stem; each hook halves the value.",
         {G + "gather_rhythm_marks": "box:only=flag"}, ("adjudicate_flag_is_not_a_flag", "adjudicate_duration"), ("flag",), (),
         "the note value (an eighth or shorter); a flagged note is never put in a beam group."),
    Mark("rest", "Rest", "A silence of a written length; a whole rest means the whole bar.",
         {G + "gather_glyph_families": "box:only=rest", G + "gather_rest_ink_contact": "box+ink", G + "gather_unboxed_rest_ink": "ink",
          G + "gather_empty_bar_rest_search": "ink"},
         ("adjudicate_rest_is_not_a_rest", "adjudicate_unboxed_ink_is_a_rest", "adjudicate_head_ink_is_a_rest",
          "adjudicate_notehead_is_a_whole_rest", "adjudicate_empty_bar_whole_rest", "adjudicate_narrow_box_is_an_eighth_rest"),
         ("rest", "whole_rest"), (), "`<rest>`; a whole rest fills the bar, plain or blue."),
    Mark("dot", "Dot", "The dot after a head that adds half its value.",
         {G + "gather_rhythm_marks": "box:only=aug_dot", G + "gather_dot_positions": "box+ink", G + "_observe_dot_stroke_ink": "ink"},
         ("adjudicate_dot_role",), ("dot",), (), "`<dot>` on the note it lengthens."),
    Mark("accidental", "Accidental", "A sharp, flat or natural in front of a head.",
         {G + "gather_accidental_positions": "box", G + "file_accidental_position": "box+ink",
          "page_accidental_ink.py:gather_page_accidental_ink": "ink"},
         ("adjudicate_accidental_owner", "adjudicate_accidental_is_not_an_accidental"), ("accidental", "accidental_ink"), (),
         "`<accidental>` and the sounding `<alter>`, READ or GUESSED."),
    Mark("arc", "Tie and slur", "A curve over notes: the nearer of stacked arcs is the tie.",
         {G + "gather_glyph_families": "box:only=arc_box", "arcs_system.py:gather_system_arcs": "box+ink", G + "gather_arc_claim": "record",
          G + "gather_arc_ink": "box+ink", "arc_strip.py:gather_arc_strip": "box", "page_arcs.py:gather_page_arcs": "ink"},
         ("adjudicate_arc_owner", "adjudicate_arc_kind", "adjudicate_tie_pair", "adjudicate_page_arc_binding", "adjudicate_arc_is_not_an_arc"),
         ("arc", "arc_trace"), ("arcs_system.py:gather_system_arcs", G + "gather_arc_claim", "adjudicate_arc_owner", "adjudicate_arc_kind",
                                "adjudicate_tie_pair"),
         "`<slur>` / `<tied>` on the two written heads.", ("page_arcs.py:gather_page_arcs", "adjudicate_page_arc_binding")),
    Mark("hairpin", "Hairpin", "The opening or closing wedge between staves (crescendo / diminuendo).",
         {G + "gather_wedge_boxes": "box+ink", G + "gather_hairpin_claim": "ink", G + "gather_wedge_rescue": "box",
          "positions.py:gather_band_positions": "box:only=wedge_band_position"},
         ("adjudicate_wedge_anchor",), ("hairpin", "hairpin_trace"), (), "`<wedge>` on two written notes, where the anchor is decided."),
    Mark("dynamic", "Dynamic", "The letters p, f, sf ... under a staff.",
         {G + "gather_dynamic_letters": "box", G + "gather_letter_look": "box+ink",
          "positions.py:gather_band_positions": "box:only=dynamic_band_position"},
         ("adjudicate_dynamic", "adjudicate_dynamic_anchor", "adjudicate_dynamic_is_not_a_dynamic"), ("dynamic",), (),
         "`<dynamics>` in its bar."),
    Mark("word", "Word", "A printed word in the music: legato, Allegro con brio.",
         {G + "gather_direction_words": "text", G + "_direction_cells_abstain": "record", G + "gather_page_claims": "record",
          "positions.py:gather_band_positions": "box:only=direction_band_position"},
         ("adjudicate_direction",), ("word", "text"), (), "`<words>`: plain, blue when GUESSED, red when UNREAD."),
    Mark("articulation", "Articulation", "A staccato dot, accent or tenuto on a note.",
         {G + "gather_glyph_families": "box:only=articulation_mark", G + "_observe_mark_shape": "box+ink", G + "gather_mark_shapes": "box+ink"},
         ("adjudicate_articulation_owner", "adjudicate_articulation_is_not_an_articulation"), ("mark",), (), ""),
    Mark("fermata", "Fermata", "The pause sign over a note.", {G + "gather_glyph_families": "box:only=fermata_mark"},
         ("adjudicate_fermata_owner",), (), (), ""),
    Mark("ornament", "Ornament", "A trill, turn or mordent sign.", {G + "gather_glyph_families": "box:only=ornament_mark"},
         ("adjudicate_ornament_owner",), (), (), ""),
    Mark("tremolo", "Tremolo slash", "A slash through a stem that repeats the note.",
         {"page_tremolo.py:gather_page_tremolo": "ink", G + "_observe_stem_slashes": "ink"}, (), ("tremolo",), (), ""),
    Mark("tuplet", "Tuplet", "The 3 (or 5, 6 ...) over a group; a tuplet exists only where its marking is seen.",
         {G + "gather_rhythm_marks": "box:only=tuplet_marker"}, ("adjudicate_tuplet", "adjudicate_tuplet_marker_is_not_a_marker"), (), (), ""),
    Mark("barline", "Barline", "The vertical line that ends a bar.",
         {G + "gather_measures": "ink", G + "gather_barline_claim": "ink", "barline_columns.py:gather_barline_columns": "ink"},
         ("adjudicate_measure_partition",), ("barline",), (), "the `<measure>` boundaries."),
    Mark("bracket", "Bracket and brace", "The bracket or brace that groups staves at the left.",
         {G + "_gather_bracket_blocks": "ink", G + "gather_page_claims": "record"}, ("adjudicate_staff_group", "adjudicate_group_symbol"),
         ("bracket",), (), ""),
    Mark("repeat", "Repeat and ending", "Repeat dots at a barline; the 1st / 2nd ending brackets.",
         {G + "gather_repeat_dots": "ink", G + "gather_volta_brackets": "ink", G + "gather_volta_numerals": "text"},
         ("adjudicate_repeat_barlines", "adjudicate_endings"), (), (), ""),
    Mark("barnumber", "Bar number", "The small number printed above a system.",
         {G + "gather_printed_bar_numbers": "text", G + "_printed_bar_numbers_surya": "text"}, ("adjudicate_printed_bar_number",), (), (), ""),
    Mark("instrument", "Instrument name", "The name in the left margin that says which part a staff is.",
         {G + "gather_margin_labels": "text", G + "_labels_abstain_per_staff": "record", G + "gather_external": "catalog"},
         ("adjudicate_instrument", "adjudicate_slot_index", "adjudicate_part_partition"), (), (),
         "`<part-name>`; a staff that cannot be named is held out of the file and counted."),
    Mark("staff", "Staff and system", "The five lines of a part, and the staves played together as one system.",
         {G + "gather_geometry": "ink", G + "gather_systems": "ink"},
         ("adjudicate_system_membership", "adjudicate_system_staff_count", "adjudicate_staff_ordinal"), ("staff_line",), (), ""),
    Mark("voices", "Voices", "Two lines of music on one staff (stems up and down).", {}, ("adjudicate_voices", "adjudicate_unison_voices"),
         (), (), ""),
    Mark("other", "Arpeggio, pedal, ottava", "Marks the file does not yet write in full.", {},
         ("adjudicate_arpeggiato_is_not_an_arpeggiato", "adjudicate_pedal_owner", "adjudicate_ottava_owner"), (), (), ""),
    Mark("ink", "Page ink (every stroke)", "Every stroke on the page, before it is any mark; who owns each stroke.",
         {G + "gather_ink": "ink", G + "gather_cell_ink_pieces": "ink", G + "gather_stroke_map": "ink", G + "gather_glyph_strokes": "box+ink",
          "page_strokes.py:gather_page_strokes": "ink", G + "_file_ink_claim": "record", "page_claim_names.py:gather_page_claim_names": "record",
          "page_claim_names.py:gather_page_claim_boxes": "box"},
         ("adjudicate_stroke_owner",), (), (), "nothing of its own: it decides which mark each stroke belongs to."),
    Mark("box", "Detector boxes (every mark)", "The boxes the detector draws for every kind of mark; a box is where to look.",
         {G + "gather_detections": "box", "page_marks.py:gather_page_marks": "box", "page_owner.py:_file_page_owners": "box",
          "positions.py:gather_step_positions": "box"},
         ("adjudicate_unread_mark",), (), (), "an unread box is counted, never written as a mark."),
    Mark("document", "The printing", "Which edition and movement this is; scanned or engraved.",
         {G + "gather_document_identity": "catalog", G + "gather_input_domain": "ink", G + "gather_movements": "record"},
         ("adjudicate_movement_start",), (), (), ""),
)
MARK_BY_KEY = {m.key: m for m in MARKS}


def _reader_found(v: str) -> Tuple[str, Optional[Set[str]]]:
    found, _, only = v.partition(":only=")
    return found, (set(only.split(",")) if only else None)


def _covers(listed: Set[str], key: str) -> bool:
    """A listed function covers itself and every function nested in it."""
    rel, _, qual = key.partition(":")
    parts = qual.split(".")
    return any(f"{rel}:{'.'.join(parts[:i])}" in listed for i in range(1, len(parts) + 1))


def table_problems(an: Analysis) -> List[str]:
    """The declared table against the code. Empty, or the build fails."""
    out: List[str] = []
    listed = {k for m in MARKS for k in m.readers}
    for m in MARKS:
        for k, v in m.readers.items():
            if k not in an.funcs:
                out.append(f"mark `{m.key}` names a reader that no longer exists: {k}")
            found, only = _reader_found(v)
            if found not in FOUND:
                out.append(f"mark `{m.key}`: reader {k} has an unknown `found from` {found!r}")
            for q in (only or ()):
                if q not in an.q_vals:
                    out.append(f"mark `{m.key}`: reader {k} limits to an unknown fact {q!r}")
        for o in m.old:
            if ":" in o and o not in an.funcs:
                out.append(f"mark `{m.key}` names an old reader that no longer exists: {o}")
    filers = {s.where for s in an.sites if s.kind != "read" and s.stage == "GATHER"}
    for k in sorted(filers):
        if not _covers(listed, k):
            out.append(f"a GATHER function files rows and is in no mark: {k} (add it to `flow_map.MARKS`)")
    if an.real and an.registry:
        from . import adjudicate
        importlib.import_module(f"{BASE_PKG}.adjudicators")
        names = {s.fn.__name__ for s in adjudicate.REGISTRY.values()}
        declared = {d for m in MARKS for d in m.deciders}
        for d in sorted(names - declared):
            out.append(f"a registered decision is in no mark: {d} (add it to `flow_map.MARKS`)")
        for d in sorted(declared - names):
            out.append(f"a mark names a decision the registry no longer has: {d}")
        for m in MARKS:
            for o in m.old:
                if ":" not in o and o not in names:
                    out.append(f"mark `{m.key}` names an old decision the registry no longer has: {o}")
        fams = set(claim_families())
        for m in MARKS:
            for c in m.claims:
                if c not in fams:
                    out.append(f"mark `{m.key}` names a claim family the code no longer has: {c}")
        owned = {c for m in MARKS for c in m.claims}
        for c in sorted(fams - owned):
            out.append(f"a claim family is in no mark: {c} (add it to a mark's `claims` in `flow_map.MARKS`)")
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. the claims register, as the code resolves it under the defaults
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
def claim_families() -> List[str]:
    from . import claim_order as CO, stroke_owner as SO
    out: List[str] = []
    for fams in list(SO.TIERS) + [SO.CONSUMERS]:
        out += [f for f in fams if f not in out]
    for _n, fams, _c in CO.LAYERS:
        out += [f for f in fams if f not in out]
    for n, fams, _c in CO.LAYERS:
        if not fams and n not in out:
            out.append(n)
    return out


@dataclass
class ClaimRow:
    family: str
    tier: Optional[int]
    tier_of: int
    layer: Optional[int]
    layer_of: int
    layer_name: str
    consulted: bool              # refused by the register consult (`claimed_by._ORDER`)
    mark_only: bool              # `claim_final.mark_only()` under the defaults
    filers: List[Tuple[str, bool, str]]        # (rel:func, live, why) of Q.CLAIMED_AREA rows filing this owner
    by_box: bool                 # a detector-box family the stroke owner claims for directly


def claims_register(an: Analysis) -> List[ClaimRow]:
    from . import claim_final as CF, claim_order as CO, stroke_owner as SO
    from .adjudicators import claimed_by as CB
    with default_env():
        mo = set(CF.mark_only())
    consulted = set(CB._ORDER)
    tier = {}
    for t, fams in enumerate(SO.TIERS):
        for f in fams:
            tier.setdefault(f, t)
    for f in SO.CONSUMERS:
        tier.setdefault(f, len(SO.TIERS))
    layer = {}
    for i, (n, fams, _c) in enumerate(CO.LAYERS):
        for f in fams:
            layer.setdefault(f, (i, n))
        if not fams:
            layer.setdefault(n, (i, n))
    filers: Dict[str, List[Tuple[str, bool, str]]] = collections.defaultdict(list)
    for s in an.sites:
        if s.quantity == "claimed_area" and s.kind == "observe" and s.owner:
            filers[s.owner].append((s.where, an.site_live(s), an.site_why(s)))
    out = []
    for f in claim_families():
        li = layer.get(f)
        out.append(ClaimRow(f, tier.get(f), len(SO.TIERS) + 1, li[0] if li else None, len(CO.LAYERS), li[1] if li else "-",
                            f in consulted, f in mo, sorted(set(filers.get(f, ()))), f not in SO.AREA_OWNERS and f in tier))
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. the gaps (PART 3), every one derived
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Gap:
    kind: str
    subject: str                 # a fact, a reason word, a function
    text: str
    where: List[str]
    marks: List[str]


GAP_KINDS = (
    ("starved", "STARVED CONSUMER: a stage reads a fact nothing files under the default flags"),
    ("old_feeds", "OLD READER BESIDE A NEW ONE: an old reader still runs and a later step still reads what it files"),
    ("double_fed", "DOUBLE-FED CONSUMER: one function reads the same mark from the old reader and the new one"),
    ("dead_reason", "DEAD REASON WORD: a consumer tests a reason word no decider can return under the default flags"),
    ("dead_detail", "DETAIL KEY READ, NEVER FILED: a stage reads a detail key no code files"),
    ("unread", "FILED, NEVER READ BY A STAGE: a live producer whose fact no stage reads (a human or a tool may)"),
    ("off_flag", "PRODUCER ONLY BEHIND AN OFF FLAG: a fact filed only by code that does not run by default"),
    ("stale_doc", "STALE FLAG TEXT: a docstring says a flag's default is the opposite of what the code returns"),
)


def _marks_of_fact(q: str, an: Analysis, fs: Dict[str, Fact]) -> List[str]:
    out = []
    for m in MARKS:
        if q in mark_facts(m, an, fs):
            out.append(m.key)
    return out


def mark_facts(m: Mark, an: Analysis, fs: Dict[str, Fact]) -> Set[str]:
    got: Set[str] = set()
    listed = {k: _reader_found(v)[1] for k, v in m.readers.items()}
    for s in an.sites:
        if s.kind == "read":
            continue
        for k, only in listed.items():
            if _covers({k}, s.where) and (only is None or s.quantity in only):
                got.add(s.quantity)
    for f in fs.values():
        for v in f.verdict_by:
            if v.split(":")[-1] in m.deciders:
                got.add(f.q)
    return got


def shared_facts(an: Analysis, fs: Dict[str, Fact]) -> Set[str]:
    """Facts three or more marks file (`claimed_area`, `glyph_box` ...): a consumer of one reads every mark's rows and filters them itself, so
    they are shown once (`--quantity`) and never counted as one mark's feed."""
    if "_shared" in _CACHE_FACTS:
        return _CACHE_FACTS["_shared"]
    c = collections.Counter(q for m in MARKS for q in mark_facts(m, an, fs))
    out = {q for q, n in c.items() if n >= 3}
    _CACHE_FACTS["_shared"] = out
    return out


_CACHE_FACTS: Dict[str, Any] = {}


def _filed_by(o: str, an: Analysis, fs: Dict[str, Fact]) -> Set[str]:
    if ":" in o:
        return {s.quantity for s in an.sites if s.kind != "read" and _covers({o}, s.where)}
    return {f.q for f in fs.values() if any(v.endswith(":" + o) for v in f.verdict_by)}


def old_facts(m: Mark, an: Analysis, fs: Dict[str, Fact]) -> Dict[str, Set[str]]:
    """{old reader: the facts only the old readers file} (a fact the new readers also file, or a shared fact, is not the old reader's)."""
    sh = shared_facts(an, fs)
    news: Set[str] = set()
    for k in list(m.readers) + list(m.deciders):
        if k not in m.old:
            news |= _filed_by(k, an, fs)
    return {o: _filed_by(o, an, fs) - news - sh for o in m.old}


def new_facts(m: Mark, an: Analysis, fs: Dict[str, Fact]) -> Set[str]:
    sh = shared_facts(an, fs)
    out: Set[str] = set()
    for k in m.new:
        out |= _filed_by(k, an, fs)
    return out - sh


def _callees(an: Analysis) -> Dict[str, Set[str]]:
    if "_callees" in _CACHE_FACTS:
        return _CACHE_FACTS["_callees"]
    out: Dict[str, Set[str]] = collections.defaultdict(set)
    for k, fi in an.funcs.items():
        for caller, live, _w in fi.call_sites:
            if live:
                out[caller].add(k)
    _CACHE_FACTS["_callees"] = out
    return out


_DOC_DEFAULT = re.compile(r"`?(OMR_[A-Z0-9_]+)`?[^.;\n]{0,40}?default\s+(ON|OFF)", re.I)


def stale_flag_text(an: Analysis) -> List[Tuple[str, str, str, Any]]:
    """(file:function, flag, says, is) where a docstring of a stage or helper module names a flag's default wrongly."""
    one: Dict[str, Set[Any]] = collections.defaultdict(set)
    for p in an.predicates():
        if len(p.flags) == 1 and isinstance(p.default, bool):
            one[p.flags[0]].add(p.default)
    default = {k: next(iter(v)) for k, v in one.items() if len(v) == 1}
    out = []
    for m in an.by_rel.values():
        if m.stage in (None, "tools") and not m.helper:
            continue
        nodes = [("<module>", m.tree)] + [(fi.qual, fi.node) for fi in an.funcs.values() if fi.rel == m.rel]
        for qual, node in nodes:
            doc = ast.get_docstring(node) or ""
            for mt in _DOC_DEFAULT.finditer(doc):
                flag, says = mt.group(1), mt.group(2).upper()
                window = doc[max(0, mt.start() - 30): mt.end() + 30].lower()
                if any(w in window for w in ("until", "was default", "used to", "before", "formerly", "flipped", "landed")):
                    continue
                if flag in default and (says == "ON") != default[flag]:
                    out.append((f"{m.rel}:{qual}", flag, says, default[flag]))
    return sorted(set(out))


def gaps(an: Analysis, fs: Dict[str, Fact]) -> List[Gap]:
    out: List[Gap] = []
    for f in fs.values():
        if is_starved(f):
            cons = sorted({s.where for s in f.reads_live if s.stage in _PIPE}) + [f"INFER {x}" for x in f.infer_reads]
            why = ("every row that would file it is behind an off flag: " + "; ".join(sorted({f"{s.where} ({an.site_why(s)})" for s in f.observe_dead}))
                   if f.status == OFF_FLAG else "nothing files it (" + (f"abstentions only: {len(f.abstain)}" if f.abstain else "no row at all") +
                   (f"; declared in `wants` by {', '.join(sorted(set(f.wants)))}" if f.wants else "") + ")")
            out.append(Gap("starved", f.q, f"`{f.q}` is read and {why}", cons, _marks_of_fact(f.q, an, fs)))
    reads_of: Dict[str, Set[str]] = collections.defaultdict(set)
    for f in fs.values():
        for s0 in f.reads_live:
            reads_of[s0.where].add(f.q)
    callees = _callees(an)
    reg = {r.family: r for r in claims_register(an)}
    for m in MARKS:
        olds = old_facts(m, an, fs)
        for o, qs in olds.items():
            live = an.fn_live(*o.split(":", 1)) if ":" in o else True
            if not live:
                continue
            callers = sorted({c for c, lv, _w in an.funcs[o].call_sites if lv and not an.fn_dead(c)}) if ":" in o else []
            later = sorted({s0.where for q in qs for s0 in fs[q].reads_live if s0.stage in ("ADJUDICATE", "EVALUATE", "INFER", "EXPORT")
                            and s0.where.split(":")[-1] not in m.deciders and not any(_covers({k}, s0.where) for k in m.readers)})
            owners = sorted({s0.owner for s0 in an.sites if s0.quantity == "claimed_area" and s0.kind == "observe" and s0.owner
                             and ":" in o and _covers({o}, s0.where) and an.site_live(s0)})
            claim = "".join(f"; it still claims ink as `{w}`, which " + ("only marks" if reg[w].mark_only else "OWNS it (a later box mostly on it is refused)")
                            for w in owners if w in reg)
            if qs and later:
                out.append(Gap("old_feeds", o, f"old {m.name.lower()} reader `{o}` still runs; what only the old path files "
                                               f"({', '.join(f'`{q}`' for q in sorted(qs))}) is read by {len(later)} later function(s){claim}", later, [m.key]))
            else:
                out.append(Gap("old_feeds", o, f"old {m.name.lower()} reader `{o}` still runs by default" +
                                               (f" (called from {_short(callers, 3)})" if callers else "") +
                                               (("; what it files is only shared facts (" + ", ".join(f"`{q}`" for q in sorted(_filed_by(o, an, fs))) + ")")
                                                if _filed_by(o, an, fs) and not qs else ("; it files no row of its own" if not qs else "")) + claim, [o], [m.key]))
        if m.old and m.new:
            old_q = {q for v in olds.values() for q in v}
            new_q = new_facts(m, an, fs)
            cand = [k for k, fi in an.funcs.items() if an.by_rel[fi.rel].stage in ("ADJUDICATE", "EVALUATE", "INFER", "EXPORT")
                    and not an.fn_dead(k) and fi.name not in m.deciders and fi.name not in m.old]
            for w in sorted(cand):
                direct = reads_of.get(w, set())
                kids = [reads_of.get(c, set()) for c in callees.get(w, ())]
                allr = direct.union(*kids) if kids else set(direct)
                if not (allr & old_q and allr & new_q):
                    continue
                if any(k0 & old_q and k0 & new_q for k0 in kids):
                    continue                     # a callee is the meeting point; it is listed itself
                out.append(Gap("double_fed", w, f"`{w}` meets the {m.name.lower()} from the old path ({', '.join(f'`{q}`' for q in sorted(allr & old_q))}) "
                                                f"and from the new one ({', '.join(f'`{q}`' for q in sorted(allr & new_q))})"
                                                + ("" if direct & old_q and direct & new_q else " through the functions it calls"), [w], [m.key]))
    for g in reason_gaps(an):
        out.append(Gap("dead_reason", g.word, f"reason `{g.word}` is tested and {g.kind}" + (f" ({', '.join(g.made_at[:3])})" if g.made_at else ""),
                       g.tested_at, []))
    for k, where in detail_gaps(an):
        out.append(Gap("dead_detail", k, f"detail key `{k}` is read and filed by nothing", where, []))
    for f in fs.values():
        if f.status == FILED_NEVER_READ:
            tools = sorted({s.where for s in f.reads_live if s.stage not in _PIPE})
            out.append(Gap("unread", f.q, f"`{f.q}` is filed and read by no stage" + (f" (tools: {len(tools)})" if tools else ""),
                           sorted({s.where for s in f.observe_live}) + [f"ADJUDICATE {v}" for v in f.verdict_by], _marks_of_fact(f.q, an, fs)))
        elif f.status == OFF_FLAG and not f.pipe_read_stages():
            out.append(Gap("off_flag", f.q, f"`{f.q}` is filed only by code off by default, and nothing reads it",
                           sorted({f"{s.where} ({an.site_why(s)})" for s in f.observe_dead}), _marks_of_fact(f.q, an, fs)))
    for w, flag, says, is_ in stale_flag_text(an):
        out.append(Gap("stale_doc", f"{w} {flag}", f"`{w}` says `{flag}` is default {says}; the code returns {_onoff(is_)}", [w], []))
    return out


def _onoff(v: Any) -> str:
    if v is True:
        return "ON"
    if v is False:
        return "OFF"
    return repr(v)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. the page
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
_CMD = "python3 -m tools.omr.staged.flow_map"
_MAX = 8                                       # names shown per stage in a mark block; `--quantity` shows all


def _short(items: Sequence[str], n: int = _MAX) -> str:
    items = list(items)
    s = ", ".join(f"`{x}`" for x in items[:n])
    return s + (f" +{len(items) - n} more" if len(items) > n else "")


def mark_block(m: Mark, an: Analysis, fs: Dict[str, Fact], gp: List[Gap], reg: List[ClaimRow]) -> List[str]:
    L = [f"### {m.name} -- `--mark {m.key}`", "", m.plain, ""]
    kinds = sorted({_reader_found(v)[0] for v in m.readers.values()})
    L.append(f"- **found from**: {', '.join(kinds) if kinds else '(no reader of its own)'}")
    rd = []
    for k, v in m.readers.items():
        found, only = _reader_found(v)
        state = reader_state(k, an, only)
        tag = " OLD" if k in m.old else ""
        rd.append(f"`{k}` [{found}{(' ' + ','.join(sorted(only))) if only else ''}] {state}{tag}")
    if rd:
        L.append("- **readers** (GATHER): " + "; ".join(rd))
    if m.claims:
        cl = []
        for r in reg:
            if r.family in m.claims:
                pos = []
                if r.tier is not None:
                    pos.append(f"stroke-owner tier {r.tier + 1} of {r.tier_of}")
                if r.layer is not None:
                    pos.append(f"claim order {r.layer + 1} of {r.layer_of} ({r.layer_name})")
                how = "MARKS ONLY (never refuses)" if r.mark_only else "OWNS its ink (a later box on it is refused)"
                if r.family in ("stem", "beam", "flag"):
                    how = "a consumer: reads only ink no earlier claim took"
                live = [w for w, lv, _ in r.filers if lv]
                filed = (f"; filed by {_short(sorted(set(live)), 4)}" if live else "") + \
                        (f"; off by default: {_short(sorted({w for w, lv, _ in r.filers if not lv}), 3)}" if any(not lv for _, lv, _ in r.filers) else "")
                cl.append(f"`{r.family}` ({', '.join(pos) or 'not in the tier list'}) {how}{filed}")
        L.append("- **claims**: " + "; ".join(cl))
    else:
        L.append("- **claims**: nothing")
    sh = shared_facts(an, fs)
    mf = sorted(mark_facts(m, an, fs) - sh)
    msh = sorted(mark_facts(m, an, fs) & sh)
    if mf:
        L.append("- **hands on** (facts): " + ", ".join(f"`{q}` {'' if fs[q].status == LIVE else '(' + fs[q].status + ')'}".rstrip() for q in mf))
    if msh:
        L.append("- **also files the shared facts** (every mark's rows in one fact; readers in `--quantity`): " + ", ".join(f"`{q}`" for q in msh))
    if m.deciders:
        dec = []
        for f in fs.values():
            for v in f.verdict_by:
                if v.split(":")[-1] in m.deciders:
                    dec.append(f"`{v.split(':')[-1]}` -> `{f.q}`")
        L.append("- **decided by** (ADJUDICATE): " + "; ".join(sorted(dec)))
    by_stage: Dict[str, Set[str]] = collections.defaultdict(set)
    for q in mf:
        f = fs[q]
        for s in f.reads_live:
            if s.stage in ("GATHER", "ADJUDICATE") and (any(_covers({k}, s.where) for k in m.readers) or s.where.split(":")[-1] in m.deciders):
                continue
            by_stage[s.stage].add(s.where)
        for r in f.infer_reads:
            by_stage["INFER"].add(f"infer rule {r}")
    ev_rules = sorted({e for q in mf for e in _evaluate_causes(q)})
    if ev_rules:
        by_stage["EVALUATE"] |= {f"rule {r}" for r in ev_rules}
    for st in ("GATHER", "ADJUDICATE", "EVALUATE", "INFER", "EXPORT", "HARNESS", "tools"):
        if by_stage.get(st):
            L.append(f"- **read by {st}** ({len(by_stage[st])}): {_short(sorted(by_stage[st]))}")
    if m.written:
        L.append(f"- **written** (declared): {m.written}")
    gates: Set[str] = set()
    for k in m.readers:
        gates |= set(an.fn_gates(k))
    if gates:
        L.append("- **flags on its readers' paths** (as the code resolves them today): " + ", ".join(f"`{g}`" for g in sorted(gates)))
    if m.old:
        ol = []
        olds = old_facts(m, an, fs)
        for o in m.old:
            live = an.fn_live(*o.split(":", 1)) if ":" in o else True
            ol.append(f"`{o}` {'still runs' if live else 'off by default'}" + (f", files only it: {', '.join(f'`{q}`' for q in sorted(olds[o]))}" if olds[o] else ""))
        L.append("- **old readers beside it** (declared; running derived): " + "; ".join(ol))
    mine = [g for g in gp if m.key in g.marks]
    if mine:
        L.append(f"- **open gaps** ({len(mine)}):")
        for g in mine:
            L.append(f"  - {g.kind.upper()}: {g.text}")
    else:
        L.append("- **open gaps**: none derived")
    L.append("")
    return L


def reader_state(k: str, an: Analysis, only: Optional[Set[str]] = None) -> str:
    """`files rows` where one of its own record calls (or one nested in it) is reached by default; `OFF by default` where none is; for a
    reader that files through a helper, whether the function itself is reached."""
    own = [s for s in an.sites if s.kind != "read" and _covers({k}, s.where) and (only is None or s.quantity in only)]
    if own:
        return "runs" if any(an.site_live(s) for s in own) else "OFF by default"
    return "runs" if an.fn_live(*k.split(":", 1)) else "OFF by default"


def _evaluate_causes(q: str) -> List[str]:
    from . import evaluate
    return [r.consequence.value for r in evaluate.RULES if r.cause == q and not getattr(r, "stub", False)]


def fact_block(f: Fact, an: Analysis, fs: Dict[str, Fact]) -> List[str]:
    L = [f"### `{f.q}` (Q.{f.attr}) -- {f.status}", ""]
    if f.observe_live:
        L.append(f"- `{f.q}` filed by: " + ", ".join(f"{s.stage} `{w}`" for s, w in _uniq((s, s.where) for s in f.observe_live)))
    if f.observe_dead:
        L.append(f"- `{f.q}` filed OFF by default: " + "; ".join(f"`{w}` ({an.site_why(s)})" for s, w in _uniq((s, s.where) for s in f.observe_dead)))
    if f.verdict_by:
        L.append(f"- `{f.q}` decided by: " + ", ".join(f"ADJUDICATE `{v}`" for v in f.verdict_by))
    if f.effect_of:
        L.append(f"- `{f.q}` revised by: " + ", ".join(f"EVALUATE `{v}`" for v in f.effect_of))
    if f.infer_writes:
        L.append(f"- `{f.q}` collapsed by: " + ", ".join(f"INFER `{v}`" for v in f.infer_writes))
    if f.outside:
        L.append(f"- `{f.q}` filed outside the pipeline by `{f.outside}` (a human's review)")
    if f.abstain:
        L.append(f"- `{f.q}` abstained by (not a producer): " + ", ".join(f"`{w}`" for w in sorted({s.where for s in f.abstain})))
    if f.wants:
        L.append(f"- `{f.q}` declared in `wants` (not a read): " + ", ".join(f"`{w}`" for w in sorted(set(f.wants))))
    by: Dict[str, Set[str]] = collections.defaultdict(set)
    for s in f.reads_live:
        by[s.stage].add(s.where)
    for r in f.infer_reads:
        by["INFER"].add(f"infer rule {r}")
    for r in _evaluate_causes(f.q):
        by["EVALUATE"].add(f"rule {r}")
    for st in STAGES:
        if by.get(st):
            L.append(f"- `{f.q}` read by {st}: " + ", ".join(f"`{w}`" for w in sorted(by[st])))
    if f.reads_dead:
        L.append(f"- `{f.q}` read only OFF by default: " + ", ".join(f"`{w}`" for w in sorted({s.where for s in f.reads_dead})))
    mk = _marks_of_fact(f.q, an, fs)
    if mk:
        L.append(f"- `{f.q}` belongs to: " + ", ".join(f"`--mark {k}`" for k in mk))
    L.append("")
    return L


def _uniq(pairs):
    seen = set()
    for s, w in pairs:
        if w not in seen:
            seen.add(w)
            yield s, w


def gap_lines(gp: List[Gap]) -> List[str]:
    L = []
    for kind, title in GAP_KINDS:
        mine = [g for g in gp if g.kind == kind]
        L += [f"### {title} ({len(mine)})", ""]
        if not mine:
            L += ["none", ""]
            continue
        for g in mine:
            L.append(f"- {g.text}" + (f" -- at {_short(g.where, 6)}" if g.where and g.kind not in ("double_fed", "stale_doc") else ""))
        L.append("")
    return L


@dataclass
class Built:
    an: Analysis
    fs: Dict[str, Fact]
    gp: List[Gap]
    reg: List[ClaimRow]
    problems: List[str]


_CACHE: Dict[str, Built] = {}


def build(fresh: bool = False) -> Built:
    """The whole derivation on this tree, once per process (every check that needs it shares it)."""
    if "b" in _CACHE and not fresh:
        return _CACHE["b"]
    an = Analysis()
    fs = facts(an)
    reg = claims_register(an)
    b = Built(an, fs, gaps(an, fs), reg, table_problems(an))
    _CACHE["b"] = b
    return b


def render(b: Optional[Built] = None) -> str:
    b = b or build()
    an, fs, gp, reg = b.an, b.fs, b.gp, b.reg
    if b.problems:
        raise SystemExit("flow_map: the declared table disagrees with the code:\n  " + "\n  ".join(b.problems))
    counts = collections.Counter(f.status for f in fs.values())
    L = [
        "# Data flow: where every mark is read and where it goes",
        "",
        f"GENERATED by `{_CMD}` from the code (ROADMAP 2.331, Sean 2026-11-21). Do not edit by hand: a fast test fails when this page is stale.",
        "STAGED path only. Flags are shown as the code resolves them with no `OMR_*` variable set.",
        "",
        "## How to read this",
        "",
        "- PART 1 has one block per MARK (clef, notehead, beam ...): how it is found, what ink it claims, what it hands on, who reads it at each "
        "stage, what the file writes, which flags gate it, old readers still beside it, and its open gaps.",
        "- PART 2 has one block per FACT (a `Q.` quantity on the record): who files it, who reads it, and its status.",
        "- PART 3 lists every gap the code shows: starved consumers, double feeds, dead reason words, old readers beside new ones.",
        "- `runs` / `OFF by default`: whether the reader's code is reached with every flag at its default.",
        "- Statuses: " + "; ".join(f"**{k}** {v}" for k, v in STATUS_HELP.items()) + ".",
        "- Found from: `ink` the raster itself; `box` a detector box (a box the detector never drew has no subject); `box+ink` a box measured "
        "against its own ink; `text` OCR; `catalog` a fact not read off this page; `record` bookkeeping on rows already filed.",
        "- DECLARED (one table in `flow_map.MARKS`, checked against the code): the mark names, `found from`, which functions read each mark, old "
        "readers, and the `written` line. Everything else is DERIVED.",
        "- Blind spots: a site is OFF only where a flag decides it (a variable set False on the default branch is not seen); detail keys match by "
        "bare name; nothing here runs a page.",
        "",
        "## How to ask",
        "",
        "```",
        f"{_CMD} --mark clef            # one mark's block (the same rows as below)",
        f"{_CMD} --quantity Q.CLEF      # one fact's block (Q. name or its value)",
        f"{_CMD} --consumer export      # every 'read by' row naming a stage, a file or a function",
        f"{_CMD} --gaps                 # PART 3",
        f"{_CMD} --check                # exit 1 if this page is stale",
        "```",
        "",
        "Today: " + ", ".join(f"{counts[k]} {k}" for k in STATUS_HELP if counts.get(k)) + f"; {len(gp)} gaps; "
        f"{len(an.predicates())} flag predicates; {len(set(an.unresolved))} record calls this map cannot resolve.",
        "",
        "## The claim order (who owns which ink, earliest first)",
        "",
        "Stroke-owner tiers (`stroke_owner.TIERS`, then the consumers stem/beam/flag) and the plan's layer (`claim_order.LAYERS`); "
        "`claim_final.mark_only()` called with the defaults; `claimed_by._ORDER` is the register consult.",
        "",
    ]
    for r in reg:
        bits = []
        if r.tier is not None:
            bits.append(f"tier {r.tier + 1}")
        if r.layer is not None:
            bits.append(f"layer {r.layer + 1} {r.layer_name}")
        bits.append("marks only" if r.mark_only else ("consumer" if r.family in ("stem", "beam", "flag") else "owns"))
        if r.consulted:
            bits.append("register consult")
        if r.by_box:
            bits.append("claimed from a detector box's strokes")
        live = sorted({w for w, lv, _ in r.filers if lv})
        dead = sorted({w for w, lv, _ in r.filers if not lv})
        fl = (f"; filed by {_short(live, 4)}" if live else "") + (f"; off by default: {_short(dead, 3)}" if dead else "")
        L.append(f"- `{r.family}`: {', '.join(bits)}{fl}")
    L += ["", "## PART 1 -- by mark", ""]
    L.append("Marks: " + " · ".join(f"[{m.name}](#{_anchor(m)})" for m in MARKS))
    L.append("")
    for m in MARKS:
        L += mark_block(m, an, fs, gp, reg)
    L += ["## PART 2 -- by fact", ""]
    for st in STATUS_HELP:
        qs = [f.q for f in fs.values() if f.status == st]
        if qs:
            L.append(f"- **{st}** ({len(qs)}): " + ", ".join(f"`{q}`" for q in qs))
    L.append("")
    for f in fs.values():
        L += fact_block(f, an, fs)
    L += ["## PART 3 -- the gaps", "",
          "Every line is derived from the code. What the code cannot show (a rule that reads the wrong evidence, a value that is wrong) stays in "
          "`benchmarks/data-flow-audit-2026-11/FINDINGS.md`.", ""]
    L += gap_lines(gp)
    L += ["## Record calls this map cannot resolve", "",
          "A record call whose quantity is computed (the accessors themselves, a loop this map cannot follow). Listed so the count can only go down.",
          "", ", ".join(f"`{u}`" for u in sorted(set(an.unresolved))) or "none", ""]
    return "\n".join(L).rstrip() + "\n"


def _anchor(m: Mark) -> str:
    t = f"{m.name} -- --mark {m.key}".lower()
    return re.sub(r"[^a-z0-9 -]", "", t).replace(" ", "-")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 12. the command
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
def _section(text: str, start: str) -> List[str]:
    """The lines of the page's section whose heading starts with `start`, to the next heading of the same level or higher."""
    level = len(start) - len(start.lstrip("#"))
    out, on = [], False
    for ln in text.splitlines():
        h = len(ln) - len(ln.lstrip("#")) if ln.startswith("#") else 0
        if h and h <= level:
            on = ln.startswith(start)
        if on:
            out.append(ln)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="The generated data-flow map (docs/data-flow.md).")
    ap.add_argument("--check", action="store_true", help="exit 1 if docs/data-flow.md is stale")
    ap.add_argument("--mark")
    ap.add_argument("--quantity")
    ap.add_argument("--consumer")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--stdout", action="store_true", help="print the page instead of writing it")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        ok = PAGE.is_file() and PAGE.read_text() == text
        print("docs/data-flow.md is " + ("current" if ok else f"STALE: run `{_CMD}`"))
        return 0 if ok else 1
    if a.mark:
        if a.mark not in MARK_BY_KEY:
            print("no such mark; marks: " + ", ".join(MARK_BY_KEY))
            return 2
        print("\n".join(_section(text, f"### {MARK_BY_KEY[a.mark].name} -- `--mark {a.mark}`")))
        return 0
    if a.quantity:
        q = a.quantity[2:] if a.quantity.startswith("Q.") else a.quantity
        b = build()
        val = b.an.q_attr.get(q, q if q in b.an.q_vals else None)
        if val is None:
            print(f"no such fact: {a.quantity}")
            return 2
        print("\n".join(_section(text, f"### `{val}` ")))
        return 0
    if a.consumer:
        needle = a.consumer.lower()
        head = None
        for ln in text.splitlines():
            if ln.startswith("## PART 3"):
                break
            if ln.startswith("### `"):
                head = ln
            elif head and " read by " in ln and ln.startswith("- `") and needle in ln.lower():
                print(head)
                print(ln)
        return 0
    if a.gaps:
        print("\n".join(_section(text, "## PART 3")))
        return 0
    if a.stdout:
        sys.stdout.write(text)
        return 0
    PAGE.write_text(text)
    print(f"wrote {PAGE.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
