"""The three scores of `CRITERION.md`, over a whole page. REACH FIRST.

SCORE 1  READING   — at `--cell`, how many staves yield a meter-shaped stack?
SCORE 2  REFUSAL   — at the control cells, how many yield one? Must be ZERO.
SCORE 3  MECHANICAL— over EVERY cell, how many components does the line bridge
                     give complete-and-separated that neither single image does?

⚠️ TWO ARMS, ALWAYS, AND THE CONTROL IS THE POINT. `bridge` requires every
pixel of the gap to be one erasure TOOK — the multi-membership claim.
`dilate` requires only that the gap be short. If naive dilation does the same
job, multi-membership adds nothing; if it joins what the bridge refuses, the
`removed` requirement is what buys the refusal. Both are reported side by side
for all three scores.

⚠️ THE SHAPE WINDOW IS THE PRIOR JOB'S, read off Sean's 400-dpi crops and not
fitted to anything here.

⚠️ SCORE 3 IS A COUNT OF COMPONENTS, NOT OF MARKS. Nothing here knows what a
mark is; "merged under intact" means the intact component that contains this
group also contains erased ink the bridge did NOT join to it, which is a
measurable fact about the two partitions and not a judgement about glyphs.

Usage:
    python3 probe/arm.py <pdf> <page> --cell 6 --controls 7,8,9 --out out/arm.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from bridge import (load_page, pixel_sets, components, cell_units,   # noqa: E402
                    bridge_join, groups_of)

#: IMPORTED IN SPIRIT from `omr-ink-gather-2026-09/probe/target_cell.py`:
#: a two-space-wide stack of digits spanning the staff, standing clear of the
#: barline. Read off the print, never fitted.
W_MIN, W_MAX = 1.4, 2.4
H_MIN, H_MAX = 3.2, 5.0
X_MIN, X_MAX = 0.8, 2.6

ARMS = ("bridge", "dilate")


def _cell_result(c, arm: str, bound_mult: float):
    sets = pixel_sets(c)
    sp, thick = cell_units(c)
    if sets is None or not sp or not thick:
        return None
    intact, erased, removed = sets
    bound = max(1, int(round(thick * bound_mult)))
    n, labels, stats = components(erased)
    if n <= 1:
        return {"sp": sp, "bound": bound, "n_erased": 0, "groups": {},
                "n_joined_groups": 0, "n_merged_and_broken": 0,
                "meter_shaped": [], "edges": 0, "gaps": []}
    parent, edges = bridge_join(labels, removed, bound=bound,
                                require_removed=(arm == "bridge"))
    groups = groups_of(parent, stats)

    ni, ilabels, istats = components(intact)
    # For each erased label, which intact component holds it? (the dominant one)
    owner = {}
    for lab in range(1, n):
        x, y, w, h, _a = (int(stats[lab, k]) for k in range(5))
        sub = ilabels[y:y + h, x:x + w][labels[y:y + h, x:x + w] == lab]
        v = sub[sub > 0]
        owner[lab] = int(np.bincount(v).argmax()) if v.size else 0

    joined = {g: v for g, v in groups.items() if len(v["members"]) >= 2}
    merged_and_broken = 0
    for g, v in joined.items():
        owners = {owner[m] for m in v["members"] if owner[m]}
        if not owners:
            continue
        # Is the intact component that holds this group ALSO holding erased ink
        # the bridge did not join here?  That is "merged under intact-only".
        others = {lab for lab in range(1, n)
                  if owner[lab] in owners and parent[lab] not in (g,)}
        if others:
            merged_and_broken += 1

    meter = []
    for g, v in groups.items():
        w_sp, h_sp, x_sp = v["w"] / sp, v["h"] / sp, v["x0"] / sp
        if (W_MIN <= w_sp <= W_MAX and H_MIN <= h_sp <= H_MAX
                and X_MIN <= x_sp <= X_MAX):
            meter.append({"w_sp": round(w_sp, 2), "h_sp": round(h_sp, 2),
                          "x_sp": round(x_sp, 2),
                          "members": len(v["members"])})
    return {"sp": sp, "bound": bound, "n_erased": n - 1,
            "n_joined_groups": len(joined),
            "n_merged_and_broken": merged_and_broken,
            "meter_shaped": meter, "edges": len(edges),
            "gaps": [e[2] for e in edges]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=6)
    ap.add_argument("--controls", default="7,8,9")
    ap.add_argument("--bound-mult", type=float, default=1.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    t0 = time.time()
    _pws, cells = load_page(a.pdf, a.page)
    staves = sorted({c.staff_index for c in cells})
    print(f"REACH  staves={len(staves)}  cells={len(cells)}  "
          f"prepare={time.time() - t0:.1f}s")
    if not cells:
        print("DEAD: no cells")
        return 2

    controls = [int(s) for s in a.controls.split(",") if s.strip()]
    report = {"page": a.page, "cell": a.cell, "controls": controls,
              "bound_mult": a.bound_mult, "arms": {}}

    for arm in ARMS:
        t1 = time.time()
        per = {}
        for c in cells:
            r = _cell_result(c, arm, a.bound_mult)
            if r is not None:
                per[(c.staff_index, c.measure_index)] = r
        secs = time.time() - t1
        if not per:
            print(f"DEAD: arm {arm} produced no cell result")
            return 2

        n_comp = sum(r["n_erased"] for r in per.values())
        joined = sum(r["n_joined_groups"] for r in per.values())
        mb = sum(r["n_merged_and_broken"] for r in per.values())
        gaps = [g for r in per.values() for g in r["gaps"]]

        read_hits = [(st, r["meter_shaped"]) for (st, ci), r in per.items()
                     if ci == a.cell and r["meter_shaped"]]
        read_joined = [(st, m) for st, ms in read_hits for m in ms
                       if m["members"] >= 2]
        ctrl_hits = {ci: [(st, r["meter_shaped"])
                          for (st, cc), r in per.items()
                          if cc == ci and r["meter_shaped"]]
                     for ci in controls}

        print(f"\n=== ARM {arm}  ({secs:.1f}s, bound = "
              f"{a.bound_mult}x measured line thickness) ===")
        print(f"  components (erased)            {n_comp}")
        print(f"  groups the join actually made  {joined}"
              f"   ({100.0 * joined / max(n_comp, 1):.2f}% of components)")
        print(f"  ... AND merged under intact    {mb}"
              f"   ({100.0 * mb / max(n_comp, 1):.2f}%)  <- SCORE 3")
        if gaps:
            print(f"  bridge gaps px: min={min(gaps)} median="
                  f"{int(np.median(gaps))} max={max(gaps)}")
        print(f"  SCORE 1 READING  cell {a.cell}: "
              f"{len(read_hits)} of {len(staves)} staves carry a meter-shaped "
              f"group; {len(read_joined)} of those were BUILT by the join")
        for ci in controls:
            print(f"  SCORE 2 REFUSAL  cell {ci}: {len(ctrl_hits[ci])} "
                  f"meter-shaped group(s)"
                  f"{'  <-- FALSE POSITIVE' if ctrl_hits[ci] else '  ok'}")

        report["arms"][arm] = {
            "seconds": round(secs, 2), "components": n_comp,
            "joined_groups": joined, "merged_and_broken": mb,
            "gap_min": min(gaps) if gaps else None,
            "gap_median": int(np.median(gaps)) if gaps else None,
            "gap_max": max(gaps) if gaps else None,
            "score1_staves_with_meter_shape": len(read_hits),
            "score1_built_by_the_join": len(read_joined),
            "score2": {str(ci): len(ctrl_hits[ci]) for ci in controls},
            "n_staves": len(staves),
        }

    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=1))
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
