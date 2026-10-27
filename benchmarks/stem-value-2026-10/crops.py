"""2.209 rule-7 crops: an orange box on a detector box, ~12 x 10 staff spaces around it. Usage: crops.py OUT_DIR plate:glyph ..."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
items = [a.split(":") for a in sys.argv[2:]]
cache = {}
for n, (plate, g) in enumerate(items, 1):
    base = LR.slice_dir(plate, "2.202strokes")
    page = int(g.split("/")[1])
    bb = None
    for l in open(base / "observations.jsonl"):
        if g in l and '"glyph_box"' in l:
            o = json.loads(l)
            if o["subject"] == g and o["quantity"] == "glyph_box":
                bb = o["detail"]["bbox_page_px"]; break
    assert bb, g
    k = (plate, page)
    if k not in cache:
        cache.clear(); cache[k] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    im = cache[k]; u = LR.PLATES[plate]["unit"]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    x0, y0, x1, y1 = max(0, int(cx - 6 * u)), max(0, int(cy - 5 * u)), int(cx + 6 * u), int(cy + 5 * u)
    c = im.crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([bb[0] - x0, bb[1] - y0, bb[2] - x0, bb[3] - y0], outline=(255, 140, 0), width=max(2, int(u / 8)))
    c = c.resize((520, int(520 * c.height / c.width)))
    c.save(out / ("%02d_%s_%s.png" % (n, plate, g.replace("/", "-"))))
    print(n, plate, g)
