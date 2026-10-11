"""ROADMAP 2.86 -- re-decide `Q.MEASURE_PARTITION` ONLY over a saved record's
own GATHER rows plus its saved `Q.SYSTEM_KEY` verdicts, STREAMING the input
(`ijson`) so a multi-GB record is never loaded whole. Base vs arm on ONE
record: run it twice, once with `--tree` pointing at an origin/main
worktree (the base decision) and once at the lane (the arm).

    python3 benchmarks/omr-measure-partition-2026-09/probe/readjudicate_2_86.py \
        REC --tree /path/to/worktree --out OUT.json

Reads only what `adjudicate_measure_partition` declares: `Q.BARLINE_COLUMN`
and the TAIL cell's `Q.GLYPH_BOX` rows (pass 1 finds each staff's
`n_cells`, pass 2 keeps only glyph rows in cell `n_cells - 1`), and the
saved `Q.SYSTEM_KEY` verdicts INJECTED exactly as saved, never recomputed
(they are inputs, not a baseline: CLAUDE.md §6b). Prints bars per system
and the running bar offset in reading order, which is what the export's
bar numbers inherit.

⚠️ BLIND TO GATHER (CLAUDE.md §4d): a zero here says nothing about a GATHER
change. ⚠️ The base tree's decision does not want `Q.SYSTEM_KEY`; the
injected verdicts are simply unread there.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path


def _outcome(Outcome, word):
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[word]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--tree", default=str(Path(__file__).resolve().parents[3]),
                    help="the worktree whose decision to run (default: this one)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tree)

    import ijson
    from tools.omr.staged import adjudicate as A
    from tools.omr.staged import adjudicators  # noqa: F401
    from tools.omr.staged.record import Kind, Log, Outcome, Q, Subject, Verdict

    t0 = time.time()
    n_cells = {}
    with open(a.record, "rb") as fh:
        for it in ijson.items(fh, "record.observations.item", use_float=True):
            if it["quantity"] == Q.BARLINE_COLUMN:
                n_cells[it["subject"]] = (it, int(it["value"]))
    log = Log()
    for key, (it, _n) in n_cells.items():
        log.observe(Subject.from_key(key), Q.BARLINE_COLUMN, it["value"],
                    reader=it["reader"], frame=it["frame"],
                    score=it.get("score"), **dict(it.get("detail") or {}))
    # Every staff's own tail index, per system: the decision on one staff
    # reads EVERY staff's cell at ITS last index, so all of them are kept.
    tail_of = collections.defaultdict(set)
    for key, (_it, n) in n_cells.items():
        s = Subject.from_key(key)
        tail_of[(s.page, s.system)].add(n - 1)
    n_glyph = 0
    with open(a.record, "rb") as fh:
        for it in ijson.items(fh, "record.observations.item", use_float=True):
            if it["quantity"] != Q.GLYPH_BOX:
                continue
            s = Subject.from_key(it["subject"])
            if s.cell is None or s.cell not in tail_of.get((s.page, s.system), ()):
                continue
            log.observe(s, Q.GLYPH_BOX, it["value"], reader=it["reader"],
                        frame=it["frame"], score=it.get("score"),
                        **dict(it.get("detail") or {}))
            n_glyph += 1
    log.freeze()
    current, superseded = {}, set()
    with open(a.record, "rb") as fh:
        for it in ijson.items(fh, "record.verdicts.item", use_float=True):
            if it["quantity"] not in (Q.SYSTEM_KEY, Q.MEASURE_PARTITION):
                continue
            if it.get("supersedes"):
                superseded.add(it["supersedes"])
            current[(it["quantity"], it["subject"])] = it
    saved_partition = {}
    for (q, key), v in current.items():
        if v["id"] in superseded:
            continue
        if q == Q.MEASURE_PARTITION:
            saved_partition[key] = v.get("value")
            continue
        log.record(Verdict(id=v["id"], subject=Subject.from_key(key),
                           quantity=q, outcome=_outcome(Outcome, v["outcome"]),
                           value=v.get("value"), decider=v["decider"],
                           reason=v["reason"]))
    print(f"  {len(n_cells)} staves, {n_glyph} tail glyph rows "
          f"({round(time.time() - t0, 1)}s)", file=sys.stderr)

    spec = A.REGISTRY[Q.MEASURE_PARTITION]
    per_system = collections.OrderedDict()
    reasons = collections.Counter()
    for key in sorted(n_cells, key=lambda k: Subject.from_key(k)):
        sub = Subject.from_key(key)
        v = A.adjudicate_one(log, spec, sub)
        reasons[v.reason] += 1
        row = per_system.setdefault(sub.at(Kind.SYSTEM).to_key(), {"bars": collections.Counter(),
                                     "saved": collections.Counter(),
                                     "reasons": collections.Counter(),
                                     "detail": None})
        row["bars"][v.value] += 1
        row["saved"][saved_partition.get(key)] += 1
        row["reasons"][v.reason] += 1
        if v.detail and row["detail"] is None:
            row["detail"] = dict(v.detail)
    out = []
    running = 0
    for sys_key, row in per_system.items():
        bars = row["bars"].most_common(1)[0][0]
        running += bars if isinstance(bars, int) else 0
        out.append({"system": sys_key, "bars": bars,
                    "bars_by_staff": dict(row["bars"]),
                    "saved_bars": dict(row["saved"]),
                    "reasons": dict(row["reasons"]),
                    "detail": row["detail"], "bars_through_here": running})
        print(f"{sys_key:28s} bars={bars!s:>3} through={running:4d} "
              f"{dict(row['reasons'])} {row['detail'] or ''}")
    print("reasons:", dict(reasons))
    if a.out:
        json.dump({"record": a.record, "tree": a.tree, "systems": out,
                   "reasons": dict(reasons)}, open(a.out, "w"), indent=1,
                  default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
