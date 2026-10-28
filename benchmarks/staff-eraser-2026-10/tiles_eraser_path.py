"""ROADMAP 2.213b: 12 blind tiles from a lane_report work dir, on NOTE / beam / flag / value changes ONLY.

    python3 benchmarks/staff-eraser-2026-10/tiles_2213b.py WORK_DIR OUT_DIR [seed]

lane_report's own picker draws words/dynamics tiles whose orange box is a HOST note's (place(), lines 340-345), so Sean answers the note. This script
re-uses its diff and picker unchanged but hands them only the four kinds that have ink of their own, then re-cuts tall (recrop_tiles.py).
Writes OUT_DIR/key.json (outside the tile folder) first, then recrop_tiles builds OUT_DIR/tiles and the final key.
"""
import json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.206/benchmarks/staff-eraser-2026-10").resolve().parents[1]))
from tools.omr.staged.lane_report import diff_arms, pick_tiles, PLATES

KEEP = {"note", "rest", "beam", "flag", "value", "pitch", "dot", "time", "meter"}
work, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2188
ch, same = {}, {}
for p in PLATES:
    f_off, f_on = work / ("%s.off.symbols.json" % p), work / ("%s.on.symbols.json" % p)
    if not f_off.exists():
        continue
    d = diff_arms(json.load(open(f_off)), json.load(open(f_on)), tol=0.5 * PLATES[p]["unit"])
    ch[p] = [c for c in d["changes"] if c["kind"] in KEEP]
    same[p] = [c for c in d["same"] if c["kind"] in KEEP]
    print(p, "changes kept", len(ch[p]), "of", len(d["changes"]))
items = pick_tiles(ch, same, seed, n_cases=9, n_controls=6)
_c = [i for i in items if i.get("role") == "control"]
items = [i for i in items if i.get("role") != "control"] + _c[:3]   # 9 cases + 3 controls = 12
for extra in range(1, 40):        # the picker draws controls only for the kinds it drew: top up with more controls until there are 12 tiles
    if len(items) >= 12:
        break
    have = {(i["plate"], i["rg"]) for i in items}
    for i in pick_tiles({}, same, seed + extra, n_cases=0, n_controls=3):
        if (i["plate"], i["rg"]) not in have and len(items) < 12 and i.get("role") == "control":
            items.append(i); have.add((i["plate"], i["rg"]))
out.mkdir(parents=True, exist_ok=True)
json.dump(items, open(out / "pre_key.json", "w"), default=str)
subprocess.check_call([sys.executable, str(pathlib.Path(__file__).parent / "recrop_tiles.py"), str(out / "pre_key.json"), str(out)])
