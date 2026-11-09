"""2.279b: crop look at the refused chord groups. usage: crops.py RECORD GROUPS.json OUTDIR CLASS_PREFIX N SEED
Each crop: the page piece around the group, one thin orange box per head, caption = pitch, type, stem tail, direction.
Our look, not evidence."""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw                       # noqa: E402
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402
from tools.omr.staged import lane_report as LR          # noqa: E402
from tools.omr.staged.export import Record              # noqa: E402
from tools.omr.preprocessing import render_page         # noqa: E402

rec_path, gj, out, pref, n, seed = sys.argv[1:7]
groups = [g for g in json.load(open(gj)) if g["class"].startswith(pref)]
random.Random(int(seed)).shuffle(groups)
groups = groups[:int(n)]
rec = Record(load_record(rec_path))
boxes = LR.glyph_boxes(rec.obs_of(Q.GLYPH_BOX))
plate = "litolff" if "litolff" in rec_path else "brahms"
u = LR.PLATES[plate]["unit"]
Path(out).mkdir(parents=True, exist_ok=True)
cache = {}
tiles = []
for i, g in enumerate(groups, 1):
    pg = g["cell"][0]
    if pg not in cache:
        cache.clear()
        cache[pg] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[pg]
    bs = [boxes[h["glyph"]]["box"] for h in g["heads"] if h["glyph"] in boxes]
    x0 = min(b[0] for b in bs)
    y0 = min(b[1] for b in bs)
    x1 = max(b[2] for b in bs)
    y1 = max(b[3] for b in bs)
    cx = (x0 + x1) / 2
    X0, X1 = int(cx - 4 * u), int(cx + 4 * u)
    Y0, Y1 = int(y0 - 3 * u), int(y1 + 3 * u)
    c = im.crop((X0, Y0, X1, Y1)).copy()
    dr = ImageDraw.Draw(c)
    for h in g["heads"]:
        b = boxes[h["glyph"]]["box"]
        dr.rectangle([b[0] - 2 - X0, b[1] - 2 - Y0, b[2] + 2 - X0, b[3] + 2 - Y0], outline=(255, 120, 0), width=2)
    cap = " | ".join("%s %s s=%s %s" % (h["pitch"], h["type"], (h["stem"] or "-").split(":")[-1][-3:], h["dir"] or "-")
                     for h in g["heads"])
    s = 360.0 / c.width
    c = c.resize((360, int(c.height * s)))
    t = Image.new("RGB", (360, c.height + 28), (255, 255, 255))
    t.paste(c, (0, 28))
    ImageDraw.Draw(t).text((2, 2), "%d %s p%d s%d st%d c%d" % ((i, g["class"][:6]) + tuple(g["cell"])), fill=(0, 0, 0))
    ImageDraw.Draw(t).text((2, 14), cap[:70], fill=(0, 0, 0))
    tiles.append(t)
cols = 4
rows = (len(tiles) + cols - 1) // cols
h = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * 368 + 8, rows * (h + 8) + 8), (255, 255, 255))
for k, t in enumerate(tiles):
    sheet.paste(t, (8 + (k % cols) * 368, 8 + (k // cols) * (h + 8)))
sheet.save(Path(out) / ("sheet_%s.png" % pref))
print("saved", len(tiles))
