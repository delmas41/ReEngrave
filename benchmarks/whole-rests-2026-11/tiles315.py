"""ROADMAP 2.315 -- 12 blind tiles of bars the change CHANGED (two plates, six each, random seed 2315), drawn like the 2.311 red-bar tiles: one staff, the bar barline to
barline in one thin orange box, a full neighbouring bar either side, >= 450 px tall, same width, two to a row, nothing else drawn; the key (which arm wrote what) is a
separate file outside the folder.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/whole-rests-2026-11/tiles315.py --work out/lane-report/2.315-r1/work --out out/print/2.315-r1

A changed bar = a place the ON file writes (or no longer writes) that the OFF file does not, from the lane report's own `symbols.json` of each arm.
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import random
from pathlib import Path

from redbars_tiles import staff_geometry
from redbars_tiles_more import draw_tile, sheet

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2311/"
REC = {"litolff": S + "lit-a.record.json", "brahms": S + "bra-a.record.json"}
FACTS = {"litolff": S + "lit-a.facts.json", "brahms": S + "bra-a.facts.json"}


def bar_of(rg):
    p = rg.split("/")
    return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))


def changed_bars(work: Path, plate: str):
    off = json.load(open(work / ("%s.off.symbols.json" % plate)))
    on = json.load(open(work / ("%s.on.symbols.json" % plate)))
    side = {}
    for arm, d in (("off", off), ("on", on)):
        for h in d["hosts"]:
            if h["kind"] != "rest":
                continue
            side.setdefault(bar_of(h["rg"]), {}).setdefault(arm, []).append(h["rg"])
    out = []
    for bar, v in side.items():
        a, b = sorted(v.get("off", [])), sorted(v.get("on", []))
        if a != b:
            out.append(bar)
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2315)
    ap.add_argument("--n", type=int, default=6)
    a = ap.parse_args()
    work = Path(a.work)
    rng = random.Random(a.seed)
    chosen, pool_n = [], {}
    for plate in ("litolff", "brahms"):
        pool = changed_bars(work, plate)
        pool_n[plate] = len(pool)
        chosen += [(plate, b) for b in rng.sample(pool, min(a.n, len(pool)))]
    geo, facts = {}, {}
    for plate in ("litolff", "brahms"):
        wanted = set()
        for pl, b in chosen:
            if pl == plate:
                wanted.add("staff/%d/%d/%d" % b[:3])
                wanted.add("cell/%d/%d/%d/%d" % b)
        geo[plate] = staff_geometry(REC[plate], wanted)
        facts[plate] = json.load(open(FACTS[plate]))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tiles, key = [], []
    for n, (plate, b) in enumerate(chosen, 1):
        bar = dict(page=b[0], system=b[1], staff=b[2], cell=b[3])
        crop, geom = draw_tile(plate, facts[plate], geo[plate], bar)
        crop.save(out / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append(dict(tile=n, plate=plate, page=b[0], system=b[1], staff=b[2], cell=b[3], pool=pool_n[plate], **geom))
    sheet(tiles, out / "sheet.png")
    (out / "README.md").write_text("Twelve pieces of the printed page, one staff each. ONE thin orange box = one bar. Nothing else is drawn.\n\n"
                                   "Question, for every tile: what is printed in the boxed bar? (rests, notes with their values, or empty.)\n\nAnswer by tile number.\n")
    Path(str(out) + "-key.json").write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(tiles), "pools", pool_n, "heights", [round(t.height) for t in tiles])


if __name__ == "__main__":
    main()
