"""whole-rest m0: tight crops of glyph boxes off the print, nothing drawn. usage: m0_boxcrop.py PLATE PKL OUTDIR SUB [SUB...]"""
import sys, pickle, pathlib
import numpy as np
from PIL import Image
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
plate, pkl, out = sys.argv[1:4]
out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
d = pickle.load(open(pkl, "rb"))
bx = {o["subject"]: o["detail"]["bbox_page_px"] for o in d["observations"] if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
sp = {o["subject"]: float(o["value"]) for o in d["observations"] if o["quantity"] == "staff_spacing"}
for s in sys.argv[4:]:
    p = s.split("/"); pg = int(p[1]); b = bx[s]; u = sp["staff/%s/%s/%s" % (p[1], p[2], p[3])]
    im = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    c = im.crop((int(cx - 5 * u), int(cy - 4 * u), int(cx + 5 * u), int(cy + 4 * u)))
    c = c.resize((c.width * 3, c.height * 3), Image.LANCZOS)
    f = out / (s.replace("/", "_") + ".png"); c.save(f); print(f)
