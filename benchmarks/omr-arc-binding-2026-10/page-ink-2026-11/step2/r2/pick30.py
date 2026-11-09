"""2.274 step 2 r2: the seeded look sample for criteria 1 and 2 (my look, not Sean's tiles).

    python3 pick30.py WORKDIR SLICEDIR OUT.json SEED plate:p,p [plate:p ...]

10 replaced + 10 new + 10 unchanged WRITTEN runs (all of a category if fewer), drawn with random.Random(SEED) from the pooled hold-out + new pages. Writes the sample (category, plate,
page, run, piece) and nothing else; `look.py` draws the crops.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    work, slices, out, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    pool = {"replaced": [], "new": [], "unchanged": []}
    for spec in sys.argv[5:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            for r in A.per_run(extra, off, boxes, runs):
                if r["status"] != "written":
                    continue
                cat = {"whole": "unchanged", "none": "new"}.get(r["off"], "replaced")
                pool[cat].append(dict(category=cat, plate=plate, page=p, run=r["ordinal"], piece=r.get("piece"), kind=r["kind"], off=r["off"]))
    rng = random.Random(seed)
    pick = []
    for cat in ("replaced", "new", "unchanged"):
        items = pool[cat]
        rng.shuffle(items)
        pick += items[:10]
    rng.shuffle(pick)
    for i, it in enumerate(pick, 1):
        it["n"] = i
    json.dump(dict(seed=seed, pools={k: len(v) for k, v in pool.items()}, sample=pick), open(out, "w"), indent=1)
    print({k: len(v) for k, v in pool.items()}, "picked", len(pick))


if __name__ == "__main__":
    main()
