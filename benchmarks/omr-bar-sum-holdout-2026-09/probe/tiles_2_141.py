"""ROADMAP 2.141 blind tiles: Litolff W2 bars that share a cause with Sean's wrong tiles 6 / 10.

    python3 tiles_2_141.py CAUSES.json GEOM.json TILES_DIR KEY_JSON

Same tile as 2.134/2.136 (600 dpi, 900 px, big tile number, RED corners = the bar, BLUE corners = each note the
fix settled, nothing of ours drawn). Bars: every unseen Litolff W2 bar with the T6 test (a head with a stem each
way whose beam levels were counted one-sided or per voice with differing counts), then the unseen U bars (a
displaced whole rest nobody sized). Frame control as in 2.136. Key (what the fix settled, which test fired) goes to
KEY_JSON, NOT beside the tiles. Shuffled (seed 2141).
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
CAUSES, GEOM, OUT, KEY = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
SEEN = {(5, 0, 0, 6), (7, 1, 9, 3), (3, 1, 0, 8)}


def t6(e):
    if e["is_rest"] or e["outcome"] not in ("decided", "narrowed"):
        return False
    # the CV head_stem verdict itself says a stem each way (NOT the reach ruler alone: Brahms 1 and 7 trip that one)
    if e["head_stem_reason"] not in ("unison_two_voices", "two_stems"):
        return False
    bv = e["beam_voices"]
    return e["beam_side"] is not None if bv is None else bv["up"] != bv["down"]


def old_t(e):
    """the first draft of the test (reach 'both' / any stem each way): kept only to pick CONTROL bars"""
    return (not e["is_rest"] and e["outcome"] in ("decided", "narrowed")
            and (e["reach"] == "both" or e["head_stem_reason"] == "unison_two_voices" or e["beam_voices"]))


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


rows = json.load(open(CAUSES))
geo = json.load(open(GEOM))
items = []
for r in rows:
    c = tuple(r["cell"])
    if c in SEEN:
        continue
    live = [e for e in r["elems"] if e["left_the_bar"] is None]
    which = "T6" if any(t6(e) for e in live) else ("U" if r["U"] else ("control_not_flagged" if any(old_t(e) for e in live) else None))
    if which:
        items.append((which, c, r))
rnd = random.Random(2141)
rnd.shuffle(items)
items = [i for i in items if i[0] == "T6"] + [i for i in items if i[0] == "U"][:2] \
    + [i for i in items if i[0] == "control_not_flagged"][:3]
rnd.shuffle(items)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
public = {"dpi": 600, "question": (
    "In the bar inside the RED corners, the notes inside the BLUE corners: reading left to right, what is the "
    "value of each: an eighth (beamed or flagged), a sixteenth, a quarter, a dotted eighth, a dotted quarter, or "
    "something else? Say if you cannot tell. If the bar has a second voice, say what that voice has."), "tiles": []}
key = {"question_note": "hidden key; Sean's tiles carry no key", "tiles": []}
pages = {}
n = 0
for which, c, r in items:
    page = c[0]
    bx, ln = geo["box"]["%d,%d,%d,%d" % c], geo["lines"]["%d,%d,%d" % c[:3]]
    if page not in pages:
        pages = {page: np.asarray(Image.fromarray(render_page(PDF, page, dpi=600).rgb).convert("RGB"))}
    img = pages[page].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
    if not fc["passes"] or neg["passes"]:
        print("frame control REFUSED", c, fc, neg)
        continue
    settled = r["w2_as_written"]["settled"]
    boxes = []
    for g in settled:
        b = geo["glyph"].get("glyph/%d/%d/%d/%d/%s" % (*c, g))
        if b:
            boxes.append(b[0])
    if not boxes:
        continue
    n += 1
    sp = float(np.mean(np.diff(ln)))
    pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
    wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
    wy0, wy1 = int(min(ln[0] - 4.5 * sp, min(b[1] for b in boxes) - 30)), int(ln[-1] + 4.5 * sp)
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
    key["tiles"].append({"n": n, "file": name, "cell": list(c), "test": which, "settled_beats_beamlevels": settled,
                         "T6_glyphs": [e["glyph"] for e in r["elems"] if e["left_the_bar"] is None and t6(e)],
                         "U_glyphs": r["U"], "frame_control": fc, "frame_control_negative": neg,
                         "page_box_600dpi": [wx0, wy0, wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(public, indent=1))
KEY.parent.mkdir(parents=True, exist_ok=True)
KEY.write_text(json.dumps(key, indent=1, default=str))
print("wrote", n, "tiles ->", OUT)
