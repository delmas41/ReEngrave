#!/usr/bin/env python3
"""lane-ledger-far-side-rule (2026-10-04): score the far-side ledger rule on
the 2.44c truth sets, arm by arm, with a per-head list of every change.

Arms (all `four_causes_cd=True`, the round-8 reader):
  default   -- today's reader (control: Litolff 25/14/5, Brahms 11/0/0)
  fix1      -- near_edge_ledgers + restore_masked_near_edge (29/13/2, 11/0/0)
  fix1_far  -- fix1 + far_side_ledger

Two reference exclusions (reference WRONG, Sean): `glyph/1/0/10/14/1` (dropped
by `edge_census.load_heads` as before, n=44) and, from 2026-10-04,
`glyph/3/0/0/6/2` (Sean: ON its arrowed line, -6; the reference -4 is wrong)
-- the "n=43" tallies drop it too.

    python3 benchmarks/omr-local-staff-2026-09/score_far_side.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

WRONG_REFERENCE = {"glyph/3/0/0/6/2"}          # Sean 2026-10-04

ARMS = {
    "default": dict(),
    "fix1": dict(near_edge_ledgers=True, restore_masked_near_edge=True),
    "fix1_far": dict(near_edge_ledgers=True, restore_masked_near_edge=True,
                     far_side_ledger=True),
}


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
    for excl, label in ((set(), "n=44/11"), (WRONG_REFERENCE, "n=43/11 (3/0/0/6/2 excluded)")):
        print(f"== {label}")
        for arm in ARMS:
            for d in ts.DOCS:
                vs = [r["v"] for s, r in res[arm][d].items() if s not in excl]
                print(f"{arm:9} {d:20} {ec.tally(vs)} n={len(vs)}")
    for a, b in (("default", "fix1"), ("fix1", "fix1_far")):
        print(f"\n--- {b} vs {a}: every changed head ---")
        for d in ts.DOCS:
            for s, r in res[b][d].items():
                o = res[a][d][s]
                if (r["pos"], r["v"]) != (o["pos"], o["v"]):
                    print(f"{d[:8]} {s:20} {o['pos']!s:>5} {o['v']:7} -> "
                          f"{r['pos']!s:>5} {r['v']:7} ref={r['truth']}  {r['reason'][:100]}")
        broke = [s for d in ts.DOCS for s, r in res[b][d].items()
                 if res[a][d][s]["v"] == "right" and r["v"] != "right"]
        print("right heads broken:", broke)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
