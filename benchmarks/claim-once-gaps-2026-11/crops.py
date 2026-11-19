"""2.322 crops from gaps_page.py npz: ink black, no-owner ink red, beam-role stroke ink blue, a thin box on request.
    python3 crops.py PLATE DATADIR OUTDIR nonebeam N SEED | heads FILE_SUBJECTS...   (see main)"""
import json, random, sys, pathlib
import numpy as np, cv2
plate, data, out, mode = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4]
out.mkdir(parents=True, exist_ok=True)
cache = {}
def page(pg):
    if pg not in cache: cache[pg] = np.load(data / ("%s_p%d.npz" % (plate, pg)))
    return cache[pg]
def crop(pg, box, name, pad=40, scale=3, mark=None):
    z = page(pg); ink, none, rm = z["ink"], z["none"], z["rolemap"]
    x0, y0, x1, y1 = box
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(ink.shape[1], x1 + pad), min(ink.shape[0], y1 + pad)
    im = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
    sub = ink[Y0:Y1, X0:X1]
    im[sub] = (60, 60, 60)
    im[np.isin(rm[Y0:Y1, X0:X1], [1, 2, 3]) & sub] = (200, 120, 0)     # BGR: blue-ish for beam-role
    im[none[Y0:Y1, X0:X1]] = (0, 0, 230)                                # red: no owner
    im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    bx = [(x0 - X0) * scale, (y0 - Y0) * scale, (x1 - X0) * scale, (y1 - Y0) * scale]
    cv2.rectangle(im, (bx[0], bx[1]), (bx[2], bx[3]), (0, 160, 0), 1)
    cv2.imwrite(str(out / name), im)
if mode == "nonebeam":
    comps = json.load(open(data / ("%s_nonebeam_components.json" % plate)))
    n, seed = int(sys.argv[5]), int(sys.argv[6])
    big = [c for c in comps if c["px"] >= 150]
    random.Random(seed).shuffle(big)
    keep = big[:n]
    for i, c in enumerate(keep, 1):
        crop(c["page"], c["box"], "none_%02d_p%d_%s.png" % (i, c["page"], c["class"]), pad=30)
    json.dump(keep, open(out / "none_crops.json", "w"), indent=1)
    print(len(big), "components >=150px;", "saved", len(keep))
elif mode == "beamnone":
    heads = json.load(open(data / ("%s_heads2.json" % plate)))
    comps = []
    for pg in sorted({x["page"] for x in heads}):
        z = page(pg)
        m = z["none"] & np.isin(z["rolemap"], [1, 2, 3])
        hb = np.zeros_like(m)
        for x in heads:
            if x["page"] == pg:
                a, b, c, d = x["box"]
                hb[b:d, a:c] = True
        m &= ~hb
        nlab, lab, stats, _c = cv2.connectedComponentsWithStats(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
        for j in range(1, nlab):
            x, y, w_, h_, a_ = stats[j]
            px = int((m & (lab == j)).sum())
            if px >= 60:
                comps.append({"page": pg, "box": [int(x), int(y), int(x + w_), int(y + h_)], "px": px})
    random.Random(int(sys.argv[6])).shuffle(comps)
    print(len(comps), "beam-role no-owner components >=60 px outside head boxes, total px", sum(c["px"] for c in comps))
    for i, c in enumerate(comps[:int(sys.argv[5])], 1):
        crop(c["page"], c["box"], "beamnone_%02d_p%d.png" % (i, c["page"]), pad=40)
elif mode == "subj":
    h = {x["subject"]: x for x in json.load(open(data / ("%s_heads2.json" % plate)))}
    for i, s in enumerate(sys.argv[5].split(","), 1):
        x = h[s]
        crop(x["page"], x["box"], "subj_%02d_p%d_%s.png" % (i, x["page"], s.replace("/", "-")), pad=45)
    print("saved", len(sys.argv[5].split(",")))
else:
    h = json.load(open(data / ("%s_heads2.json" % plate)))
    sel = [x for x in h if x["written"] and x["beam_role_share"] >= 0.5]
    random.Random(int(sys.argv[6])).shuffle(sel)
    for i, x in enumerate(sel[:int(sys.argv[5])], 1):
        crop(x["page"], x["box"], "headbeam_%02d_p%d.png" % (i, x["page"]), pad=45)
    print("saved", min(len(sel), int(sys.argv[5])))
