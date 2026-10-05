#!/usr/bin/env python3
"""lane-ledger-edge-fix (2026-10-04): score the near-edge-ledger fix on the
2.44c truth sets, arm by arm, with a per-head list of every change.

Arms (all `four_causes_cd=True`, the round-8 reader):
  default  -- today's reader (control: Litolff 25/14/5, Brahms 11/0/0)
  part1    -- `near_edge_ledgers=True`
  part12   -- part1 + `restore_masked_near_edge=True` (if built)

    python3 benchmarks/omr-local-staff-2026-09/score_edge_fix.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402  (load_heads, verdict, tally)
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

ARMS = {
    "default": dict(),
    "part1": dict(near_edge_ledgers=True),
}
if "restore_masked_near_edge" in score.reader_absolute_position.__code__.co_varnames:
    ARMS["part12"] = dict(near_edge_ledgers=True, restore_masked_near_edge=True)


def read(h, **kw):
    return score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True, **kw)


def run(heads_by_doc):
    res = {}
    for arm, kw in ARMS.items():
        res[arm] = {}
        for d, hs in heads_by_doc.items():
            rows = {}
            for h in hs:
                pos, reason = read(h, **kw)
                rows[h["subject"]] = dict(pos=pos, reason=reason,
                                          v=ec.verdict(pos, h["truth"]),
                                          truth=h["truth"])
            res[arm][d] = rows
    return res


def main():
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = run(heads)
    for arm in ARMS:
        for d in ts.DOCS:
            vs = [r["v"] for r in res[arm][d].values()]
            print(f"{arm:8} {d:20} {ec.tally(vs)} n={len(vs)}")
    for arm in ARMS:
        if arm == "default":
            continue
        print(f"\n--- {arm} vs default: every changed head ---")
        for d in ts.DOCS:
            for s, r in res[arm][d].items():
                b = res["default"][d][s]
                if (r["pos"], r["v"]) != (b["pos"], b["v"]):
                    print(f"{d[:8]} {s:20} {b['pos']!s:>5} {b['v']:7} -> "
                          f"{r['pos']!s:>5} {r['v']:7} ref={r['truth']}  {r['reason'][:90]}")
        broke = [(s) for d in ts.DOCS for s, r in res[arm][d].items()
                 if res["default"][d][s]["v"] == "right" and r["v"] != "right"]
        print("right heads broken:", broke)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
