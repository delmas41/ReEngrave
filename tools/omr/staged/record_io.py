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

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .record import Kind, Subject

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


def pool_id_lists(record: dict) -> dict:
    """The record with its repeated verdict id lists pooled.

    Returns a NEW dict (the input's verdict dicts are copied, never
    mutated); returns the input itself when nothing qualifies, so a small
    record is unchanged in identity as well as content. Self-checks by
    expanding its own output and comparing every pooled field to the input;
    raises `PoolMismatch` on any difference.
    """
    verdicts: List[dict] = list(record.get("verdicts") or ())
    if not verdicts:
        return record
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

    out_verdicts = [dict(v) for v in verdicts]

    # ── flat fields: one shared core per group, private ids inserted ───────
    for fld in FLAT_FIELDS:
        groups: Dict[tuple, List[int]] = defaultdict(list)
        for idx, v in enumerate(verdicts):
            lst = v.get(fld)
            if isinstance(lst, list) and len(lst) >= MIN_POOL_IDS:
                groups[_group_key(v)].append(idx)
        for members in groups.values():
            if len(members) < 2:
                continue
            first = verdicts[members[0]][fld]
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
                lst = verdicts[idx][fld]
                ins = _encode(lst, core)
                # Not an in-order subsequence, or more private than shared:
                # inline, exactly as before.
                if ins is None or 2 * len(ins) > len(lst):
                    continue
                if pid is None:
                    pid = intern(core)
                out_verdicts[idx][fld] = {REF_KEY: pid, INS_KEY: ins}

    # ── correlated: inner lists interned by content where repeated ─────────
    seen: Counter = Counter()
    for v in verdicts:
        for g in v.get(GROUPED_FIELD) or ():
            if isinstance(g, list) and len(g) >= MIN_POOL_IDS:
                seen[tuple(g)] += 1
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
            out_verdicts[idx][GROUPED_FIELD] = enc

    if not pools:
        return record

    # ── the control: expand our own output and compare ─────────────────────
    check = [dict(v) for v in out_verdicts]
    _expand_verdicts(check, pools)
    for orig, back in zip(verdicts, check):
        for fld in FLAT_FIELDS + (GROUPED_FIELD,):
            if orig.get(fld) != back.get(fld):
                raise PoolMismatch(
                    f"{orig.get('id')}.{fld}: pooled spelling does not "
                    f"expand back to the input (refusing to write)")

    out = dict(record)
    out["verdicts"] = out_verdicts
    out[POOL_KEY] = pools
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
    return record


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
