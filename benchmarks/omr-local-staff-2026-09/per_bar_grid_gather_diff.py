"""ROADMAP 2.57: flag off vs on, the same one-page GATHER+ADJUDICATE re-gather.

  python3 benchmarks/omr-local-staff-2026-09/per_bar_grid_gather_diff.py off.json on.json [truth.json truth_key]

Reads each record ONLY via record_io.load_record. Per glyph: NOTEHEAD_STAFF_POSITION
(ADJUDICATE's staff position, the quantity the grid feeds) in both arms; counts
glyph sets, heads whose position changed (by how many steps), and, when a truth
file is given (the 2.44c far-head truth set), whether any truth head moved.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record  # noqa: E402


def positions(path):
    r = load_record(path)
    pos, cells = {}, Counter()
    for o in r["record"]["observations"]:
        if o["quantity"] == "notehead_staff_position":
            pos[o["subject"]] = o["value"]
        elif o["quantity"] == "cell_box":
            cells[o["subject"]] += 1
    return pos, len(cells), r["provenance"]


def main(off, on, truth=None, key=None):
    a, na, pa = positions(off)
    b, nb, pb = positions(on)
    both = sorted(set(a) & set(b))
    chg = [(g, a[g], b[g]) for g in both if a[g] != b[g]]
    d = Counter()
    for g, x, y in chg:
        try:
            d[round(float(y) - float(x), 2)] += 1
        except Exception:
            d["non-numeric"] += 1
    print(f"cells {na}/{nb}; heads with a position: off {len(a)} on {len(b)}; in both {len(both)}; only-off {len(set(a) - set(b))} only-on {len(set(b) - set(a))}")
    print(f"position changed: {len(chg)}  by step: {dict(sorted(d.items(), key=lambda kv: str(kv[0])))}")
    if truth:
        ts = {t["subject"] for t in json.load(open(truth))[key]}
        moved = [(g, a.get(g), b.get(g)) for g in ts if g in a and g in b and a[g] != b[g]]
        present = [g for g in ts if g in a]
        print(f"truth-set heads on this page: {len(present)}; moved: {moved}")
    json.dump(chg, open(Path(on).with_suffix(".posdiff.json"), "w"))
    print("dirty:", pa.get("dirty"), pb.get("dirty"))


if __name__ == "__main__":
    main(*sys.argv[1:])
