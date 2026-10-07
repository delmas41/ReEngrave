"""ROADMAP 2.57 control: what the new per-bar grid does to the recorded heads.

The cell CROP and canonical scale do not depend on the grid (only the stored
rows do), so a head's recorded canonical box stays valid; its in-staff position
is re-read against the old and the new grid of its cell:
    step = round(2 * (y_centre - top_line) / spacing_canonical)      (half-steps from the top line)
Inputs: `grid_<doc>_*.json` from `per_bar_grid_one_line_off.py grid` (the canonical
rows of every cell under both arms) and the verifier's `<doc>.extract.json`
(`verify_staff_line_offsets.py extract`: record -> recorded head boxes).
  python3 benchmarks/omr-local-staff-2026-09/per_bar_grid_heads.py litolff|brahms <extract.json> <truth.json>
Only IN-STAFF heads (|old step| <= 8 half-steps from the top line, i.e. between
the outer lines +-0) are summarised as 'in staff'; ledger-side heads are counted
separately because the far-head reader, not the grid, answers them.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def step(box, canon):
    _n, _x, yc, _w, hc = box
    ycen = yc + hc / 2.0
    sp = (canon[-1] - canon[0]) / 4.0
    return (ycen - canon[0]) / (sp / 2.0)


def main(doc, extract, truth):
    grid = {}
    for f in glob.glob(str(HERE / "out" / f"grid_{doc}_*.json")):
        for r in json.load(open(f)):
            grid[r["cell"]] = r
    ex = json.load(open(extract))
    tr = json.load(open(truth))
    tkey = "beethoven5-litolff" if doc == "litolff" else "brahms1-breitkopf"
    truth_subj = {t["subject"] for t in tr[tkey]}
    n = Counter()
    deltas = Counter()
    changed_truth = []
    examples = []
    for g, h in ex["heads"].items():
        cell = "cell/" + "/".join(g.split("/")[1:5])
        r = grid.get(cell)
        if not r or "off" not in r or "on" not in r:
            n["no_grid"] += 1
            continue
        a, b = r["off"]["canon"], r["on"]["canon"]
        if a == b:
            n["same_grid"] += 1
            continue
        s0, s1 = step(h["box"], a), step(h["box"], b)
        in_staff = -0.5 <= s0 <= 8.5
        d = round(s1) - round(s0)
        n["grid_changed_head"] += 1
        if in_staff:
            n["in_staff_head_in_changed_cell"] += 1
            if d != 0:
                n["in_staff_step_changed"] += 1
                deltas[d] += 1
                examples.append((g, round(s0, 2), round(s1, 2)))
        if g in truth_subj:
            changed_truth.append((g, round(s0, 2), round(s1, 2)))
    print(doc, dict(n))
    print("  in-staff step change (new - old, in half-steps):", dict(sorted(deltas.items())))
    print("  truth-set far heads in a cell whose grid changed:", changed_truth)
    json.dump(examples, open(HERE / "out" / f"head_changes_{doc}.json", "w"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
