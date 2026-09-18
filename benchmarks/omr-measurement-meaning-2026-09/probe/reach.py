"""REACH FIRST: is there a population for a UNIT / FRAME / COMPARABILITY check?

Derived from the AST of every non-test module under `tools/omr/`. Nothing is
hand-listed; the accessor set and its argument indices come from
`reach._accessors()`, the derivation this repo already trusts.

Answers, in order:

  [1] which quantities are WRITTEN in more than one coordinate frame?
      -- a quantity whose two rows are not mutually comparable without a check
  [2] which quantities are READ by more than one module?
  [3] where does a consumer POOL rows of one quantity -- read several and put
      their values into arithmetic, a comparison, or min/max/sum/sorted?

  [1 AND 3] is the population a check could act on.

    python3 benchmarks/omr-measurement-meaning-2026-09/probe/reach.py [--json]
"""
from __future__ import annotations

import ast
import collections
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from tools.omr.staged.record import Q               # noqa: E402
from tools.omr.staged import reach as reach_mod     # noqa: E402

#: Q attribute name -> value, e.g. "STAFF_SPACING" -> "staff_spacing"
Q_BY_ATTR = {n: v for n, v in vars(Q).items()
             if isinstance(v, str) and not n.startswith("_")}
Q_VALUES = set(Q_BY_ATTR.values())

#: `frame=` spellings that name one frame. Derived names are resolved by
#: attribute/id so a rename in gather.py shows up as an `<unresolved>` token
#: rather than being silently mapped to the wrong frame.
_FRAME_CONSTS = {"FRAME_PAGE": "page", "FRAME_SYSTEM": "system",
                 "FRAME_HEADER_WINDOW": "header_window",
                 "FRAME_MARGIN": "system_margin"}


def _files():
    out = []
    for p in sorted((_ROOT / "tools" / "omr").rglob("*.py")):
        if p.name.startswith("test_") or "tests" in p.parts:
            continue
        out.append(p)
    return out


def _q_of(node):
    if isinstance(node, ast.Attribute) and node.attr in Q_BY_ATTR:
        return Q_BY_ATTR[node.attr]
    if isinstance(node, ast.Constant) and node.value in Q_VALUES:
        return node.value
    return None


def _local_frames(fn):
    """`{name: frame token}` for `name = <frame expr>` inside one function.

    ⚠️ Needed, not cosmetic: every per-cell gather helper writes
    `frame = frame_cell(...)` once and then passes `frame=frame`, so a
    resolver that stops at the Name reports THIRTEEN quantities as
    `<unresolved>` and the multi-frame population reads far smaller than it
    is. Found by grepping the assignment rather than trusting the token.
    """
    out = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name):
                tok = _frame_of(n.value, {})
                if not tok.startswith("<unresolved"):
                    out[t.id] = tok
    return out


def _frame_of(v, locals_=None):
    """Canonicalise a `frame=` argument to a comparable token.

    A per-cell frame is canonicalised to `cell:*` because `cell:0` and
    `cell:7` are the SAME KIND of frame; what matters for comparability is
    that a cell frame and a page frame are different kinds. ⚠️ Two different
    cells' canonical frames coincide BY CONSTRUCTION, which is the
    `Q.ONSET_COLUMN` fault -- that is a stronger statement than this token
    makes and is reported separately.
    """
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        s = v.value
        return "cell:*" if s.startswith("cell:") else s
    if isinstance(v, ast.Name):
        if v.id in _FRAME_CONSTS:
            return _FRAME_CONSTS[v.id]
        if locals_ and v.id in locals_:
            return locals_[v.id]
        return "<unresolved:%s>" % v.id
    if isinstance(v, ast.Attribute):
        return _FRAME_CONSTS.get(v.attr, "<unresolved:%s>" % v.attr)
    if isinstance(v, ast.Call):
        f = v.func
        nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "?")
        if nm == "frame_cell":
            return "cell:*"
        if nm == "frame_bar_head":
            return "bar_head:*"
        return "<unresolved:call:%s>" % nm
    if isinstance(v, ast.BinOp):                    # "cell:%d" % c
        if (isinstance(v.left, ast.Constant)
                and str(v.left.value).startswith("cell:")):
            return "cell:*"
        return "<unresolved:binop>"
    if isinstance(v, ast.JoinedStr):                # f"cell:{c}"
        head = next((x.value for x in v.values
                     if isinstance(x, ast.Constant)), "")
        return "cell:*" if str(head).startswith("cell:") else "<unresolved:f>"
    if isinstance(v, ast.IfExp):
        return "<unresolved:ifexp>"
    return "<unresolved:%s>" % type(v).__name__


def _dict_kwargs(scope):
    """`{var name: set of keyword names}` ever put into a dict in this scope.

    Collects BOTH `d = dict(k=v, ...)` and `d.update(k=v, ...)`.

    ⚠️⚠️ THE `.update()` HALF IS NOT OPTIONAL AND THIS PROBE'S FIRST RUN
    PROVES IT. `capture.py` documents `**common` bound to `dict(...)` as the
    trap that made `gather_coverage` report five families as having no
    reader. The dominant spelling in `gather.py` is the OTHER one --
    `box_detail.update(bbox_page_px=..., upscale=...)` then `**box_detail` --
    and resolving only `dict(...)` found 12 unit-declaring keys and **ZERO**
    frame disagreements, i.e. it reported the question as clean by failing to
    ask it. The same anti-pattern, one spelling further on.
    """
    out = collections.defaultdict(set)
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if (isinstance(t, ast.Name) and isinstance(n.value, ast.Call)
                    and getattr(n.value.func, "id", None) == "dict"):
                out[t.id] |= {k.arg for k in n.value.keywords if k.arg}
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr == "update" and isinstance(n.func.value, ast.Name):
                out[n.func.value.id] |= {k.arg for k in n.keywords if k.arg}
    return out


def _unpacked_frames(fn, locals_):
    """`{dict name: frame token}` for `name = dict(..., frame=...)`.

    ⚠️ `capture.py`'s documented trap, which the SHIPPED `gather_coverage`
    fell into: `gather_glyph_families` builds `common = dict(reader=...,
    frame=frame, ...)` and calls `observe(..., **common)`. A visitor reading
    only literal keywords sees no frame at all and reports the row as
    carrying none.
    """
    out = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if not isinstance(t, ast.Name) or not isinstance(n.value, ast.Call):
                continue
            f = n.value.func
            if getattr(f, "id", None) != "dict":
                continue
            for kw in n.value.keywords:
                if kw.arg == "frame":
                    out[t.id] = _frame_of(kw.value, locals_)
    return out


def _frame_arg(call, locals_, unpacked):
    """The frame token a write call carries, looking through `**name`."""
    for kw in call.keywords:
        if kw.arg == "frame":
            return _frame_of(kw.value, locals_)
    for kw in call.keywords:
        if kw.arg is None and isinstance(kw.value, ast.Name):   # **common
            if kw.value.id in unpacked:
                return unpacked[kw.value.id]
            return "<unresolved:**%s>" % kw.value.id
    return "<unspecified>"


def collect():
    read_at, write_at = reach_mod._accessors()
    writes = collections.defaultdict(set)
    write_sites = collections.defaultdict(list)
    reads = collections.defaultdict(set)
    files = 0

    for p in _files():
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:
            continue
        files += 1
        rel = str(p.relative_to(_ROOT))
        # ⚠️ Each call is resolved in its NEAREST enclosing scope, innermost
        # winning. A single module-level `ast.walk` also reaches every nested
        # call, but with no locals in hand -- so it would resolve
        # `frame=frame` as unresolved and the per-cell writes would vanish.
        parent = {}
        for n in ast.walk(tree):
            for ch in ast.iter_child_nodes(n):
                parent[id(ch)] = n
        cache = {}

        def _scope_maps(node):
            chain, cur = [], node
            while id(cur) in parent:
                cur = parent[id(cur)]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.Module)):
                    chain.append(cur)
            loc, unp = {}, {}
            for scope in reversed(chain):          # outermost first
                if id(scope) not in cache:
                    l = _local_frames(scope)
                    cache[id(scope)] = (l, _unpacked_frames(scope, l))
                l, u = cache[id(scope)]
                loc.update(l)
                unp.update(u)
            return loc, unp

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute)
                    else getattr(f, "id", None))
            if name in write_at:
                idx = write_at[name]
                q = _q_of(node.args[idx]) if len(node.args) > idx else None
                if q is None:
                    continue
                loc, unp = _scope_maps(node)
                fr = _frame_arg(node, loc, unp)
                writes[q].add(fr)
                write_sites[q].append((rel, node.lineno, fr))
            elif name in read_at:
                idx = read_at[name]
                q = _q_of(node.args[idx]) if len(node.args) > idx else None
                if q is None:
                    q = next((_q_of(kw.value) for kw in node.keywords
                              if kw.arg == "quantity"), None)
                if q is not None:
                    reads[q].add(rel)
    return writes, write_sites, reads, files


#: Suffix -> the UNIT/FRAME the key name itself declares. Ordered longest
#: first so `_page_px` is not read as `_px`.
#:
#: ⚠️ This is a NAMING convention, not a type. It is trusted here only to
#: report a DISAGREEMENT between a row's `frame` field and its own detail
#: keys -- never to assert what a key holds.
UNIT_SUFFIX = [
    ("_page_px", "page/px"), ("_canonical", "canonical/px"),
    ("_page", "page/px"), ("_spaces", "staff-space"),
    ("_steps", "staff-step"), ("_px", "?/px"),
    ("_ql", "quarter-length"), ("_beats", "beat"),
    ("_fraction", "dimensionless"), ("_ratio", "dimensionless"),
    ("_frac", "dimensionless"),
]

#: Which row frames a key's declared frame is compatible with.
FRAME_OF_UNIT = {"page/px": {"page", "system", "header_window",
                             "system_margin"},
                 "canonical/px": {"cell:*", "bar_head:*"}}


def _unit_of_key(key):
    for suf, unit in UNIT_SUFFIX:
        if key.endswith(suf):
            return unit
    return None


def detail_units():
    """(quantity, detail key) -> declared unit, with the row frames seen.

    Reports a row whose `frame` field and whose own detail keys name
    DIFFERENT coordinate frames -- `Q.GLYPH_BOX` is filed at `cell:*` and
    carries `bbox_page_px`, so the row's `frame` describes its `value` and
    not its contents.
    """
    read_at, write_at = reach_mod._accessors()
    rows = collections.defaultdict(lambda: collections.defaultdict(set))
    for p in _files():
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:
            continue
        rel = str(p.relative_to(_ROOT))
        parent = {}
        for n in ast.walk(tree):
            for ch in ast.iter_child_nodes(n):
                parent[id(ch)] = n
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute)
                    else getattr(f, "id", None))
            if name not in write_at:
                continue
            idx = write_at[name]
            q = _q_of(node.args[idx]) if len(node.args) > idx else None
            if q is None:
                continue
            # locals for the frame, same walk as collect()
            chain, cur = [], node
            while id(cur) in parent:
                cur = parent[id(cur)]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.Module)):
                    chain.append(cur)
            loc, unp, dkw = {}, {}, collections.defaultdict(set)
            for scope in reversed(chain):
                l = _local_frames(scope)
                loc.update(l)
                unp.update(_unpacked_frames(scope, l))
                for k2, v2 in _dict_kwargs(scope).items():
                    dkw[k2] |= v2
            fr = _frame_arg(node, loc, unp)
            keys = [kw.arg for kw in node.keywords if kw.arg]
            for kw in node.keywords:
                if kw.arg is None and isinstance(kw.value, ast.Name):
                    keys += sorted(dkw.get(kw.value.id, ()))
            for k in keys:
                u = _unit_of_key(k)
                if u:
                    rows[q][(k, u)].add((fr, rel, node.lineno))
    return rows


#: Frame token -> the `Kind` whose extent that frame is measured within.
#: DECLARED, because there is no mechanical link from the string "cell:0" to
#: `Kind.CELL`. It is GUARDED: any frame token the probe sees that is not in
#: here is reported, so a new frame cannot be silently skipped.
FRAME_EXTENT = {
    "cell:*": "CELL", "bar_head:*": "CELL",
    "header_window": "STAFF",
    "system": "SYSTEM", "system_margin": "SYSTEM",
    "page": "PAGE",
    "dossier": "DOCUMENT",
}

#: Detail keys that lift a row into the PAGE frame. A decision pooling
#: per-cell rows across cells is safe iff it reads one of these instead of
#: the row's own value.
PAGE_FRAME_KEYS = {"bbox_page_px", "x_center_page", "y_center_page",
                   "staff_bottom_line_page", "x_page"}


def scope_vs_frame():
    """Decisions whose SCOPE is coarser than the FRAME their rows live in.

    ⚠️⚠️ THIS IS THE `Q.ONSET_COLUMN` FAULT STATED DERIVABLY, and it is the
    one arm that would have caught that bug BEFORE the repair. A measure
    cell is rescaled so the staff span is constant, so **two cells'
    canonical frames coincide BY CONSTRUCTION** -- two staves agreeing at
    canonical x is not evidence of anything. A decision at `Kind.SYSTEM`
    reading rows written in a `cell:*` frame is pooling across frames, and
    neither `wiring` (which asks about SCOPE reach) nor arm 4 (which asks
    about a row's own detail) can see it.

    Reported, never gated: a decision may be pooling legitimately because it
    reads a PAGE-frame detail key instead of the row's value. That is why
    `reads_page_key` travels with every row of this table.
    """
    # ⚠️⚠️ THE IMPORT IS LOAD-BEARING AND THIS ARM'S FIRST RUN PROVES IT.
    # `adjudicate.REGISTRY` is populated by the `@decision` decorator, which
    # runs only when the `adjudicators` package is imported. Imported bare,
    # `len(REGISTRY) == 0` -- so the first run of this arm iterated NOTHING
    # and printed a confident `0`, which reads exactly like "no decision
    # pools across frames". The assertion below is the positive control that
    # a zero here means the question was asked.
    from tools.omr.staged import adjudicate as A
    from tools.omr.staged import adjudicators as _ad   # noqa: F401  registers
    from tools.omr.staged.record import _KIND_DEPTH

    assert len(A.REGISTRY) > 20, (
        f"REGISTRY holds {len(A.REGISTRY)} decisions; the adjudicators "
        f"package did not register. A zero from this arm would be vacuous.")

    depth = {k.name: v for k, v in _KIND_DEPTH.items()}
    writes, _, _, _ = collect()
    out, unknown = [], set()
    for name, spec in sorted(A.REGISTRY.items()):
        sdepth = depth[spec.scope.name]
        fn = spec.fn if hasattr(spec, "fn") else None
        try:
            import inspect as _i
            src = _i.getsource(fn) if fn else ""
        except (OSError, TypeError):
            src = ""
        for q in sorted(spec.wants):
            for fr in sorted(writes.get(q, ())):
                ext = FRAME_EXTENT.get(fr)
                if ext is None:
                    unknown.add(fr)
                    continue
                if depth[ext] > sdepth:          # frame FINER than the scope
                    keys = sorted(k for k in PAGE_FRAME_KEYS if k in src)
                    out.append((name, spec.scope.name, q, fr, ext, keys))
    return out, sorted(unknown)


#: Names whose appearance in a function means the function is COMBINING
#: numbers rather than merely reading them.
POOL_CALLS = {"sum", "max", "min", "sorted", "mean", "fmean", "median",
              "abs", "round"}


def pooling():
    """Functions that read rows of a quantity AND combine numbers.

    Deliberately SYNTACTIC and over-inclusive: the point of this arm is to
    bound the population, not to accuse a site. A function that reads rows of
    `q` and contains any arithmetic, comparison, or pooling call is counted.
    """
    read_at, _ = reach_mod._accessors()
    multi = {a for a in read_at if a in ("rows", "verdicts", "obs", "obs_of",
                                         "refusals", "verdicts_of", "admitted")}
    out = []
    for p in _files():
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:
            continue
        rel = str(p.relative_to(_ROOT))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qs, arith = set(), False
            for n in ast.walk(fn):
                if isinstance(n, ast.Call):
                    f = n.func
                    nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                    if nm in multi:
                        idx = read_at.get(nm, 0)
                        q = _q_of(n.args[idx]) if len(n.args) > idx else None
                        if q:
                            qs.add(q)
                    if nm in POOL_CALLS:
                        arith = True
                elif isinstance(n, (ast.BinOp, ast.Compare)):
                    arith = True
            if qs and arith:
                out.append((rel, fn.lineno, fn.name, sorted(qs)))
    return out


def main() -> int:
    writes, write_sites, reads, files = collect()
    pools = pooling()

    multi_frame = {q: sorted(v) for q, v in writes.items() if len(v) > 1}
    multi_reader = {q: sorted(v) for q, v in reads.items() if len(v) > 1}
    pooled_qs = {q for _, _, _, qs in pools for q in qs}
    both = sorted(set(multi_frame) & pooled_qs)

    print("=" * 76)
    print("REACH — is there a population for a UNIT/FRAME/COMPARABILITY check?")
    print("=" * 76)
    print(f"  files walked                        {files}")
    print(f"  Q vocabulary                        {len(Q_BY_ATTR)}")
    print(f"  quantities WRITTEN                  {len(writes)}")
    print(f"  quantities READ                     {len(reads)}")
    print(f"  quantities POOLED (read + combined) {len(pooled_qs)}")
    print()
    print(f"[1] written in >1 FRAME               {len(multi_frame)}")
    for q, fr in sorted(multi_frame.items()):
        print(f"      {q:32s} {fr}")
    print()
    print(f"[2] read by >1 MODULE                 {len(multi_reader)}")
    for q, mods in sorted(multi_reader.items()):
        print(f"      {q:32s} {[m.rsplit('/', 1)[-1] for m in mods]}")
    print()
    print(f"[3] functions reading rows + combining numbers   {len(pools)}")
    for rel, ln, fname, qs in pools:
        print(f"      {rel.rsplit('/', 1)[-1]:20s}:{ln:<5d} {fname:32s} {qs}")
    print()
    print(f"[1 AND 3] multi-frame AND pooled      {len(both)}")
    for q in both:
        print(f"      {q:32s} {multi_frame[q]}")

    du = detail_units()
    mixed, unit_keys = [], 0
    for q, keys in sorted(du.items()):
        for (k, u), sites in sorted(keys.items()):
            unit_keys += 1
            ok = FRAME_OF_UNIT.get(u)
            if not ok:
                continue                  # scale-free or time: no frame claim
            bad = sorted({fr for fr, _, _ in sites} - ok)
            if bad:
                mixed.append((q, k, u, bad, sorted(sites)[0]))
    print()
    print(f"[4] detail keys DECLARING a unit      {unit_keys}")
    print(f"    rows whose frame field and own detail keys DISAGREE  {len(mixed)}")
    for q, k, u, bad, site in mixed:
        print(f"      {q:26s} {k:22s} says {u:13s} row frame {bad}")
        print(f"          {site[1].rsplit('/', 1)[-1]}:{site[2]}")

    svf, unknown_frames = scope_vs_frame()
    print()
    print(f"[5] decision SCOPE coarser than row FRAME   {len(svf)}")
    print("    (rows whose coordinate systems coincide BY CONSTRUCTION)")
    blind = [r for r in svf if not r[5]]
    for name, scope, q, fr, ext, keys in svf:
        mark = "reads " + ",".join(keys) if keys else "** no page-frame key **"
        print(f"      {name:30s} scope={scope:8s} {q:24s} frame={fr:10s} {mark}")
    print(f"    of which the decision reads NO page-frame detail key: {len(blind)}")
    if unknown_frames:
        print(f"    ⚠️ frame tokens not in FRAME_EXTENT: {unknown_frames}")

    hist = collections.Counter(f for v in writes.values() for f in v)
    print()
    print("frame tokens (number of quantities carrying each):")
    for f, n in hist.most_common():
        print(f"      {f:26s} {n}")

    # positive controls: a zero in any of these means the walk did not run
    assert files > 10, "files walked is a control; a low number means no walk"
    assert len(writes) > 30, "writers is a control"
    assert len(reads) > 30, "readers is a control"

    if "--json" in sys.argv:
        out = _ROOT / "benchmarks" / "omr-measurement-meaning-2026-09" / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "reach.json").write_text(json.dumps({
            "files_walked": files,
            "n_quantities": len(Q_BY_ATTR),
            "n_written": len(writes),
            "n_read": len(reads),
            "multi_frame": multi_frame,
            "multi_reader": multi_reader,
            "pooled_quantities": sorted(pooled_qs),
            "pools": [[r, l, f, qs] for r, l, f, qs in pools],
            "multi_frame_and_pooled": both,
            "frame_histogram": dict(hist),
            "write_sites": {q: v for q, v in write_sites.items()},
        }, indent=2, default=str))
        print(f"\nwrote {out / 'reach.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
