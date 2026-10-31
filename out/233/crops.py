"""2.233 crops: usage crops.py SPEC.json OUTDIR. SPEC = [{plate, page, boxes:[[x0,y0,x1,y1]...], name}]. Thin orange box on each head.
Crop = union of boxes padded 140 px each side (600 dpi page px)."""
import json, os, sys
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a26d61ddc53de8906")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES

spec = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
pages = {}
for it in spec:
    key = (it["plate"], it["page"])
    if key not in pages:
        pages[key] = Image.fromarray(render_page(str(LIB / PLATES[it["plate"]]["pdf"]), it["page"], dpi=600).rgb).convert("RGB")
    im = pages[key]
    bs = it["boxes"]
    x0 = min(b[0] for b in bs); y0 = min(b[1] for b in bs); x1 = max(b[2] for b in bs); y1 = max(b[3] for b in bs)
    pad = it.get("pad", 140)
    cx0, cy0, cx1, cy1 = int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad)
    crop = im.crop((cx0, cy0, cx1, cy1))
    d = ImageDraw.Draw(crop)
    for b in bs:
        d.rectangle([b[0] - cx0, b[1] - cy0, b[2] - cx0, b[3] - cy0], outline=(255, 140, 0), width=2)
    sc = 2 if crop.width < 500 else 1
    if sc != 1:
        crop = crop.resize((crop.width * sc, crop.height * sc), Image.LANCZOS)
    crop.save(os.path.join(out, it["name"] + ".png"))
    print(it["name"], crop.size)
