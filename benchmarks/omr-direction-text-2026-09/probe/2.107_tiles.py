"""2.107 blind print tiles for Sean: the dynamics the second look newly READS,
the look-alikes it refused, and controls.

    python3 .../2.107_tiles.py OUTDIR  DOC:TAG [...]   (TAG.reach.json and
        TAG.glyphs.json in $LETTER_LOOK_SCRATCH, written by the 2.107 reach tool)

Each tile: one mark, phone-sized (900 px wide), a big tile number, a RED corner
bracket round the SUBJECT, the staff the page's own. ONE question for all of
them, asked in `manifest.json` -- *what is the bracketed mark?* -- and our
reading (what the look read, which head/rest boxes it removed, the strings the
library refused, the best note/rest it competed with) lives in `manifest.json`
ONLY, never on the image. Three kinds, mixed by a fixed hash so the order says
nothing:

  read     the bracket is the letters the look read (a library dynamic)
  refused  the bracket is a group the look looked at hardest and refused to read
           (the best letter it saw, rejected) -- the near-miss gallery
  control  the bracket is a real head or rest that stands near a dynamic the
           detector boxed, a group the look saw and read as NOTHING

The same frame control as 2.89/2.90 (asserted per tile, with its negative);
tiles Sean has already judged (Litolff p2 `sf`, 2.90 tile 9) are not re-asked.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

SCRATCH = Path(os.environ.get("LETTER_LOOK_SCRATCH", "."))
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "dvorak": LIB + "dvorak/symphony-8-op88/dvorak--symphony-8-op88--novello-1892--imslp405841.pdf",
    "schumann": LIB + "schumann/symphony-2-op61/schumann--symphony-2-op61--peters-1887--imslp514290.pdf",
    "tchaikovsky": LIB + "tchaikovsky/symphony-4-op36/tchaikovsky--symphony-4-op36--jurgenson--imslp377460.pdf",
}
# Sean already judged these (document, page, x0, y0, x1, y1 of the tile subject)
ANSWERED = [("litolff", 2, 1376, 2151, 1417, 2200)]
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
DPI = 600
PER_KIND = {"read": 6, "refused": 2, "control": 2}


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def bracket(arr, x0, y0, x1, y1, colour, arm=22, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


def frame_control(ink, x0, x1, lines, shift=0.0):
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()


def staff_for(geo, page, box):
    """The staff (its five lines) whose band holds the box's centre, widest
    margin of 8 spaces."""
    cy = (box[1] + box[3]) / 2
    best = None
    for sysn, sd in geo.get(str(page), {}).items():
        for st in sd["staves"]:
            ys = st[2]
            sp = (ys[-1] - ys[0]) / 4.0
            d = 0 if ys[0] <= cy <= ys[-1] else min(abs(cy - ys[0]), abs(cy - ys[-1]))
            if d <= 8 * sp and (best is None or d < best[0]):
                best = (d, int(sysn), st[0], ys)
    return best


def pick(items, k, salt):
    return sorted(items, key=lambda it: hashlib.md5((salt + json.dumps(it["box_page"])
                                                       + str(it["page"])).encode()).hexdigest())[:k]


candidates = {"read": [], "refused": [], "control": []}
for spec in sys.argv[2:]:
    doc, tag = spec.split(":")
    reach = json.load(open(SCRATCH / f"{tag}.reach.json"))
    glyphs = json.load(open(SCRATCH / f"{tag}.glyphs.json"))
    dyn = {}
    for r in glyphs["rows"]:
        if r["box"] and str(r["cls"]).startswith("dynamic"):
            dyn.setdefault(r["page"], []).append(r["box"])
    boxes = {r["key"]: r for r in glyphs["rows"]}
    for x in reach:
        x = dict(x, doc=doc, geo=glyphs["geo"])
        b = x["box_page"]
        if any(a[0] == doc and a[1] == x["page"] and overlaps(b, a[2:]) for a in ANSWERED):
            continue
        if x["status"] in ("read", "narrowed"):
            candidates["read"].append(x)
        elif x["status"] == "rejected" and x["reason"] == "no_letter_read":
            best = x["near"][0][1] if x["near"] else 0.0
            if best >= 0.3:
                candidates["refused"].append(dict(x, _best=best))
            near_dyn = any(overlaps([b[0] - 6 * 16, b[1] - 6 * 16, b[2] + 6 * 16, b[3] + 6 * 16], d)
                           for d in dyn.get(x["page"], []))
            if near_dyn and x["rival"] and x["rival"][1] >= 0.8 and x["seeds"]:
                seed = boxes.get(x["seeds"][0][0])
                if seed and seed["box"]:
                    candidates["control"].append(dict(x, subject_box=seed["box"]))

chosen = []
for kind, k in PER_KIND.items():
    pool = candidates[kind]
    if kind == "refused":
        pool = sorted(pool, key=lambda v: -v["_best"])[:k]
    else:
        pool = pick(pool, k, kind)
    chosen += [dict(v, kind=kind) for v in pool]
chosen.sort(key=lambda v: hashlib.md5((v["doc"] + json.dumps(v["box_page"]) + str(v["page"])).encode()).hexdigest())

pages = {}
manifest = {"dpi": DPI, "question": "What is the bracketed mark? (a dynamic -- which letters? -- "
                                    "a note, a rest, or something else)",
            "tiles": []}
n = 0
for v in chosen:
    doc, page = v["doc"], v["page"]
    sub = v.get("subject_box") or v["box_page"]
    x0, y0, x1, y1 = [int(t) for t in sub]
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(
            Image.fromarray(render_page(PDFS[doc], page, dpi=DPI).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    st = staff_for(v["geo"], page, (x0, y0, x1, y1))
    if st is None:
        print("skipped (no staff near):", doc, page, sub)
        continue
    _d, system, staff, ln = st
    sp = float(np.mean(np.diff(ln)))
    fx0, fx1 = int(x0 - 8 * sp), int(x1 + 8 * sp)
    cal = max((t / 20.0 for t in range(-8, 9)), key=lambda t: frame_control(ink, fx0, fx1, ln, t)["ratio"])
    fc, neg = frame_control(ink, fx0, fx1, ln, cal), frame_control(ink, fx0, fx1, ln, cal + 0.5)
    if not fc["passes"] or neg["passes"]:
        print("skipped (frame control):", doc, page, sub, fc, neg)
        continue
    n += 1
    wx0, wx1 = int(x0 - 9 * sp), int(x1 + 9 * sp)
    wy0, wy1 = int(min(ln[0] - 4.5 * sp, y0 - sp)), int(max(ln[-1] + 4.5 * sp, y1 + sp))
    bracket(img, x0 - 8, y0 - 8, x1 + 8, y1 + 8, (220, 0, 0))
    crop = Image.fromarray(img[max(wy0, 0):wy1, max(wx0, 0):wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    manifest["tiles"].append({
        "n": n, "file": name, "kind": v["kind"], "document": doc, "page": page,
        "system": system, "staff": staff, "bracket_page_box_600dpi": [x0, y0, x1, y1],
        "our_reading": {"status": v["status"], "text": v["text"], "candidates": v["cands"],
                        "regions": v["regions"], "best_letters": v["near"],
                        "best_note_or_rest": v["rival"], "library_tried": v["tried"],
                        "unstable_across_erasures": v.get("unstable")},
        "head_and_rest_boxes_under_it": v["seeds"], "cover": v["cover"],
        "frame_control": fc, "frame_control_negative": neg,
        "calibration_shift_spaces": cal, "page_box_600dpi": [max(wx0, 0), max(wy0, 0), wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
(OUT / "answers.template.json").write_text(json.dumps(
    {str(t["n"]): {"what_it_is": None, "note": ""} for t in manifest["tiles"]}, indent=1))
print("wrote", n, "tiles to", OUT)
