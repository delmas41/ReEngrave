"""2.294 step 1 blind tiles (12). Seeded rule (seed 2294, random.Random): from the TEST-scope sites of sites.py, alternating Brahms / Litolff:
  5 of class b (refused): 3 drawn from all b sites, 2 drawn from b sites whose refused box is a rest, dynamic or accidental family;
  4 of class d (unclaimed ink at the contact), 1 of class c (weak), 2 of class a (nothing lost, the controls).
One window about 2 x 1 staff-heights around the site (the page's own render, binarised: the canvas ink), one thin orange box on the SITE, nothing else drawn, no caption.
Question for Sean (README): "Which marks meet inside the box? Name each one (a slur and a stem, ...) -- is each of them a whole, real mark?"
Key one level above the tiles. usage: tiles_step1.py SCRATCH OUTDIR"""
import json, sys, random, pathlib
import numpy as np, cv2

d = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
(out / "tiles").mkdir(parents=True, exist_ok=True)
rng = random.Random(2294)
sites = [s for s in json.load(open(d / "sites.json")) if s["scope"] == "test"]
for s in sites:
    s["fam"] = {r.split(":")[-1] for r in s["refused"]}
cls = lambda c, f=lambda s: True: [s for s in sites if s["class"] == c and f(s)]
chosen, used = [], set()


def take(pool, n):
    pool = list(pool)
    rng.shuffle(pool)
    got = []
    # alternate plates
    for plate in ["brahms", "litolff"] * n:
        if len(got) >= n:
            break
        for s in pool:
            if s["plate"] == plate and id(s) not in used:
                used.add(id(s)); got.append(s); break
    return got


chosen += take(cls("b"), 3)
chosen += take(cls("b", lambda s: bool(s["fam"] & {"rest", "dynamic", "accidental"})), 2)
chosen += take(cls("d"), 4)
chosen += take(cls("c"), 1)
chosen += take(cls("a"), 2)
rng.shuffle(chosen)
key = []
cache = {}
for i, s in enumerate(chosen, 1):
    k = (s["plate"], s["page"])
    if k not in cache:
        cache.clear()
        z = np.load(d / "off" / ("%s.p%d.npz" % k))
        cache[k] = (z["ink"], float(z["sp"]) or 30.0)
    ink, sp = cache[k]
    x0, y0, x1, y1 = s["bbox"]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    hw, hh = max(9 * sp, (x1 - x0) / 2 + 3 * sp), max(5.5 * sp, (y1 - y0) / 2 + 3 * sp)
    X0, X1, Y0, Y1 = int(max(0, cx - hw)), int(min(ink.shape[1], cx + hw)), int(max(0, cy - hh)), int(min(ink.shape[0], cy + hh))
    im = np.where(ink[Y0:Y1, X0:X1], 0, 255).astype(np.uint8)
    f = 720.0 / im.shape[1]
    im = cv2.cvtColor(cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA), cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im, (int((x0 - X0 - 2) * f), int((y0 - Y0 - 2) * f)), (int((x1 - X0 + 2) * f), int((y1 - Y0 + 2) * f)), (0, 140, 255), 1)
    cv2.imwrite(str(out / "tiles" / ("tile-%02d.png" % i)), im)
    key.append(dict(tile=i, plate=s["plate"], page=s["page"], pair=s["pair"], cls=s["class"], refused=s["refused"], weak_px=s["weak_px"], none_px=s["none_px"],
                    bbox_page_px=s["bbox"], contact_px=s["contact_px"]))
(out / "key.json").write_text(json.dumps(key, indent=1, default=str))
(out / "tiles" / "README.txt").write_text(
    "12 tiles, one window each. A thin orange box marks a place where ink of two marks meets. Question for every tile:\n"
    "Which marks meet inside the box? Name each one (for example a slur and a stem) -- is each of them a whole, real mark?\n")
# sheet: 3 columns, LARGE numbers drawn in a white strip above each tile (no inset on the tile)
ims = []
for i in range(1, len(chosen) + 1):
    t = cv2.imread(str(out / "tiles" / ("tile-%02d.png" % i)))
    strip = np.full((90, t.shape[1], 3), 255, np.uint8)
    cv2.putText(strip, str(i), (10, 78), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 6)
    ims.append(cv2.copyMakeBorder(np.vstack([strip, t]), 0, 14, 7, 7, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
H = max(m.shape[0] for m in ims); W = max(m.shape[1] for m in ims)
ims = [cv2.copyMakeBorder(m, 0, H - m.shape[0], 0, W - m.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for m in ims]
rows = [np.hstack(ims[r:r + 3]) for r in range(0, len(ims), 3)]
cv2.imwrite(str(out / "sheet.png"), np.vstack(rows))
print(len(chosen), "tiles;", [(k["tile"], k["plate"][:2], k["page"], k["cls"], "-".join(k["pair"])) for k in key])
