"""Reading and writing a staged record FILE: the id-list pools.

Roadmap 1.1b, 2026-09-22. ⚠️ THIS MODULE CHANGES HOW A RECORD IS SPELLED ON
DISK AND NOTHING ELSE. `Log`, `Verdict`, `Evidence` and every stage are
untouched; an in-memory record dict is never pooled; `load_record` gives a
reader exactly the dict `Log.to_json` produced.

Why it exists, measured on the two committed shared records (compact JSON,
`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §12):

  * an `arc_owner` verdict is **99.2 % three id lists** -- `basis` (37 %),
    `considered` (31 %), `correlated` (31 %) -- and 0.4 % everything else;
  * the set `considered - used` is IDENTICAL for every arc in a system
    (exactly one distinct set per system on both documents), because
    `adjudicate_arc_owner` reads the whole system's `Q.GLYPH_BOX` rows once
    per arc to find the rival staff that explains the arc better;
  * so on Breitkopf 2,207 verdicts each carry the same ~1,800 ids three
    times: 183 MB of a 245 MB record.

The three fields are HARNESS-computed (`adjudicate_one`), and `basis` is
load-bearing -- `Log.closure` walks it, and `Evidence._admit`'s circularity
filter reads that closure -- so their CONTENT cannot shrink. Their SPELLING
can: a list that repeats another list up to a few private ids is written as
a reference to one pooled copy plus the private ids at their positions.

    "considered": {"$pool": "pool:00003", "ins": [[0, "obs:005283"]]}
    "correlated": [{"$pool": "pool:00004"}, ["obs:1", "obs:2"]]
    ...
    "pools": {"pool:00003": ["obs:000104", "obs:000106", ...], ...}

`ins` holds `[final_index, id]` pairs in ascending index order; expansion
copies the pool and inserts each id at its index. The encoding is LOSSLESS
INCLUDING ORDER (`considered` is insertion-ordered, `basis` sorted) and the
writer PROVES it on every call: `pool_id_lists` expands its own output and
raises `PoolMismatch` unless every field deep-equals the input. That is the
control this repo requires of a serialiser -- one that can fail.

⚠️⚠️ A NAIVE READER SEES A DICT WHERE A LIST WAS. `for rid in v["considered"]`
on a pooled verdict iterates the strings `"$pool"` and `"ins"`; a
`quantity_of.get(rid)` lookup returns None for both and a `discard(None)`
hides it. That is the failure the roadmap row warned about, and the answer
is that a record FILE is read through `load_record` (or `expand_result` on
a dict already loaded) and nowhere else -- every in-tree reader of
`record.verdicts` goes through it, and `test_record_pools.py` holds the
naive reading up against the loaded one so the difference is on the record
rather than assumed away. Streaming readers of `record.observations`
(`positional_store.stream_observations`, `record_slim`) are unaffected:
observations are never pooled, and `record_slim` copies `pools` and the
refs through verbatim, which the same test checks.

The grouping is deliberately generic -- verdicts of one quantity by one
decider under one system (or page, or the document) -- and names no
adjudicator: `wedge_anchor` has the same shape at a smaller scale and any
future system-scoped read will too. A list below `MIN_POOL_IDS` ids, or a
group of one, is written inline exactly as before, so a small fixture's
record is byte-for-byte what it always was.
"""
from __future__ import annotations

import contextlib
import gc
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .record import Kind, LazyBasis, Subject

#: Where the pooled lists live inside `record`.
POOL_KEY = "pools"
#: The key that marks a reference. A `$` cannot begin a row id, a quantity
#: or a subject key, so a reference is never mistaken for one of those.
REF_KEY = "$pool"
INS_KEY = "ins"
#: Flat id lists that repeat across a group up to a few private ids.
FLAT_FIELDS: Tuple[str, ...] = ("considered", "basis")
#: A list of id lists, whose inner lists repeat verbatim.
GROUPED_FIELD = "correlated"
#: Below this many ids a list is written inline. Chosen so that a hand-built
#: test fixture (a dozen rows) is never pooled and a system-scoped read
#: (hundreds to thousands) always is.
MIN_POOL_IDS = 64


class PoolMismatch(RuntimeError):
    """The pooled spelling did not expand back to the input, or a reference
    names a pool the file does not hold. Never caught internally."""


# ─────────────────────────────────────────────────────────────────────────────
# One list against one pool
# ─────────────────────────────────────────────────────────────────────────────


def _encode(lst: Sequence[str], core: Sequence[str]) -> Optional[List[list]]:
    """`ins` such that `_decode(core, ins) == lst`, or None if `core` is not
    an in-order subsequence of `lst`."""
    ins: List[list] = []
    j = 0
    n = len(core)
    for i, x in enumerate(lst):
        if j < n and x == core[j]:
            j += 1
        else:
            ins.append([i, x])
    if j != n:
        return None
    return ins


def _decode(core: Sequence[str], ins: Sequence[Sequence[Any]]) -> List[str]:
    out = list(core)
    for pos, x in ins:
        out.insert(int(pos), x)
    return out


def _resolve(ref: Any, pools: Dict[str, list]) -> List[str]:
    if not isinstance(ref, dict) or REF_KEY not in ref:
        raise PoolMismatch(f"not a pool reference: {ref!r}")
    core = pools.get(ref[REF_KEY])
    if core is None:
        raise PoolMismatch(
            f"reference to {ref[REF_KEY]!r}, which this record's "
            f"{POOL_KEY!r} does not hold -- a pooled record written without "
            f"its pools, or a pool renamed after the fact")
    return _decode(core, ref.get(INS_KEY) or ())


# ─────────────────────────────────────────────────────────────────────────────
# Pooling (write side)
# ─────────────────────────────────────────────────────────────────────────────


def _group_key(v: dict) -> tuple:
    """Verdicts that plausibly read the same population: one quantity, one
    decider, one system -- or one page, or the document, for a coarser
    subject."""
    sub = Subject.from_key(v["subject"])
    anchor = sub.at(Kind.SYSTEM) or sub.at(Kind.PAGE) or sub.at(Kind.DOCUMENT)
    return (v.get("quantity"), v.get("decider"),
            anchor.to_key() if anchor is not None else "")


def _expand_verdicts(verdicts: List[dict], pools: Dict[str, list]) -> None:
    for v in verdicts:
        for fld in FLAT_FIELDS:
            val = v.get(fld)
            if isinstance(val, dict):
                v[fld] = _resolve(val, pools)
        groups = v.get(GROUPED_FIELD)
        if groups:
            v[GROUPED_FIELD] = [
                _resolve(g, pools) if isinstance(g, dict) else g
                for g in groups]


def json_default(o: Any) -> Any:
    """`default=` for encoding a record: a `LazyBasis` / `RecordBasis` is the list it stands for (ROADMAP 2.249);
    anything else `str`, as the record has always been written."""
    if isinstance(o, (LazyBasis, RecordBasis)):
        return list(o)
    return str(o)


# ─────────────────────────────────────────────────────────────────────────────
# Format 2 (ROADMAP 2.249 m8): an ADJUDICATE verdict's basis is derived, not stored
# ─────────────────────────────────────────────────────────────────────────────

DERIVED_KEY = "basis_from"


def _file_form(v: dict) -> dict:
    """The verdict as the FILE holds it: a derived basis (`basis_from: "considered"`) is left out."""
    if v.get(DERIVED_KEY) == "considered" and "basis" in v:
        v = dict(v)
        del v["basis"]
    return v


class _RowGraph:
    """What each row of a LOADED record rests on directly -- a derived verdict's `considered`, any other row's
    `basis` -- and the closures walked over it (memoised, bounded, least recently used out first)."""

    MAX_IDS = 30_000_000

    def __init__(self, record: dict) -> None:
        self.edges: Dict[str, Sequence[str]] = {}
        for kind in ("observations", "abstentions", "verdicts"):
            for r in record.get(kind) or ():
                rid = r.get("id")
                if rid is None:
                    continue
                if r.get(DERIVED_KEY) == "considered":
                    self.edges[rid] = r.get("considered") or ()
                else:
                    b = r.get("basis")
                    self.edges[rid] = () if isinstance(b, RecordBasis) else (b or ())
        self.derived = {r.get("id") for r in record.get("verdicts") or () if r.get(DERIVED_KEY) == "considered"}
        from collections import OrderedDict
        self.memo: "OrderedDict[str, frozenset]" = OrderedDict()
        self.held = 0

    def closure(self, rid: str) -> frozenset:
        """`rid` and every row it rests on, transitively (memoised)."""
        hit = self.memo.get(rid)
        if hit is not None:
            self.memo.move_to_end(rid)
            return hit
        res = frozenset(self._walk([rid]))
        self.memo[rid] = res
        self.held += len(res)
        while self.held > self.MAX_IDS and len(self.memo) > 1:
            _k, old = self.memo.popitem(last=False)
            self.held -= len(old)
        return res

    def closure_of_many(self, ids: Sequence[str]) -> set:
        """The union of `closure(r)` for every `r` in `ids`: a verdict's closure is memoised (others rest on it too),
        a reading's is walked inline."""
        out: set = set()
        stack = []
        for rid in ids:
            if rid in out:
                continue
            if rid in self.derived:
                out |= self.closure(rid)
            else:
                stack.append(rid)
        out |= self._walk(stack, out)
        return out

    def _walk(self, stack, seen=None) -> set:
        out: set = set() if seen is None else seen
        memo = self.memo
        while stack:
            rid = stack.pop()
            if rid in out:
                continue
            hit = memo.get(rid)
            if hit is not None:
                memo.move_to_end(rid)
                out |= hit
                continue
            out.add(rid)
            stack.extend(self.edges.get(rid, ()))
        return out


class RecordBasis(Sequence):
    """A loaded format-2 verdict's `basis`: `considered` plus each considered row's closure, spelled out (sorted, as
    format 1 stored it) when read. Behaves as that sorted list: iteration, `len`, indexing, `in`, `==`, `bool`."""

    __slots__ = ("_graph", "considered", "_t")

    def __init__(self, graph: _RowGraph, considered: Sequence[str]) -> None:
        self._graph = graph
        self.considered = tuple(considered)
        self._t: Optional[tuple] = None

    def _spell(self) -> tuple:
        t = self._t
        if t is None:
            t = tuple(sorted(self._graph.closure_of_many(self.considered)))
        return t

    def __iter__(self):
        return iter(self._spell())

    def __len__(self) -> int:
        return len(self._spell())

    def __bool__(self) -> bool:
        return bool(self.considered)

    def __getitem__(self, i):
        return self._spell()[i]

    def __contains__(self, x) -> bool:
        return x in self._graph.closure_of_many(self.considered)

    def __eq__(self, other) -> bool:
        if isinstance(other, (RecordBasis, LazyBasis)):
            return tuple(self) == tuple(other)
        if isinstance(other, (list, tuple)):
            return self._spell() == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._spell())

    def __repr__(self) -> str:
        return "RecordBasis(considered=%d ids)" % len(self.considered)


def attach_derived_bases(record: dict) -> dict:
    """ROADMAP 2.249 m8: give every format-2 derived verdict of a LOADED record its `basis` back (a `RecordBasis`,
    spelled when read). A format-1 record (no `format` key) stores every basis and is returned untouched. In place."""
    verdicts = record.get("verdicts") or ()
    if not any(isinstance(v, dict) and v.get(DERIVED_KEY) == "considered" for v in verdicts):
        return record
    graph = _RowGraph(record)
    for v in verdicts:
        if isinstance(v, dict) and v.get(DERIVED_KEY) == "considered" and not isinstance(v.get("basis"), (list, tuple, LazyBasis)):
            v["basis"] = RecordBasis(graph, v.get("considered") or ())
    return record


def _is_ids(lst: Any) -> bool:
    return isinstance(lst, (list, LazyBasis))


def _pool_plan(verdicts: List[dict]):
    """ROADMAP 2.249: which (verdict, field) lists `pool_id_lists` pools, against which pool -- decided exactly as it
    always was (same groups, same cores, same pool numbering), but the encodings are not kept: `_pooled_one` makes
    each again as its verdict is written, so no second copy of every list is held."""
    pools: Dict[str, list] = {}
    by_content: Dict[tuple, str] = {}

    def intern(core: Sequence[str]) -> str:
        key = tuple(core)
        pid = by_content.get(key)
        if pid is None:
            pid = f"pool:{len(pools) + 1:05d}"
            pools[pid] = list(core)
            by_content[key] = pid
        return pid

    flat: Dict[Tuple[int, str], str] = {}
    for fld in FLAT_FIELDS:
        groups: Dict[tuple, List[int]] = defaultdict(list)
        for idx, v in enumerate(verdicts):
            lst = v.get(fld)
            if _is_ids(lst) and len(lst) >= MIN_POOL_IDS:
                groups[_group_key(v)].append(idx)
        for members in groups.values():
            if len(members) < 2:
                continue
            first = list(verdicts[members[0]][fld])
            common = set(first)
            for idx in members[1:]:
                common &= set(verdicts[idx][fld])
                if len(common) < MIN_POOL_IDS:
                    break
            if len(common) < MIN_POOL_IDS:
                continue
            core = [x for x in first if x in common]
            pid: Optional[str] = None
            for idx in members:
                lst = list(verdicts[idx][fld])
                ins = _encode(lst, core)
                # Not an in-order subsequence, or more private than shared:
                # inline, exactly as before.
                if ins is None or 2 * len(ins) > len(lst):
                    continue
                if pid is None:
                    pid = intern(core)
                flat[(idx, fld)] = pid

    # ── correlated: inner lists interned by content where repeated ─────────
    seen: Counter = Counter()
    for v in verdicts:
        for g in v.get(GROUPED_FIELD) or ():
            if isinstance(g, list) and len(g) >= MIN_POOL_IDS:
                seen[tuple(g)] += 1
    grouped: Dict[int, List[Any]] = {}
    for idx, v in enumerate(verdicts):
        groups_ = v.get(GROUPED_FIELD)
        if not groups_:
            continue
        enc: List[Any] = []
        changed = False
        for g in groups_:
            if (isinstance(g, list) and len(g) >= MIN_POOL_IDS
                    and seen[tuple(g)] >= 2):
                enc.append({REF_KEY: intern(g)})
                changed = True
            else:
                enc.append(g)
        if changed:
            grouped[idx] = enc
    return pools, flat, grouped


def _pooled_one(v: dict, idx: int, pools: Dict[str, list], flat, grouped) -> dict:
    """Verdict `idx` as the pooled record spells it, checked: its pooled fields expand back to its own (raises
    `PoolMismatch` otherwise -- the control `pool_id_lists` always ran, now one verdict at a time)."""
    out = dict(v)
    for fld in FLAT_FIELDS:
        pid = flat.get((idx, fld))
        if pid is not None:
            lst = list(v[fld])
            out[fld] = {REF_KEY: pid, INS_KEY: _encode(lst, pools[pid])}
    if idx in grouped:
        out[GROUPED_FIELD] = grouped[idx]
    if out is not v:
        back = dict(out)
        _expand_verdicts([back], pools)
        for fld in FLAT_FIELDS + (GROUPED_FIELD,):
            if v.get(fld) != back.get(fld):
                raise PoolMismatch(
                    f"{v.get('id')}.{fld}: pooled spelling does not "
                    f"expand back to the input (refusing to write)")
    return out


def pool_id_lists(record: dict) -> dict:
    """The record with its repeated verdict id lists pooled.

    Returns a NEW dict (the input's verdict dicts are copied, never
    mutated); returns the input itself when nothing qualifies, so a small
    record is unchanged in identity as well as content. Self-checks by
    expanding its own output and comparing every pooled field to the input;
    raises `PoolMismatch` on any difference.
    """
    verdicts: List[dict] = [_file_form(v) for v in record.get("verdicts") or ()]
    if not verdicts:
        return record
    pools, flat, grouped = _pool_plan(verdicts)
    if not pools:
        if any(v.get(DERIVED_KEY) == "considered" for v in verdicts):     # format 2: the file form still drops bases
            out = dict(record)
            out["verdicts"] = verdicts
            return out
        return record
    out = dict(record)
    out["verdicts"] = [_pooled_one(v, i, pools, flat, grouped) for i, v in enumerate(verdicts)]
    out[POOL_KEY] = pools
    return out


class _PooledVerdicts(list):
    """ROADMAP 2.249: the pooled verdicts, made one at a time as `_stream` writes them (never all held at once)."""

    def __init__(self, verdicts, plan):
        super().__init__()
        self._verdicts, self._plan = verdicts, plan

    def __len__(self):
        return len(self._verdicts)

    def __iter__(self):
        pools, flat, grouped = self._plan
        for i, v in enumerate(self._verdicts):
            yield _pooled_one(v, i, pools, flat, grouped)


def _streamed_pooled_result(result: dict) -> dict:
    """`pooled_result(result)`, byte for byte once written, with the verdicts pooled as they are written."""
    rec = result.get("record")
    if not isinstance(rec, dict):
        return result
    verdicts: List[dict] = [_file_form(v) for v in rec.get("verdicts") or ()]
    if not verdicts:
        return result
    plan = _pool_plan(verdicts)
    if not plan[0]:
        out_rec = dict(rec)
        out_rec["verdicts"] = verdicts
        out = dict(result)
        out["record"] = out_rec
        return out
    out_rec = dict(rec)
    out_rec["verdicts"] = _PooledVerdicts(verdicts, plan)
    out_rec[POOL_KEY] = plan[0]
    out = dict(result)
    out["record"] = out_rec
    return out


def pooled_result(result: dict) -> dict:
    """`result` as the CLI writes it: `result["record"]` pooled, every
    sibling key (`provenance`, `summary`, ...) shared with the input."""
    rec = result.get("record")
    if not isinstance(rec, dict):
        return result
    out = dict(result)
    out["record"] = pool_id_lists(rec)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Expansion (read side)
# ─────────────────────────────────────────────────────────────────────────────


def expand_id_lists(record: dict) -> dict:
    """The record with every pooled list spelled out again, IN PLACE.

    Idempotent, and a no-op on a record that was never pooled -- so a reader
    can call it on any record dict without first asking which kind it has.
    """
    pools = record.get(POOL_KEY)
    if pools:
        _expand_verdicts(list(record.get("verdicts") or ()), pools)
    record.pop(POOL_KEY, None)
    return attach_derived_bases(record)


def expand_result(data: dict) -> dict:
    """`expand_id_lists` on `data["record"]` when the CLI envelope is
    present, else on `data` itself (a bare record, as `brakes.measure`
    accepts). In place; returns `data`."""
    rec = data.get("record")
    expand_id_lists(rec if isinstance(rec, dict) else data)
    return data


def load_record(path: Union[str, Path]) -> dict:
    """⚠️ THE ONE WAY TO READ A STAGED RECORD FILE. `json.loads` plus
    `expand_result`; the dict returned is what `Log.to_json` produced."""
    return expand_result(json.loads(Path(path).read_text()))


def dumps_for_file(result: dict, **kw: Any) -> str:
    """`json.dumps` of `pooled_result(result)`; `kw` as for `json.dumps`."""
    return json.dumps(pooled_result(result), **kw)


#: ROADMAP 2.249: the levels `dump_to_file` walks itself; everything below
#: them is one `json.dumps` call per element.
_STREAM_DEPTH = 3


def _stream(obj: Any, write, enc, depth: int) -> None:
    if depth > 0 and isinstance(obj, dict) and all(isinstance(k, str) for k in obj):
        write("{")
        first = True
        for k, v in obj.items():
            if not first:
                write(",")
            first = False
            write(enc(k))
            write(":")
            _stream(v, write, enc, depth - 1)
        write("}")
    elif depth > 0 and isinstance(obj, list):
        write("[")
        for i, v in enumerate(obj):
            if i:
                write(",")
            write(enc(v))
        write("]")
    else:
        write(enc(obj))


@contextlib.contextmanager
def gc_paused():
    """⚠️ ROADMAP 2.249, SPEED ONLY: the cyclic collector off for a block that builds millions of small acyclic objects.

    Python runs a collection every few hundred allocations, and a generation-2 pass walks EVERY tracked object: with
    a staged record in memory (tens of millions of objects) pooling one 4-page Brahms record spent 62 of its 69 s
    in the collector, not in the pooling (measured: 69 s collector on, 7 s off). Nothing in such a block makes a
    reference cycle, so nothing waits on the collector there; it is switched back on (if it was on) as the block
    ends, and a collection may then run as usual. Changes no value."""
    was = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was:
            gc.enable()


def dump_to_file(result: dict, path: Union[str, Path]) -> int:
    """⚠️ ROADMAP 2.249: the record FILE, written as it is encoded.

    BYTE-IDENTICAL to `dumps_for_file(result, separators=(",", ":"),
    default=str)` (`test_record_stream.py` holds the two up against each
    other), but the whole-record string -- ~20 GB on the Brahms movement,
    held two or three times over by `json.dumps` + `write_text`'s encode --
    never exists: the envelope and the `record` dict are walked here and each
    row is one `json.dumps` call written straight to the file. Returns the
    bytes written."""
    enc = json.JSONEncoder(separators=(",", ":"), default=json_default).encode
    n = 0
    with open(path, "w", encoding="utf-8", buffering=1 << 20) as fh:
        def write(s: str) -> None:
            nonlocal n
            n += len(s)
            fh.write(s)
        with gc_paused():
            _stream(_streamed_pooled_result(result), write, enc, _STREAM_DEPTH)
    return n
