"""Crops (for MY look, not tiles): the head box (blue), the page stem the page reader named (green), the OFF cell join's stem (red).
Usage: look_heads.py REC.json PDF OUTDIR glyph ..."""
import sys, os, json
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw

rec = load_record(sys.argv[1])
pdf, out, keys = sys.argv[2], sys.argv[3], sys.argv[4:]
os.makedirs(out, exist_ok=True)
Q = M.rows_by_quantity(rec)
geo = M.cell_geometry(Q)
gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in Q["glyph_box"] if (o.get("detail") or {}).get("bbox_page_px")}
ps = {o["subject"]: o for o in Q["page_stem"]}
stem_val = {o["id"]: (o["subject"], o["value"]) for o in Q["stem"]}
pages = {}
for k in keys:
    p = int(k.split("/")[1])
    if p not in pages:
        pages[p] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[p].copy()
    dr = ImageDraw.Draw(im)
    hb = gbox.get(k)
    boxes = [("blue", hb)]
    r = ps.get(k)
    if r:
        boxes.append(("green", (r.get("detail") or {}).get("stem_box")))
    for col, b in boxes:
        if b:
            dr.rectangle([b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], outline={"blue": (0, 0, 255), "green": (0, 170, 0)}[col], width=2)
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    im.crop((int(cx - 160), int(cy - 200), int(cx + 160), int(cy + 200))).save(os.path.join(out, k.replace("/", "_") + ".png"))
    print(k, "page stem", r and (r.get("detail") or {}).get("direction"), r and (r.get("detail") or {}).get("candidates"))
