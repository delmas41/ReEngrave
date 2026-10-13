#!/usr/bin/env python3
"""l283_tip_census: over the heads of a record that have a decided stem and a decided direction, the state of the tip row at the TRUE
tip end, with the measures of the abstentions: how many `crosses_both_sides` stand just over the left-area cut, how many `occupied` cover
only a graze of ink (`covered_area`), how many `ink_not_flag_shaped` have what out / arm / t_first. Where a cut sits relative to what is
actually found. ROADMAP 2.83 probe.

    python3 l283_tip_census.py --record rec.json [--pages 0,1]
"""
import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pages", default=None)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    run = RD.load_run(a.record)
    abst = collections.defaultdict(list)
    for o in run.abstentions:
        if o["quantity"] == Q.STEM_TIP_INK:
            abst[(o["subject"], (o.get("detail") or {}).get("stem_row_id"), (o.get("detail") or {}).get("end"))].append(o)
    obs = collections.defaultdict(list)
    for o in run.observations:
        if o["quantity"] == Q.STEM_TIP_INK:
            obs[(o["subject"], (o.get("detail") or {}).get("stem_row_id"), (o.get("detail") or {}).get("end"))].append(o)
    cnt = collections.Counter()
    left, covered, notshaped, roots = [], [], [], []
    for key, g in run.glyphs.items():
        if (pages is not None and g.page not in pages) or not (g.cls or "").startswith("notehead"):
            continue
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        if not (hs and hs["outcome"] == "decided" and sd and sd["outcome"] == "decided" and sd.get("value") in ("up", "down")):
            continue
        end = "top" if sd["value"] == "up" else "bottom"
        k = (g.cell_key, hs["value"], end)
        if k in obs:
            cnt["observed:" + ("flag" if obs[k][0]["value"] else "none")] += 1
        elif k in abst:
            d = abst[k][0].get("detail") or {}
            why = d.get("why") or abst[k][0]["reason"]
            cnt["abstained:" + why] += 1
            if why == "crosses_both_sides" and d.get("left_area") is not None:
                left.append(d["left_area"])
            if why == "occupied" and d.get("covered_area") is not None:
                covered.append(d["covered_area"])
            if why == "ink_not_flag_shaped":
                notshaped.append((d.get("out"), d.get("arm"), d.get("t_first"), d.get("area")))
    print(dict(cnt))
    print("crosses_both_sides left_area: n", len(left), "in (0.05, 0.08]:", sum(1 for v in left if 0.05 < v <= 0.08),
          "(0.08, 0.12]:", sum(1 for v in left if 0.08 < v <= 0.12), "(0.12, 0.3]:", sum(1 for v in left if 0.12 < v <= 0.3), "> 0.3:", sum(1 for v in left if v > 0.3))
    print("occupied covered_area (records from 2.83 v3 with the field): n", len(covered))
    print("ink_not_flag_shaped (out, arm, t_first, area):", sorted(notshaped, key=lambda t: -(t[3] or 0))[:25])


if __name__ == "__main__":
    main()
