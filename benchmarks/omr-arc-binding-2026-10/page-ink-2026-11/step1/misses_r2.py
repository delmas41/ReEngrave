"""2.274 r2: 12 tiles of REAL detector-kept curves the ink reader did not cover whole (hold-out). Orange = the detector curve's box, blue = the run the reader read (partial), nothing else.
    python3 misses_r2.py HOLD2DIR OUTDIR     (indices are positions in bucket.py's `all` shuffle (seed 1), chosen by my look as real arcs)"""
import json, pathlib, random, re, sys
import cv2, numpy as np
wd, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
items = []
for p in sorted(wd.glob("*.step1.json")):
    stem = p.name.replace(".step1.json", "")
    J = json.load(open(p))
    for k, c in enumerate(J["curves"]):
        if not c["refused"] and c["best"] < 0.8:
            items.append((stem, k, c))
random.Random(1).shuffle(items)
PICK = [(0, "arc on / across staff lines and a barline"), (43, "arc on staff lines"), (64, "arc on staff lines"), (27, "flat arc on a staff line"),
        (1, "short tie into a stem"), (21, "short tie into a stem"), (23, "short tie into a stem"), (53, "short tie into a stem"),
        (17, "other: sparse"), (46, "other: partial run"), (68, "other: partial run"), (50, "other: heavy arc, sparse")]
ORANGE, BLUE = (0, 140, 255), (255, 80, 0)
key = []
for n, (i, kind) in enumerate(PICK, 1):
    stem, k, c = items[i]
    J = json.load(open(wd / (stem + ".step1.json")))
    sp = J["summary"]["sp"]
    img = cv2.imread(str(wd / (stem + ".raw.png")), 0)
    H, W = img.shape
    x0, y0, x1, y1 = c["box"]
    st = min(J["staves"], key=lambda s: abs((s["lines"][0] + s["lines"][-1]) / 2.0 - (y0 + y1) / 2.0))
    top, bot = min(st["lines"][0], y0), max(st["lines"][-1], y1)
    a, b, cc, d = int(max(0, x0 - 4 * sp)), int(max(0, top - 3 * sp)), int(min(W, x1 + 4 * sp)), int(min(H, bot + 3 * sp))
    crop = cv2.cvtColor(img[b:d, a:cc], cv2.COLOR_GRAY2BGR)
    sc = min(3.0, 1000.0 / (cc - a))
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
    def box(bx, col):
        cv2.rectangle(crop, (int((bx[0] - a) * sc), int((bx[1] - b) * sc)), (int((bx[2] - a) * sc), int((bx[3] - b) * sc)), col, 1)
    box([x0, y0 - 0.3 * sp, x1, y1 + 0.3 * sp], ORANGE)
    run = None
    if c["best"] >= 0.1 and c.get("run") is not None:
        run = next((r for r in J["runs"] if r["id"] == c["run"]), None)
        if run:
            box(run["box"], BLUE)
    cv2.imwrite(str(out / ("tile-%02d.png" % n)), crop)
    key.append(dict(tile=n, page=stem, kind=kind, reason=c["why_no_run"], best=c["best"], run=bool(run)))
json.dump(key, open(out / "key.json", "w"), indent=1)
print(json.dumps(key))
