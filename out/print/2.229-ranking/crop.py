"""2.229: crop bars off the print at 600 dpi (the gather's own DPI), readable: a window of +-8 staff spaces vertically around the bar's
cell_box centre, the bar's width +-2 spaces (at least 24 spaces wide), resized to 1000 px wide. The cell_box is outlined in thin orange.
usage: crop.py PLATE SLICEDIR OUTDIR KIND  page/system/staff/cell [...]   (a bar)  or  page:x0,y0,x1,y1 (a page box)"""
import json, sys, pathlib
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
plate, sl, out, kind = sys.argv[1:5]
keys = sys.argv[5:]
out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
want = {("cell/" + k): k for k in keys if ":" not in k}
boxes = {}
if want:
    for l in open(pathlib.Path(sl) / plate / "observations.jsonl"):
        if '"cell_box"' in l:
            o = json.loads(l)
            if o["quantity"] == "cell_box" and o["subject"] in want:
                boxes[want[o["subject"]]] = o["value"]
u = L.PLATES[plate]["unit"]
cache = {}
W = 1000
for k in keys:
    if ":" in k:
        pg, bx = k.split(":"); pg = int(pg); b = [float(x) for x in bx.split(",")]; name = "p%d_%s" % (pg, "_".join(str(int(x)) for x in b))
    else:
        pg = int(k.split("/")[0]); b = boxes.get(k); name = "p" + k.replace("/", "_")
        if b is None: print("no cell_box", k); continue
    if pg not in cache:
        cache.clear(); cache[pg] = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[pg]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    half = max((b[2] - b[0]) / 2 + 2 * u, 12 * u)
    x0, x1 = max(0, int(cx - half)), min(im.width, int(cx + half))
    y0, y1 = max(0, int(cy - 8 * u)), min(im.height, int(cy + 8 * u))
    c = im.crop((x0, y0, x1, y1)).copy()
    d = ImageDraw.Draw(c)
    if ":" not in k:
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
    c = c.resize((W, max(1, int(W * c.height / c.width))), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    d.text((6, 4), "%s %s" % (plate, k), fill=(0, 0, 255))
    p = out / ("%s_%s.png" % (kind, name)); c.save(p); print(p)
