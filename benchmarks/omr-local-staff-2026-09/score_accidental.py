#!/usr/bin/env python3
"""lane-ledger-accidental (2026-10-04): arm table for the three keyword
rules, scored on the 2.44c truth sets (Litolff 44, Brahms 11), STAFF POSITION
against the reference.

Control = today's best reader (fix1_far: near_edge_ledgers +
restore_masked_near_edge + far_side_ledger, all with four_causes_cd) =
Litolff 32/10/2, Brahms 11/0/0.

Arms add (all default OFF in the library):
  conn   -- exclusion's continuation test counts only ink CONNECTED to the
            neighbour head's own ink (Sean 10-01: a white gap is never a stub)
  drop   -- the walk's rungs farther out than the head's own far edge (by
            > 0.5 sp) are another head's ledgers and are not counted
  one    -- (with conn) a thin flat jut on ONE side of a neighbour head keeps
            that row (Sean 10-01: "only out on one side")

    python3 benchmarks/omr-local-staff-2026-09/score_accidental.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

CONTROL = dict(near_edge_ledgers=True, restore_masked_near_edge=True,
               far_side_ledger=True)
ARMS = {
    "control": {},
    "conn": dict(connected_continuation=True),
    "drop": dict(drop_beyond_head=True),
    "conn+drop": dict(connected_continuation=True, drop_beyond_head=True),
}
WRONG_REFERENCE = {"glyph/3/0/0/6/2"}      # Sean 2026-10-04 (reference wrong)


def read(h, **kw):
    return ec.score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True,
        **{**CONTROL, **kw})


def main():
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = {}
    for arm, kw in ARMS.items():
        res[arm] = {}
        for d, hs in heads.items():
            res[arm][d] = {}
            for h in hs:
                pos, reason = read(h, **kw)
                res[arm][d][h["subject"]] = dict(
                    pos=pos, reason=reason, truth=h["truth"],
                    v=ec.verdict(pos, h["truth"]))
    for arm in ARMS:
        for d in ts.DOCS:
            vs = [r["v"] for r in res[arm][d].values()]
            vs43 = [r["v"] for s, r in res[arm][d].items() if s not in WRONG_REFERENCE]
            print(f"{arm:14} {d:20} {ec.tally(vs)} n={len(vs)}"
                  f"   (excl. 3/0/0/6/2: {ec.tally(vs43)})")
    for arm in list(ARMS)[1:]:
        print(f"\n--- {arm} vs control: every changed head ---")
        for d in ts.DOCS:
            for s, r in res[arm][d].items():
                o = res["control"][d][s]
                if (r["pos"], r["v"]) != (o["pos"], o["v"]):
                    print(f"{d[:8]} {s:20} {o['pos']!s:>5} {o['v']:7} -> "
                          f"{r['pos']!s:>5} {r['v']:7} ref={r['truth']}  {r['reason'][:90]}")
        print("right heads broken:", [s for d in ts.DOCS for s, r in res[arm][d].items()
                                      if res['control'][d][s]['v'] == 'right' and r['v'] != 'right'])
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
