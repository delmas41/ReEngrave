#!/usr/bin/env python3
"""lane-ledger-exclusion (2026-10-04): arm table for the three exclusion rules
(and `drop_rungs_beyond_head`), scored on the 2.44c truth sets (Litolff 44,
Brahms 11), STAFF POSITION against the reference.

Control = fix1_far (near_edge_ledgers + restore_masked_near_edge +
far_side_ledger, four_causes_cd) = Litolff 32/10/2, Brahms 11/0/0; with
`drop` 33/9/2.  Rules (all default OFF in the library):
  same  -- `exclusion_boxes_for(drop_same_ink_other_staff=True)`: a box owned
           by ANOTHER staff that overlaps the subject's by > half of the
           smaller box is the same ink detected twice, not blanked
  own   -- `exclusion_rules(own_box=...)`: the subject's own box is never
           blanked
  one   -- `exclusion_rules(one_sided=True)`: a thin, flat, long-enough jut
           out of ONE side of a neighbour's box keeps its row
  conn  -- (lane-ledger-accidental) continuation counts only connected ink
  drop  -- (lane-ledger-accidental) rungs beyond the head's far edge not counted

    python3 benchmarks/omr-local-staff-2026-09/score_exclusion.py [--json f] [--arms a,b]
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
RULES = {
    "same": dict(drop_same_ink_other_staff=True),
    "own": dict(own_box_inviolate=True),
    "one": dict(one_sided_jut=True),
}
ARMS = {
    "control": {},
    "same": RULES["same"],
    "own": RULES["own"],
    "one": RULES["one"],
    "same+one": {**RULES["same"], **RULES["one"]},
    "all": {**RULES["same"], **RULES["own"], **RULES["one"]},
    "drop": dict(drop_beyond_head=True),
    "all+drop": {**RULES["same"], **RULES["own"], **RULES["one"],
                 "drop_beyond_head": True},
    "same+drop": {**RULES["same"], "drop_beyond_head": True},
    "same+one+drop": {**RULES["same"], **RULES["one"], "drop_beyond_head": True},
    "conn+same+one+drop": {**RULES["same"], **RULES["one"],
                           "drop_beyond_head": True, "connected_continuation": True},
    "one+drop": {**RULES["one"], "drop_beyond_head": True},
    "conn+one": {**RULES["one"], "connected_continuation": True},
    "conn+same": {**RULES["same"], "connected_continuation": True},
    "conn+same+one": {**RULES["same"], **RULES["one"], "connected_continuation": True},
    "conn+one+drop": {**RULES["one"], "drop_beyond_head": True,
                      "connected_continuation": True},
    "conn+same+drop": {**RULES["same"], "drop_beyond_head": True,
                       "connected_continuation": True},
    # `one` with the stricter same-thickness-along-the-run test (NOT adopted)
    "conn+same+one(strict)+drop": {**RULES["same"], **RULES["one"], "thick_tol": 1,
                                   "drop_beyond_head": True, "connected_continuation": True},
    "conn+all+drop": {**RULES["same"], **RULES["own"], **RULES["one"],
                      "drop_beyond_head": True, "connected_continuation": True},
}
WRONG_REFERENCE = {"glyph/3/0/0/6/2"}      # Sean 2026-10-04 (reference wrong)


def read(h, **kw):
    from tools.omr.annotate import ledger_grid as lg
    kw = dict(kw)
    old = lg.ONE_SIDED_JUT_THICKNESS_TOL_PX
    lg.ONE_SIDED_JUT_THICKNESS_TOL_PX = kw.pop("thick_tol", old)
    try:
        return ec.score.reader_absolute_position(
            h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
            page_accidental_boxes=h["acc"], four_causes_cd=True,
            **{**CONTROL, **kw})
    finally:
        lg.ONE_SIDED_JUT_THICKNESS_TOL_PX = old


def main():
    arms = ARMS
    if "--arms" in sys.argv:
        names = sys.argv[sys.argv.index("--arms") + 1].split(",")
        arms = {n: ARMS[n] for n in names}
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = {}
    for arm, kw in arms.items():
        res[arm] = {}
        for d, hs in heads.items():
            res[arm][d] = {}
            for h in hs:
                pos, reason = read(h, **kw)
                res[arm][d][h["subject"]] = dict(
                    pos=pos, reason=reason, truth=h["truth"],
                    v=ec.verdict(pos, h["truth"]))
    for arm in arms:
        for d in ts.DOCS:
            vs = [r["v"] for r in res[arm][d].values()]
            vs43 = [r["v"] for s, r in res[arm][d].items() if s not in WRONG_REFERENCE]
            print(f"{arm:14} {d:20} {ec.tally(vs)} n={len(vs)}"
                  f"   (excl. 3/0/0/6/2: {ec.tally(vs43)})")
    base = "control" if "control" in arms else list(arms)[0]
    for arm in list(arms):
        if arm == base:
            continue
        print(f"\n--- {arm} vs {base}: every changed head ---")
        for d in ts.DOCS:
            for s, r in res[arm][d].items():
                o = res[base][d][s]
                if (r["pos"], r["v"]) != (o["pos"], o["v"]):
                    print(f"{d[:8]} {s:20} {o['pos']!s:>5} {o['v']:7} -> "
                          f"{r['pos']!s:>5} {r['v']:7} ref={r['truth']}  {r['reason'][:90]}")
        print("right heads broken:", [s for d in ts.DOCS for s, r in res[arm][d].items()
                                      if res[base][d][s]['v'] == 'right' and r['v'] != 'right'])
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
