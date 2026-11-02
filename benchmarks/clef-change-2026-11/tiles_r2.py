"""2.251 round 2's 12 blind tiles: Sean's three round-1 places (5 the header G clef, 10 the F clef with the rest beside it, 11 the
Brahms F clef) drawn with what the reader does NOW, and 9 fresh places (seed stated). One thin orange box per tile, sized to the
mark (the claim's own area where a claim is made; the detector's box where nothing is claimed). Key outside tiles/.

python3 work-2.251/tiles_r2.py OUTDIR SEED
"""
import json, os, random, sys
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import tiles as T1  # noqa: E402  (pool(), tile())
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

FIXED = [
    dict(plate="litolff", page=6, system=0, staff=5, area=[368.4, 1157.0, 419.8, 1272.1], cls="r1-tile5", family="G",
         read=None, why="not claimed now (header G clef: its tail below the staff; a clef-sized clefG box stands there)"),
]


def fixed_f(plate, page, system, staff, box, label):
    import crops
    ink = np.asarray(crops.page_img(plate, page).convert("L")) < 128
    d = crops.cmap(plate, page)
    st = sorted([t for t in d["staves"] if t["system_index"] == system], key=lambda t: t["line_ys"][0])[staff]
    ly = st["line_ys"]; sp = (ly[4] - ly[0]) / 4
    got = CP.read_box("clefF", box, ink, CP.local_lines(ink, ly, sp, box[0]), sp)
    return dict(plate=plate, page=page, system=system, staff=staff, area=CP.f_claim_area(got, box, sp) if got["passed"] else list(box),
                cls=label, family="F", read=got["kind"], why=got["why"])


def main():
    out, seed = sys.argv[1], int(sys.argv[2])
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    rng = random.Random(seed)
    pick = list(FIXED)
    pick.append(fixed_f("litolff", 16, 0, 3, [926.175, 825.985, 980.8275, 874.18], "r1-tile10"))
    pick.append(fixed_f("brahms", 5, 1, 3, [1004.7, 4726.6, 1079.0, 4813.7], "r1-tile11"))
    old = json.load(open("out/print/2.251-tiles/key.json"))["tiles"]
    shown = {(t["plate"], t["page"], t["system"], t["staff"], round(t["area"][0] / 20)) for t in old}
    places = [(t["plate"], t["page"], t["system"], t["staff"], t["area"][0]) for t in old + pick]

    def seen(t):
        return any(t["plate"] == q[0] and t["page"] == q[1] and t["system"] == q[2] and t["staff"] == q[3]
                   and abs(t["area"][0] - q[4]) < 60 for q in places)
    P = [t for t in T1.pool() if not seen(t)]
    by = {k: [t for t in P if t["cls"] == k] for k in ("change", "header", "near")}
    print({k: len(v) for k, v in by.items()})

    def draw(cls, plate, n, family=None):
        c = [t for t in by[cls] if t["plate"] == plate and (family is None or t["family"] == family)]
        return rng.sample(c, min(n, len(c)))
    fresh = (draw("change", "litolff", 2, "C") + draw("change", "litolff", 2, "F") + draw("change", "brahms", 1, "C")
             + draw("change", "brahms", 1, "F") + draw("near", "litolff", 1) + draw("near", "brahms", 1) + draw("header", "brahms", 1))
    rest = [t for t in by["change"] if t not in fresh]
    while len(fresh) < 9 and rest:
        fresh.append(rest.pop(rng.randrange(len(rest))))
    pick += fresh[:9]
    rng.shuffle(pick)
    key = []
    for i, t in enumerate(pick, 1):
        T1.tile(t).save(os.path.join(out, "tiles", f"{i:02d}.png"))
        key.append(dict(tile=i, **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items() if k != "area"},
                        area=[round(v, 1) for v in t["area"]]))
    json.dump({"seed": seed, "what": "2.251 round-2 tiles: Sean's r1 places 5/10/11 as the reader does them now, + 9 fresh (shuffled)",
               "pool": {k: len(v) for k, v in by.items()}, "tiles": key}, open(os.path.join(out, "key.json"), "w"), indent=1)


main()
