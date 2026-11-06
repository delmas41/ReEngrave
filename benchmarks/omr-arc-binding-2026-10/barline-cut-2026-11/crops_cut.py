"""Crops for the barline-cut test (measure only). One staff window with the cell edges' barlines visible; a THIN box for each detector arc box on the
staff (every class the detector called slur/tie), nothing else drawn.

    python3 crops_cut.py tiles OUTDIR     Sean's tiles 2,4,5,9,10,12  (tile-NN.png)
    python3 crops_cut.py common OUTDIR    8 crops of the commonest case: a real arc, right end cut at the barline, no partner box (4 Litolff, 4 Brahms)
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aac9f13c6fcc2a60b/benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11")
from PIL import ImageDraw      # noqa: E402

import crops as C              # noqa: E402

ORANGE = (255, 140, 0)


def cut(plate, page, staff, focus, sp, d, ledger_rows=None, pad_x=10.0, pad_y=7.0):
    im = C.page_image(plate, page)
    rows = [r for r in d["rows"] if r["staff"] == staff]
    x0, y0, x1, y1 = focus
    win = (max(0, int(x0 - pad_x * sp)), max(0, int(y0 - pad_y * sp)), min(im.width, int(x1 + pad_x * sp)), min(im.height, int(y1 + pad_y * sp)))
    c = im.crop(win).copy()
    dr = ImageDraw.Draw(c)
    t = max(2, int(sp * 0.10))
    for r in rows:
        b = r["box"]
        if b[2] < win[0] or b[0] > win[2] or b[3] < win[1] or b[1] > win[3]:
            continue
        for i in range(t):
            dr.rectangle((b[0] - win[0] - i, b[1] - win[1] - i, b[2] - win[0] + i, b[3] - win[1] + i), outline=ORANGE)
    if c.width > 1500:
        c = c.resize((1500, int(c.height * 1500 / c.width)))
    return c, win


def main():
    mode, out = sys.argv[1], pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    data = {p: json.load(open("results/%s.cut.json" % p)) for p in ("litolff", "brahms")}
    key = []
    if mode == "tiles":
        for t in json.load(open("results/tiles_spec.json")):
            d = data[t["plate"]]
            r = next(r for r in d["rows"] if r["key"] == t["sub"])
            focus = r["box"]
            c, win = cut(t["plate"], t["page"], t["staff"], focus, t["sp"], d, pad_x=11.0)
            n = "tile-%02d.png" % t["tile"]
            c.save(out / n)
            key.append(dict(file=n, **t, window=win))
    else:
        rng = random.Random(11)
        for plate in ("litolff", "brahms"):
            led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
            real = {p for r in led if r["fate"] != "not_an_arc" for p in r["pieces"]}
            cand = [r for r in data[plate]["rows"] if r["key"] in real and r["curve"] and r["cut_r"] and not r["partner_r"] and not r["cut_l"] and r["w_sp"] >= 3]
            for r in rng.sample(cand, 4):
                c, win = cut(plate, r["page"], r["staff"], r["box"], r["sp"], data[plate])
                n = "%02d.png" % (len(key) + 1)
                c.save(out / n)
                key.append(dict(file=n, plate=plate, page=r["page"], sub=r["key"], box=r["box"], sp=r["sp"], window=win))
    (out / "key.json").write_text(json.dumps(key, indent=1))
    print("wrote", len(key), "to", out)


main()
