"""2.137 blind print tiles for Sean: is the box a notehead, a tremolo slash, or something else?

    python3 benchmarks/omr-head-fill-2026-09/probe/2.137_tiles.py OUTDIR  brahms=REC.json litolff=REC.json  SPEC.json

`SPEC.json` is an ordered list of `{"doc", "subject", "kind"}`; `kind` (fixed | control | other) lives in
`manifest.json` ONLY. Each tile is the printed page at 600 dpi, phone-sized (1000 px wide), a big tile number,
RED corner brackets on the BAR (the cell's own rectangle), BLUE corner brackets on the box in question, and
nothing else drawn: our reading is never on the image. Same frame control as 2.90_tiles.py (asserted per tile,
with its negative).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
DPI, WIDTH = 600, 1000
RED, BLUE = (220, 0, 0), (20, 90, 235)
spec = json.load(open(sys.argv[-1]))
recs = {}
for a in sys.argv[2:-1]:
    doc, path = a.split("=", 1)
    result = load_record(path)
    rec = result["record"] if "record" in result else result
    keep = {s["subject"] for s in spec if s["doc"] == doc}
    cells = {"cell/" + "/".join(k.split("/")[1:5]) for k in keep}
    staves = {"staff/" + "/".join(k.split("/")[1:4]) for k in keep}
    got = {}
    for o in rec["observations"]:
        s = o["subject"]
        if o["quantity"] == "glyph_box" and s in keep:
            got[("box", s)] = o["detail"]["bbox_page_px"]
        elif o["quantity"] == "cell_box" and s in cells:
            got[("cell", s)] = o["value"]
        elif o["quantity"] == "staff_lines" and s in staves:
            got[("lines", s)] = o["value"]
    recs[doc] = got
    del result, rec


def bracket(d, x0, y0, x1, y1, colour, arm, width):
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + dx * arm, cy)], fill=colour, width=width)
        d.line([(cx, cy), (cx, cy + dy * arm)], fill=colour, width=width)


def frame_control(ink, x0, x1, lines, shift=0.0):
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
pages, manifest, n = {}, {"dpi": DPI, "question": "What is inside the BLUE corners: a notehead, a tremolo "
                          "slash, or something else (and what)? The RED corners are the bar.", "tiles": []}, 0
for s in spec:
    doc, g = s["doc"], s["subject"]
    got = recs[doc]
    parts = g.split("/")
    page = int(parts[1])
    cell, staff = "cell/" + "/".join(parts[1:5]), "staff/" + "/".join(parts[1:4])
    bx0, by0, bx1, by1 = got[("box", g)]
    cb, lines = got[("cell", cell)], got[("lines", staff)]
    cx0, cx1 = int(cb[0]), int(cb[2])
    sp = float(np.mean(np.diff(lines)))
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(Image.fromarray(render_page(PDFS[doc], page, dpi=DPI).rgb).convert("RGB"))
    img = pages[(doc, page)]
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    cal = max((t / 20.0 for t in range(-8, 9)), key=lambda t: frame_control(ink, cx0 + 20, cx1 - 20, lines, t)["ratio"])
    fc = frame_control(ink, cx0 + 20, cx1 - 20, lines, cal)
    neg = frame_control(ink, cx0 + 20, cx1 - 20, lines, cal + 0.5)
    ok = fc["passes"] and not neg["passes"]
    pad = int(1.2 * sp)
    wx0, wx1 = max(cx0 - pad, 0), min(cx1 + pad, img.shape[1])
    wy0 = int(min(lines[0] - 5.5 * sp, by0 - sp))
    wy1 = int(max(lines[-1] + 5.5 * sp, by1 + sp))
    crop = Image.fromarray(img[max(wy0, 0):wy1, wx0:wx1].copy())
    scale = min(4.0, WIDTH / crop.width)
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(crop)
    bracket(d, (cx0 - wx0) * scale - 4, (lines[0] - 1.5 * sp - max(wy0, 0)) * scale,
            (cx1 - wx0) * scale + 4, (lines[-1] + 1.5 * sp - max(wy0, 0)) * scale, RED, int(40), 7)
    m = 6
    bracket(d, (bx0 - wx0 - m) * scale, (by0 - max(wy0, 0) - m) * scale,
            (bx1 - wx0 + m) * scale, (by1 - max(wy0, 0) + m) * scale, BLUE, int(22), 6)
    n += 1
    tile = Image.new("RGB", (crop.width, 150 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 12), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 150))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    manifest["tiles"].append({"n": n, "file": name, "doc": doc, "subject": g, "kind": s["kind"],
                              "page": page, "box_page_px": [bx0, by0, bx1, by1],
                              "frame_control": fc, "frame_control_negative": neg, "frame_ok": ok,
                              "scale": round(scale, 2)})
    if not ok:
        print("FRAME CONTROL FAILED for", g, fc, neg)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
(OUT / "answers.template.json").write_text(json.dumps(
    {str(t["n"]): {"answer": None, "note": ""} for t in manifest["tiles"]}, indent=1))
print("wrote", n, "tiles to", OUT)
