"""ROADMAP 2.99 blind print tiles: what is the bracketed mark?

    python3 .../tiles_2_99.py <AB_DIR_LIT> <AB_DIR_BRAH> <REC_LIT> <REC_BRAH> OUTDIR

`AB_DIR_*` hold `ab2_99.json` (2.99_ab.py). The records are loaded ONLY for page
geometry (cell boxes, staff lines): nothing is re-decided here.

Each tile: one BAR cut from the plate at the gather's 600 dpi (render_page's
frame), 900 px wide (phone), a big tile number on a banner, a RED corner bracket
on the bar (following its staff) and a BLUE corner bracket on the marked piece.
Nothing of ours is written on the image: what we read, and what each tile is FOR
(decided rest / refused look-alike / abstention / a standing box's mislabel), is in
manifest.json only. Order is shuffled so the answer does not follow the kind.

Frame control (it can fail): the five staff lines the record filed must carry
>= 2x the ink of the rows between them AND the same test shifted half a space
must FAIL; a tile whose control fails is skipped and reported.
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
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
AB = {"lit": Path(sys.argv[1]), "brah": Path(sys.argv[2])}
RECS = {"lit": sys.argv[3], "brah": sys.argv[4]}
OUT = Path(sys.argv[5])
OUT.mkdir(parents=True, exist_ok=True)

# (movement, subject, what this tile is FOR) -- in the order they are SHOWN.
PLAN = [
    ("lit", "glyph/2/0/5/1/350000", "decided eighth rest (its bar was held, now adds up)"),
    ("brah", "glyph/1/0/4/1/350003", "decided eighth rest (bar adds up in base by cancellation, overfull now)"),
    ("lit", "glyph/2/1/9/5/350000", "REFUSED look-alike: stem stroke (a flat?), not a rest"),
    ("lit", "glyph/2/0/7/3/350000", "decided quarter rest (its bar was held, now adds up)"),
    ("brah", "glyph/1/0/9/6/350001", "decided eighth rest (its bar was held, now adds up)"),
    ("lit", "glyph/2/0/2/5/350000", "CONTROL: a standing box says accidentalDoubleSharp; the ink reads eighth rest"),
    ("lit", "glyph/1/0/7/0/350000", "decided eighth rest (bar sums by cancellation in base; a key flat boxed as rest8th)"),
    ("brah", "glyph/1/0/2/0/350002", "ABSTAINED: tall narrow ink, shape cannot tell"),
    ("lit", "glyph/3/0/4/10/350000", "decided eighth rest (its bar was held, now adds up)"),
    ("brah", "glyph/1/1/3/6/350002", "decided eighth rest (bar still held)"),
    ("lit", "glyph/3/0/9/0/350000", "REFUSED look-alike: stem stroke (a flat?), first bar of a system"),
    ("lit", "glyph/2/0/6/3/350000", "decided quarter rest (the bar had no events before)"),
]


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


def bracket(arr, x0, y0, x1, y1, colour, arm=40, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


def _band(ink, x0, x1, rows):
    return float(np.mean([ink[int(r) - 1:int(r) + 2, x0:x1].mean() for r in rows]))


def local_lines_fit(ink, cx, lines):
    """Best vertical offset (in staff spaces) of the filed lines against the ink in
    a window of +-4 spaces around the SUBJECT's x (a scanned staff tilts: a bar-wide
    straight line is the wrong ruler -- CLAUDE.md "measure against the staff LOCALLY").
    Returns (best_dy_spaces, ratio_at_best, ratio_at_half_space_off)."""
    sp = float(np.mean(np.diff(lines)))
    x0, x1 = int(cx - 4 * sp), int(cx + 4 * sp)
    best = (0.0, 0.0)
    for dy in np.arange(-0.7, 0.71, 0.05):
        rows = [y + dy * sp for y in lines]
        mids = [(a_ + b_) / 2 + dy * sp for a_, b_ in zip(lines[:-1], lines[1:])]
        r = _band(ink, x0, x1, rows) / max(_band(ink, x0, x1, mids), 1e-6)
        if r > best[1]:
            best = (float(dy), r)
    rows = [y + (best[0] + 0.5) * sp for y in lines]
    mids = [(a_ + b_) / 2 + (best[0] + 0.5) * sp for a_, b_ in zip(lines[:-1], lines[1:])]
    neg = _band(ink, x0, x1, rows) / max(_band(ink, x0, x1, mids), 1e-6)
    return best[0], best[1], neg


def frame_control(ink, box, lines, mark):
    """A control that can FAIL: the five filed lines, fitted LOCALLY at the mark's x
    (+-0.7 space search), must carry >= 2x the ink of the gaps at the best fit AND the
    same test half a space off must be clearly worse. The best offset is REPORTED: a
    scanned staff wanders by up to a space, and the red bar bracket follows the filed
    lines, so this is what the tile shows, not a claim about the mark -- the BLUE
    bracket is the cluster's own page box, measured off the same raster."""
    cx = (mark[0] + mark[2]) / 2
    dy, ratio, neg = local_lines_fit(ink, cx, lines)
    return {"line_offset_spaces": round(dy, 2), "line_ratio": round(ratio, 2),
            "line_ratio_half_off": round(neg, 2),
            "passes": bool(ratio >= 2.0 and neg < ratio / 1.5)}


def main():
    manifest = {"dpi": 600,
                "question": ("What is the mark inside the BLUE corners? If it is a "
                             "rest, which kind (eighth, quarter, ...)? If it is not a "
                             "rest, what is it (a flat, a sharp, a dot, something "
                             "else)? The RED corners are only the bar it is in."),
                "tiles": []}
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    data = {k: json.load(open(AB[k] / "ab2_99.json")) for k in AB}
    recs, pages = {}, {}
    n = 0
    for mv, sub, purpose in PLAN:
        cl = data[mv]["clusters"].get(sub)
        if cl is None:
            print("no cluster", sub)
            continue
        det = cl["detail"]
        p = sub.split("/")
        page, system, staff, cell = (int(x) for x in p[1:5])
        if mv not in recs:
            doc = load_record(RECS[mv])
            recs[mv] = doc["record"] if "record" in doc else doc
        cell_box, lines = geometry(recs[mv], page, system)
        if (staff, cell) not in cell_box or staff not in lines:
            print("no geometry", sub)
            continue
        if (mv, page) not in pages:
            pages[(mv, page)] = np.asarray(Image.fromarray(
                render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
        img = pages[(mv, page)].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        bx, ln = cell_box[(staff, cell)], lines[staff]
        sp = float(np.mean(np.diff(ln)))
        fc = frame_control(ink, bx, ln, det["bbox_page_px"])
        if not fc["passes"]:
            print("skipped (frame control)", sub, fc)
            continue
        pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
        wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        n += 1
        bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp),
                int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
        b = det["bbox_page_px"]
        bracket(img, int(b[0]) - 6, int(b[1]) - 6, int(b[2]) + 6, int(b[3]) + 6,
                (0, 70, 230), arm=18, thick=5)
        crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
        crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))),
                           Image.LANCZOS)
        tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
        ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
        tile.paste(crop, (0, 130))
        name = f"tile_{n:02d}.png"
        tile.save(OUT / name)
        manifest["tiles"].append({
            "n": n, "file": name, "movement": mv, "subject": sub,
            "tile_is_for": purpose,
            "our_reading": {"outcome": cl["outcome"], "value": cl["value"],
                            "reason": cl["reason"]},
            "ink": {k: det.get(k) for k in (
                "width_spaces", "height_spaces", "staff_step", "max_column_share",
                "mass_y", "column_profile", "coverage", "covered_by")},
            "bar_cell": [page, system, staff, cell],
            "frame_control": fc,
            "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
