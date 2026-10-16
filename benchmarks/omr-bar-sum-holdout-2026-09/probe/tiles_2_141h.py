"""ROADMAP 2.141h blind tiles: the bars whose standing value CHANGES under the three cause fixes (all ON vs W2-only),
plus controls whose value did not change.

    python3 tiles_2_141h.py SPEC.json TILES_DIR KEY_JSON

SPEC.json: [{"movement": "lit"|"brah", "cell": [p, s, st, c], "role": "...", "blue": [glyph subject, ...], "info": {...}}]
Same tile as 2.134/2.136/2.141 (600 dpi, 900 px, big tile number, RED corners = the bar, BLUE corners = each note whose value
changed (a control: each note W2 settles), NOTHING of ours drawn). The hidden key (what the base read, what the fixes read,
which fix) goes to KEY_JSON, NOT beside the tiles. Frame control as in 2.136. Shuffled (seed 21412).
"""
import gc
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
DOCS = {
    "brah": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
             LIB + "_shared-records/brahms1-breitkopf-mvt1-whole-20261014-night.record.json"),
    "lit": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
            LIB + "_shared-records/beethoven5-litolff-mvt1-whole-20261014-night.record.json"),
}
SPEC, OUT, KEY = json.load(open(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)


def bracket(arr, x0, y0, x1, y1, colour, arm=40, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


def frame_control(ink, box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


def geometry(label, cells):
    doc = load_record(DOCS[label][1])
    rec = doc["record"] if "record" in doc else doc
    geo, need = {}, set(cells)
    for o in rec["observations"]:
        p = o["subject"].split("/")
        if len(p) < 4:
            continue
        if o["quantity"] == "cell_box" and p[0] == "cell" and len(p) > 4:
            k = tuple(int(x) for x in p[1:5])
            if k in need:
                geo[(k, "box")] = o["value"]
        elif o["quantity"] == "staff_lines" and p[0] == "staff":
            geo[(tuple(int(x) for x in p[1:4]), "lines")] = o["value"]
        elif o["quantity"] == "glyph_box" and p[0] == "glyph" and len(p) > 5 and tuple(int(x) for x in p[1:5]) in need:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                geo[(o["subject"], "px")] = bp
    del rec, doc
    gc.collect()
    return geo


geos = {m: geometry(m, {tuple(s["cell"]) for s in SPEC if s["movement"] == m}) for m in ("lit", "brah")}
items = list(SPEC)
rnd = random.Random(int(__import__("os").environ.get("TILE_SEED", 21412)))
rnd.shuffle(items)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
public = {"dpi": 600, "question": (
    "In the bar inside the RED corners, the notes inside the BLUE corners: reading left to right, what is the "
    "value of each: an eighth (beamed or flagged), a sixteenth, a quarter, a dotted eighth, a dotted quarter, or "
    "something else? Say if you cannot tell. If the bar has a second voice, say what that voice has."), "tiles": []}
key = {"question_note": "hidden key; Sean's tiles carry no key", "tiles": []}
pages, n = {}, 0
for s in items:
    label, c = s["movement"], tuple(s["cell"])
    page = c[0]
    bx, ln = geos[label].get((c, "box")), geos[label].get((c[:3], "lines"))
    boxes = [geos[label].get((g, "px")) for g in s["blue"]]
    if bx is None or ln is None or not boxes or any(b is None for b in boxes):
        print("no geometry", label, c)
        continue
    if (label, page) not in pages:
        pages = {(label, page): np.asarray(Image.fromarray(render_page(DOCS[label][0], page, dpi=600).rgb).convert("RGB"))}
    img = pages[(label, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
    if not fc["passes"] or neg["passes"]:
        print("frame control REFUSED", label, c, fc, neg)
        continue
    n += 1
    sp = float(np.mean(np.diff(ln)))
    pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
    wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
    wy0 = int(min(ln[0] - 4.5 * sp, min(b[1] for b in boxes) - 30))
    wy1 = int(max(ln[-1] + 4.5 * sp, max(b[3] for b in boxes) + 30))
    bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp), int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
    for b in boxes:
        bracket(img, int(b[0]) - 8, int(b[1]) - 8, int(b[2]) + 8, int(b[3]) + 8, (0, 70, 230), arm=18, thick=5)
    crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 150 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 12), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 150))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    public["tiles"].append({"n": n, "file": name, "blue_notes": len(boxes)})
    key["tiles"].append({"n": n, "file": name, "movement": label, "cell": list(c), "role": s["role"], "info": s.get("info"),
                         "blue": s["blue"], "blue_boxes_px": [[round(v, 1) for v in b] for b in boxes],
                         "frame_control": fc, "frame_control_negative": neg, "page_box_600dpi": [wx0, wy0, wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(public, indent=1))
KEY.parent.mkdir(parents=True, exist_ok=True)
KEY.write_text(json.dumps(key, indent=1, default=str))
print("wrote", n, "tiles ->", OUT, "key", KEY)
