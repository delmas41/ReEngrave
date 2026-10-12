"""2.90 blind print tiles for Sean: heads the exporter NEWLY writes as two voices.

    python3 .../2.90_tiles.py OUTDIR  DOC:RECORD.json:ROWS.json[:K] [...]

`ROWS.json` is `2.90_newly_two_voice.py`'s output. Each tile: one bar, phone-sized
(900 px wide), a big tile number, a RED corner bracket round EACH head the bar
now carries from the divisi split (the staff is the page's own). Question in
`manifest.json`: the written value of the note in each bracket, top to bottom.
Our values (and which voice) are in `manifest.json` ONLY, never on the image.
Same frame control as 2.89_tiles.py (asserted per tile, with its negative).
Sean's already-answered 2.89 tiles are skipped.
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
# the 2.89 tiles Sean already judged (document, page, system, staff, cell)
ANSWERED = {("brahms", 0, 0, 11, 5), ("brahms", 0, 0, 13, 1), ("brahms", 1, 0, 0, 3),
            ("brahms", 1, 0, 2, 5), ("brahms", 1, 0, 3, 2), ("litolff", 4, 0, 5, 12),
            ("litolff", 6, 0, 5, 9), ("litolff", 7, 1, 2, 13), ("litolff", 2, 0, 7, 4),
            ("litolff", 12, 0, 2, 5), ("litolff", 13, 1, 9, 13)}
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
DPI = 600


def geometry(rec, page, system):
    cell_box, lines = {}, {}
    for o in rec["observations"]:
        p = o["subject"].split("/")
        if len(p) > 3 and p[1] == str(page) and p[2] == str(system):
            if o["quantity"] == "cell_box" and p[0] == "cell":
                cell_box[(int(p[3]), int(p[4]))] = o["value"]
            elif o["quantity"] == "staff_lines" and p[0] == "staff":
                lines[int(p[3])] = o["value"]
    return cell_box, lines


def bracket(arr, x0, y0, x1, y1, colour, arm=22, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
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


try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()

work = []
for spec in sys.argv[2:]:
    parts = spec.split(":")
    doc, rec_path, rows_path = parts[:3]
    k = int(parts[3]) if len(parts) > 3 else 6
    result = load_record(rec_path)
    rec = result["record"] if "record" in result else result
    rows = [r for r in json.load(open(rows_path))
            if (doc, r["page"], r["system"], r["staff"], r["cell"]) not in ANSWERED
            and all(h.get("bbox_page") for h in r["heads"])
            and len(r["heads"]) <= 4]       # more brackets than a phone can tell apart
    # written bars first (the heads the file now carries), then kept-but-held-out
    rows.sort(key=lambda v: (v["held_out_by_sum"], v["page"], v["system"], v["staff"], v["cell"]))
    step = max(1, len(rows) // max(k, 1))
    for v in rows[::step][:k + 4]:          # spare for frame-control skips
        work.append((doc, rec, v, k))

pages, manifest = {}, {
    "dpi": DPI,
    "question": "What is the written value of the note inside each RED corner "
                "bracket (whole, half, quarter, eighth, ..., dotted or not)? "
                "Answer top to bottom.",
    "tiles": []}
quota = {}
n = 0
for doc, rec, v, k in work:
    if quota.get(doc, 0) >= k:
        continue
    page, system, staff, c = v["page"], v["system"], v["staff"], v["cell"]
    boxes = [h["bbox_page"] for h in v["heads"]]
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(
            Image.fromarray(render_page(PDFS[doc], page, dpi=DPI).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    cell_box, lines = geometry(rec, page, system)
    if (staff, c) not in cell_box or staff not in lines:
        continue
    bar, ln = cell_box[(staff, c)], lines[staff]
    sp = float(np.mean(np.diff(ln)))
    cal = max((t / 20.0 for t in range(-8, 9)),
              key=lambda t: frame_control(ink, bar, ln, t)["ratio"])
    fc = frame_control(ink, bar, ln, cal)
    neg = frame_control(ink, bar, ln, cal + 0.5)
    if not fc["passes"] or neg["passes"]:
        print("skipped (frame control):", doc, page, system, staff, c, fc, neg)
        continue
    if not (ln[0] - 8 * sp <= (y0 + y1) / 2 <= ln[-1] + 8 * sp):
        print("skipped (heads off the staff band):", doc, page, system, staff, c)
        continue
    n += 1
    quota[doc] = quota.get(doc, 0) + 1
    pad = int(max(2.5 * sp, (26 * sp - (bar[2] - bar[0])) / 2))
    wx0, wx1 = int(bar[0]) - pad, int(bar[2]) + pad
    wy0, wy1 = int(min(ln[0] - 5.5 * sp, y0 - sp)), int(max(ln[-1] + 5.5 * sp, y1 + sp))
    for h in v["heads"]:
        bx, by, bw, bh = h["bbox_page"]
        bracket(img, int(bx) - 8, int(by) - 8, int(bx + bw) + 8, int(by + bh) + 8,
                (220, 0, 0))
    crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    manifest["tiles"].append({
        "n": n, "file": name, "document": doc, "page": page, "system": system,
        "staff": staff, "cell": c, "n_heads": len(v["heads"]),
        "bar_written_by_the_export": not v["held_out_by_sum"],
        "heads_top_to_bottom": [
            {k_: h[k_] for k_ in ("pitch", "voice", "beats", "type", "dots", "dir")}
            for h in sorted(v["heads"], key=lambda h: h["bbox_page"][1])],
        "frame_control": fc, "frame_control_negative": neg,
        "calibration_shift_spaces": cal,
        "page_box_600dpi": [wx0, wy0, wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
(OUT / "answers.template.json").write_text(json.dumps(
    {str(t["n"]): {"values_top_to_bottom": None, "note": ""} for t in manifest["tiles"]}, indent=1))
print("wrote", n, "tiles to", OUT)
