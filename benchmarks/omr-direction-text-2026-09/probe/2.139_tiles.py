"""2.139 blind tiles. python3 2.139_tiles.py OUTDIR KEYFILE
RED corners round the printed mark, nothing of ours drawn; our reading lives in KEYFILE only."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SP = 28.0
# (page, box in 600-dpi page px, what the print / our reading is)  -- the print is judged by Sean
ITEMS = [
 (24, [1734, 636, 1912, 676], "word", "marc.  (blue dyn. today: mm unspellable)"),
 (4, None, "word", "Cresc.  (blue dyn. today: m)"),
 (8, None, "word", "dim  (blue dyn. today: m)"),
 (26, None, "word", "dim.  (blue dyn. today: m)"),
 (25, None, "word", "poco a poco cresc.  (blue dyn. today: m)"),
 (6, [5230, 1279, 5335, 1333], "dynamic", "pp (read dynamic, control)"),
 (3, [1156, 634, 1245, 705], "dynamic", "ff (read dynamic, control)"),
 (6, [2815, 979, 2876, 1031], "dynamic", "p (read dynamic, control)"),
]
obs = {o["id"]: o for o in json.load(open("benchmarks/omr-direction-text-2026-09/out/2.139/brahms_obs.json"))}
rows = json.load(open("benchmarks/omr-direction-text-2026-09/out/2.139/brahms_unspellable.json"))
want = {4: "cell/4/1/10/3", 8: "cell/8/0/3/6", 26: "cell/26/0/11/1", 25: "cell/25/0/0/8"}
items = []
for page, box, kind, what in ITEMS:
    cell = None
    if box is None:
        cell = want[page]
        r = next(r for r in rows if r["cell"] == cell)
        w = r["ocr"][0][0]
        word = next(o for o in obs.values() if o["quantity"] == "direction_word" and o["value"] == w
                    and o["subject"].split("/")[1] == str(page))
        # the word whose box overlaps this cell's letters
        cand = [o for o in obs.values() if o["quantity"] == "direction_word" and o["value"] == w
                and o["subject"].split("/")[1] == str(page)]
        b = r["bbox"]
        def ov(o):
            x = o["detail"]["bbox_page_px"]
            return max(0, min(x[2], b[2]) - max(x[0], b[0])) * max(0, min(x[3], b[3]) - max(x[1], b[1]))
        word = max(cand, key=ov); box = [int(t) for t in word["detail"]["bbox_page_px"]]
    items.append((page, box, kind, what, cell))
items.sort(key=lambda it: hashlib.md5(json.dumps(it[:2]).encode()).hexdigest())
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
def bracket(a, x0, y0, x1, y1, c=(220, 0, 0), arm=22, th=6):
    h, w = a.shape[:2]
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm)); ya, yb = sorted((cy, cy + dy * arm))
        a[max(cy - th // 2, 0):cy + th // 2 + 1, max(xa, 0):min(xb, w)] = c
        a[max(ya, 0):min(yb, h), max(cx - th // 2, 0):cx + th // 2 + 1] = c
pages = {}; key = {"tiles": []}; man = {"dpi": 600, "document": "Brahms Symphony 1 (Breitkopf)",
  "question": "What is printed inside the red corners: a dynamic (which), or a word (which)?", "tiles": []}
for n, (page, box, kind, what, cell) in enumerate(items, 1):
    if page not in pages:
        pages[page] = np.asarray(Image.fromarray(render_page(PDF, page, dpi=600).rgb).convert("RGB"))
    img = pages[page].copy(); x0, y0, x1, y1 = box
    wx0, wx1 = int(x0 - 9 * SP), int(x1 + 9 * SP); wy0, wy1 = int(y0 - 5 * SP), int(y1 + 4 * SP)
    bracket(img, x0 - 8, y0 - 8, x1 + 8, y1 + 8)
    crop = Image.fromarray(img[max(wy0, 0):wy1, max(wx0, 0):wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    t = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(t).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font); t.paste(crop, (0, 130))
    t.save(OUT / f"tile_{n:02d}.png")
    man["tiles"].append({"n": n, "file": f"tile_{n:02d}.png", "page": page, "bracket_page_box_600dpi": box})
    key["tiles"].append({"n": n, "page": page, "box": box, "kind": kind, "ours": what, "cell": cell})
(OUT / "manifest.json").write_text(json.dumps(man, indent=1))
(OUT / "answers.template.json").write_text(json.dumps({str(i["n"]): {"what_it_is": None, "note": ""} for i in man["tiles"]}, indent=1))
Path(sys.argv[2]).write_text(json.dumps(key, indent=1))
print("wrote", len(items))
