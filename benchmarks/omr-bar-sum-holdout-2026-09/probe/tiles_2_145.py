"""2.145 blind print tiles for Sean: heads the gate takes for a rest, plus controls that can fail.

    python3 .../tiles_2_145.py OUTDIR KEYFILE

Inputs (all small slices, no whole-record load; see cache_2_145.py / geom_slice_2_145.py / replay_2_145.py):
  out/2.145/{lit,brah}-hits.json   candidates + controls (count_2_145.py)
  out/2.145/{lit,brah}-replay.json arms (replay_2_145.py): the ON arm names which heads were refused
  out/2.145/{lit,brah}-geom.json   cell boxes + staff lines

Roles (NEVER printed on the image; KEYFILE and manifest.json only):
  reinstated   -- the ON arm refused the head `is_a_rest_shape` and wrote a rest
  declined     -- the 2.99 windows read the ink as a rest but the gate declined (a stem or a second head)
  stem_control -- a STEMMED head whose ink reads rest-shaped by shape alone (must stay a note)
  head_control -- a STEMLESS head whose ink is not rest-shaped (must stay a note)
Each tile: one bar, 900 px wide, a tile number, RED corners on the bar, BLUE corners on the head's ink. Nothing of ours
(no reading, no class, no score) is drawn; readings are in manifest.json only.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
OUT, KEY = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
DOCS = {"litolff": "lit", "brahms": "brah"}


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


rng = random.Random(145)
chosen = []
for doc, tag in DOCS.items():
    hits = json.load(open(f"out/2.145/{tag}-hits.json"))
    rep = json.load(open(f"out/2.145/{tag}-replay.json"))
    on = rep["on"]
    for h in hits["hits"]:
        refused = bool(on.get(h["head"], {}).get("nn") and on[h["head"]]["nn"][1] is True)
        chosen.append((doc, "reinstated" if refused else "declined", h))
    ctrl = hits["controls"]
    stemmed = sorted(ctrl["stemmed_reads_rest"], key=lambda r: r["head"])
    stemless = sorted(ctrl["stemless_not_rest_shaped"], key=lambda r: r["head"])
    k_stem, k_head = (2, 1) if doc == "litolff" else (1, 1)
    for r in rng.sample(stemmed, min(k_stem, len(stemmed))):
        chosen.append((doc, "stem_control", r))
    for r in rng.sample(stemless, min(k_head, len(stemless))):
        chosen.append((doc, "head_control", r))
rng.shuffle(chosen)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()

pages, geoms = {}, {d: json.load(open(f"out/2.145/{t}-geom.json")) for d, t in DOCS.items()}
manifest = {"dpi": 600, "question": "What is the mark inside the BLUE corners (a note -- which value -- or a rest -- which "
                                    "kind -- or something else)? The RED corners are only the bar it is in.",
            "tiles": []}
key = []
n = 0
for doc, role, h in chosen:
    g = h["head"].split("/")
    page, system, staff, cell = (int(x) for x in g[1:5])
    box = h["page_bbox"]
    gk = geoms[doc]
    cb = gk["cell_box"].get(f"{page}/{system}/{staff}/{cell}")
    ln = gk["staff_lines"].get(f"{page}/{system}/{staff}")
    if cb is None or ln is None or not box:
        print("skip (no geometry):", h["head"])
        continue
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(Image.fromarray(render_page(PDFS[doc], page, dpi=600).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    sp = float(np.mean(np.diff(ln)))
    cal = max((k / 20.0 for k in range(-8, 9)), key=lambda t: frame_control(ink, cb, ln, t)["ratio"])
    fc, neg = frame_control(ink, cb, ln, cal), frame_control(ink, cb, ln, cal + 0.5)
    if not fc["passes"] or neg["passes"]:
        print("skipped (frame control):", h["head"], fc, neg)
        continue
    n += 1
    pad = int(max(2.5 * sp, (14 * sp - (cb[2] - cb[0])) / 2))
    wx0, wx1 = int(cb[0]) - pad, int(cb[2]) + pad
    wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
    bracket(img, int(cb[0]) + 6, int(ln[0] - 1.3 * sp), int(cb[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
    bracket(img, int(box[0]) - 6, int(box[1]) - 6, int(box[2]) + 6, int(box[3]) + 6, (0, 70, 230), arm=18, thick=5)
    crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    manifest["tiles"].append({"n": n, "file": name, "document": doc, "glyph": h["head"],
                              "our_reading": {"class": h.get("class"), "strict": h.get("strict"),
                                              "step_free": h.get("free"), "step": h.get("step"),
                                              "width_spaces": h.get("w"), "height_spaces": h.get("h")},
                              "frame_control": fc, "frame_control_negative": neg, "calibration_shift_spaces": cal,
                              "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    key.append({"n": n, "role": role, "document": doc, "glyph": h["head"]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
KEY.parent.mkdir(parents=True, exist_ok=True)
KEY.write_text(json.dumps(key, indent=1))
print("wrote", n, "tiles to", OUT, "key", KEY)
