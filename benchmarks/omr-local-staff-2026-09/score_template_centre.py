#!/usr/bin/env python3
"""lane-ledger-template-centre (2026-10-04): score the template centre as
`head_center_y` on the 2.44c truth sets. Fix 1 (near_edge_ledgers +
restore_masked_near_edge) is ON in every arm.

  control_default  -- today's reader (25/14/5 Litolff, 11/0/0 Brahms)
  F0               -- fix 1 (29/13/2, 11/0/0)
  F1               -- F0 + head_center_y = template centre on EVERY far head
  F2               -- F0 + template centre only where the template's own fit
                      passes round 4's MISS rule (IoU>=0.70, offset<=0.15 sp);
                      gate fixed before any arm was scored
  F3 (diagnostic)  -- F0 + template centre only on the 9 census heads

    python3 benchmarks/omr-local-staff-2026-09/score_template_centre.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import template_centre as tc  # noqa: E402
import edge_census as ec  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

FIX1 = dict(near_edge_ledgers=True, restore_masked_near_edge=True)


def centre_for(arm, h, fit):
    if arm in ("control_default", "F0"):
        return None
    if arm == "F1":
        return fit["tmpl_cy"]
    if arm == "F2":
        return fit["tmpl_cy"] if fit["trusted"] else None
    if arm == "F3":
        return fit["tmpl_cy"] if h["subject"] in tc.CENSUS_9 else None
    raise KeyError(arm)


ARMS = ["control_default", "F0", "F1", "F2", "F3"]


def read(h, arm, fit):
    kw = {} if arm == "control_default" else dict(FIX1)
    cy = centre_for(arm, h, fit)
    return score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True, head_center_y=cy, **kw)


def run(fitted):
    res = {}
    for arm in ARMS:
        res[arm] = {}
        for doc, d in fitted.items():
            rows = {}
            for h in d["heads"]:
                pos, reason = read(h, arm, d["fits"][h["subject"]])
                rows[h["subject"]] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                          truth=h["truth"])
            res[arm][doc] = rows
    return res


def main():
    fitted = tc.all_fits()
    res = run(fitted)
    for arm in ARMS:
        for doc in ts.DOCS:
            vs = [r["v"] for r in res[arm][doc].values()]
            print(f"{arm:16} {doc:20} {ec.tally(vs)} n={len(vs)}")
    for arm in ("F1", "F2", "F3"):
        print(f"\n--- {arm} vs F0: every changed head ---")
        for doc in ts.DOCS:
            for s, r in res[arm][doc].items():
                b = res["F0"][doc][s]
                if (r["pos"], r["v"]) != (b["pos"], b["v"]):
                    f = fitted[doc]["fits"][s]
                    print(f"{doc[:8]} {s:18} {b['pos']!s:>5} {b['v']:7} -> {r['pos']!s:>5} {r['v']:7} "
                          f"ref={r['truth']} dy={f['dy_sp']:+.2f}sp IoU={f['iou']} trusted={f['trusted']}\n"
                          f"      F0: {b['reason'][:110]}\n      {arm}: {r['reason'][:110]}")
        broke = [s for doc in ts.DOCS for s, r in res[arm][doc].items()
                 if res["F0"][doc][s]["v"] == "right" and r["v"] != "right"]
        print("right heads broken vs F0:", broke)
    if "--json" in sys.argv:
        out = {arm: res[arm] for arm in ARMS}
        out["fits"] = {doc: d["fits"] for doc, d in fitted.items()}
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
