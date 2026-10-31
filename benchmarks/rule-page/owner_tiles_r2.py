"""ROADMAP 2.238 round 2: Sean's tiles -- the 3 places round 1 wrote wrong (2.238 tiles 1, 4, 11; now as main writes them), plus 9 NEW
changed places of the round-2 lane report (never a place already shown in the 2.237 or 2.238 tiles; one per ink), shuffled.

    python3 benchmarks/rule-page/owner_tiles_r2.py WORK_DIR OUT_DIR [--seed 22382]

One staff each, a thin orange box sized to the mark (`lane_report.cut_tiles`), key.json written OUTSIDE the tile folder.
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR  # noqa: E402


def main(work, out, seed=22382):
    work, out = pathlib.Path(work), pathlib.Path(out)
    seen = set()
    for kf in (ROOT / "out/print/2.237-tiles/key.json", ROOT / "out/print/2.238-tiles/key.json"):
        seen |= {(k["plate"], k["rg"]) for k in json.load(open(kf))}
    fixed = [dict(k, role="fixed", side="as_main") for k in json.load(open(ROOT / "out/print/2.238-tiles/key.json")) if k["tile"] in (1, 4, 11)]
    for f in fixed:
        for x in ("tile", "crop_origin", "position", "cell_map"):
            f.pop(x, None)
    pool = []
    for p in ("litolff", "brahms"):
        off = json.loads((work / ("%s.off.symbols.json" % p)).read_text())
        on = json.loads((work / ("%s.on.symbols.json" % p)).read_text())
        d = LR.diff_arms(off, on, tol=0.5 * LR.PLATES[p]["unit"])
        for c in d["changes"]:
            if c.get("box") and c.get("page") is not None and c["kind"] in LR.LOCATED_KINDS and (p, c["rg"]) not in seen:
                pool.append(dict(c, plate=p, role="case"))
    rng = random.Random(seed)
    rng.shuffle(pool)
    cases = []
    for c in pool:
        if len(cases) >= 9:
            break
        staff = lambda x: (x["plate"],) + tuple(x["rg"].split("/")[1:4])     # one tile per staff
        if any(LR._same_ink(c, x) for x in cases + fixed) or any(staff(c) == staff(x) for x in cases + fixed):
            continue
        cases.append(c)
    items = fixed + cases
    rng.shuffle(items)
    print(LR.cut_tiles(items, out), "changed places available:", len(pool))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index("--seed") + 1]) if "--seed" in a else 22382)
