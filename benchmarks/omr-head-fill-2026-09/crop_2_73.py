"""ROADMAP 2.73 -- print crops of heads the change newly decided, for Sean to judge ONE AT A TIME.

PATH: STAGED, GATHER+ADJUDICATE. Each tile is a crop of the PDF page at the gather's own dpi (600), the head
bracketed in red corner brackets (the head the record NOW holds: the rebuilt standard head box where
`Q.HEAD_LINE_CUT` read the mirror hole, else the kept detector box), the staff lines visible, and NOTHING of
ours drawn -- no box, no label, no reading. Blind: the reading is in the manifest, not on the tile.

FRAME CONTROL (a control that can fail, CLAUDE.md rule 7): before a tile is written the record's own staff
lines for the head's staff are laid on the page raster; the five lines must read darker than the four spaces
between them over the staff's extent, by `MIN_CONTRAST`. A tile whose frame is off by a line is REFUSED and
listed in the manifest as refused -- it is never shown.

    python3 benchmarks/omr-head-fill-2026-09/crop_2_73.py SELECTION.json OUT_DIR

SELECTION.json: {"question": str, "tiles": [{"record": path, "pdf": path, "subject": "glyph/p/s/st/c/g",
                 "label": str, "today_before": str, "today_after": str}, ...]}
"""
from __future__ import annotations

import json
import os
import sys

MIN_CONTRAST = 1.5          # mean darkness on the 5 lines / mean darkness in the 4 spaces
DPI = 600
Z = 2


def frame_control(arr, lines, x0, x1):
    """Mean ink on the staff's five line rows vs the four spaces between them, over `[x0, x1)`."""
    import numpy as np
    on, off = [], []
    for i, y in enumerate(lines):
        yy = int(round(y))
        on.append(255.0 - arr[max(0, yy - 1):yy + 2, x0:x1].mean())
        if i + 1 < len(lines):
            ym = int(round((y + lines[i + 1]) / 2.0))
            off.append(255.0 - arr[max(0, ym - 1):ym + 2, x0:x1].mean())
    a, b = float(np.mean(on)), float(np.mean(off))
    return a / max(b, 1.0), a, b


def head_box_page(run, key):
    """The head's box in page px: the rebuilt standard head where a `head_line_cut` row stands, else the kept box."""
    g = run.glyphs[key]
    box = g.box_page
    cut = run.obs_at(key, "head_line_cut")
    if cut and g.box_canon and g.box_page:
        x, y, w, h = (float(v) for v in cut[-1]["value"])
        sx = (g.box_page[2] - g.box_page[0]) / (g.box_canon[2] - g.box_canon[0])
        sy = (g.box_page[3] - g.box_page[1]) / (g.box_canon[3] - g.box_canon[1])
        box = (g.box_page[0] + (x - g.box_canon[0]) * sx, g.box_page[1] + (y - g.box_canon[1]) * sy,
               g.box_page[0] + (x + w - g.box_canon[0]) * sx, g.box_page[1] + (y + h - g.box_canon[1]) * sy)
    return box


def main(argv=None):
    sys.path.insert(0, os.getcwd())
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import readout
    sel = json.load(open(argv[0] if argv else sys.argv[1]))
    out_dir = argv[1] if argv else sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    runs, docs, pages = {}, {}, {}
    man = []
    n = 0
    for t in sel["tiles"]:
        run = runs.setdefault(t["record"], readout.load_run(t["record"]))
        key = t["subject"]
        p = run.glyphs[key].page
        doc = docs.setdefault(t["pdf"], fitz.open(t["pdf"]))
        if (t["pdf"], p) not in pages:
            pm = doc[p].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[(t["pdf"], p)] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
        arr = pages[(t["pdf"], p)]
        sk = f"staff/{run.glyphs[key].page}/{run.glyphs[key].system}/{run.glyphs[key].staff}"
        lines = run.obs_at(sk, "staff_lines")[-1]["value"]
        ext = run.obs_at(sk, "staff_extent")
        x0, x1 = (int(ext[-1]["value"][0]), int(ext[-1]["value"][1])) if ext else (0, arr.shape[1])
        ratio, a, b = frame_control(arr, lines, x0, x1)
        x0b, y0b, x1b, y1b = head_box_page(run, key)
        entry = {"subject": key, "label": t.get("label"), "page": p, "page_box": [x0b, y0b, x1b, y1b],
                 "frame_contrast": round(ratio, 2), "today_before": t.get("today_before"),
                 "today_after": t.get("today_after"), "verdict_none_yet": None}
        if ratio < MIN_CONTRAST:
            entry["refused"] = "frame control: staff lines do not read darker than the spaces"
            man.append(entry)
            continue
        n += 1
        cx, cy = (x0b + x1b) / 2, (y0b + y1b) / 2
        W, H = 260, 190
        clip = fitz.Rect((cx - W) * 72 / DPI, (cy - H) * 72 / DPI, (cx + W) * 72 / DPI, (cy + H) * 72 / DPI)
        pix = doc[p].get_pixmap(dpi=DPI * Z, clip=clip)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        ox, oy = clip.x0 * DPI / 72, clip.y0 * DPI / 72
        a_, b_, c_, e_ = ((x0b - ox) * Z - 10, (y0b - oy) * Z - 10, (x1b - ox) * Z + 10, (y1b - oy) * Z + 10)
        d = ImageDraw.Draw(im)
        for (px, py, sx, sy) in ((a_, b_, 1, 1), (c_, b_, -1, 1), (a_, e_, 1, -1), (c_, e_, -1, -1)):
            d.line([(px, py), (px + sx * 18, py)], fill=(220, 0, 0), width=5)
            d.line([(px, py), (px, py + sy * 18)], fill=(220, 0, 0), width=5)
        out = Image.new("RGB", (im.width, im.height + 60), "white")
        out.paste(im, (0, 60))
        ImageDraw.Draw(out).text((10, 12), f"Tile {n} -- {t.get('label')}", fill="black", font=font)
        fn = f"head_{n:02d}.png"
        out.save(os.path.join(out_dir, fn))
        entry["file"] = fn
        entry["n"] = n
        man.append(entry)
    json.dump({"dpi": DPI, "question": sel.get("question"), "tiles": man}, open(os.path.join(out_dir, "manifest.json"), "w"),
              indent=1)
    print(f"{n} tiles, {sum(1 for m in man if m.get('refused'))} refused by the frame control")


if __name__ == "__main__":
    main()
