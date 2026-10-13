"""ROADMAP 2.101 blind print tiles (held-out publishers).

    python3 make_tiles.py PLAN.json OUTDIR

PLAN.json = {"docs": {doc: {"pdf": ..., "record": ARM_RECORD}}, "tiles": [spec,...]}
spec = {"doc", "kind": "mark" | "note" | "label", "subject": "...", "box": [x0,y0,x1,y1]|null,
        "purpose": "what this tile is FOR", "our_reading": {...}}

Each tile: the bar cut from the plate at the gather's 600 dpi (render_page's frame),
900 px wide (phone), a big tile number on a banner, a RED corner bracket on the bar
following its staff and a BLUE corner bracket on the subject. Nothing of ours is written
on the image: our reading, and what each tile is FOR, go in manifest.json only. Order is
shuffled (seeded) so the answer does not follow the kind or the score.

Frame control (it can fail): the five staff lines the record filed, fitted LOCALLY at the
subject's x, must carry >= 2x the ink of the gaps AND the same test half a space off must
be clearly worse; a tile that fails is skipped and reported.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

PLAN = json.load(open(sys.argv[1]))
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

QUESTIONS = {
    "mark": ("What is the mark inside the BLUE corners? If it is a rest, which kind "
             "(eighth, quarter, ...)? If it is not a rest, what is it (a flat, a sharp, a "
             "dot, part of a note, something else)? The RED corners are only the bar it is in."),
    "note": ("What note value is the note inside the BLUE corners (whole, half, quarter, "
             "eighth, sixteenth ...), or is it not a note? The RED corners are only the bar it is in."),
    "label": ("What is printed to the LEFT of the staff marked by the RED bracket (the "
              "instrument name as printed, or nothing)? Read only the line at that staff."),
}


def geometry(R, page, system):
    cell_box, lines = {}, {}
    for o in R["observations"]:
        p = o["subject"].split("/")
        if len(p) > 3 and p[1] == str(page) and p[2] == str(system):
            if o["quantity"] == "cell_box" and p[0] == "cell":
                cell_box[(int(p[3]), int(p[4]))] = o["value"]
            elif o["quantity"] == "staff_lines" and p[0] == "staff":
                lines[int(p[3])] = o["value"]
    return cell_box, lines


def bracket(arr, x0, y0, x1, y1, colour, arm=40, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


def _band(ink, x0, x1, rows):
    return float(np.mean([ink[int(r) - 1:int(r) + 2, x0:x1].mean() for r in rows]))


def local_lines_fit(ink, cx, lines):
    sp = float(np.mean(np.diff(lines)))
    x0, x1 = max(int(cx - 4 * sp), 0), int(cx + 4 * sp)
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


def fixed_ratio(ink, cx, lines, dy):
    sp = float(np.mean(np.diff(lines)))
    x0, x1 = max(int(cx - 4 * sp), 0), int(cx + 4 * sp)
    rows = [y + dy * sp for y in lines]
    mids = [(a_ + b_) / 2 + dy * sp for a_, b_ in zip(lines[:-1], lines[1:])]
    return _band(ink, x0, x1, rows) / max(_band(ink, x0, x1, mids), 1e-6)


def main():
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    specs = list(PLAN["tiles"])
    random.Random(2101).shuffle(specs)
    recs, pages = {}, {}
    manifest = {"dpi": 600, "questions": QUESTIONS, "tiles": []}
    skipped = []
    n = 0
    for sp_ in specs:
        doc, kind, sub = sp_["doc"], sp_["kind"], sp_["subject"]
        d = PLAN["docs"][doc]
        p = sub.split("/")
        page, system, staff, cell = (int(x) for x in p[1:5])
        if doc not in recs:
            recs[doc] = load_record(d["record"])["record"]
        cell_box, lines = geometry(recs[doc], page, system)
        if (staff, cell) not in cell_box or staff not in lines:
            skipped.append((sub, "no geometry"))
            continue
        if (doc, page) not in pages:
            pages[(doc, page)] = np.asarray(Image.fromarray(
                render_page(d["pdf"], page, dpi=600).rgb).convert("RGB"))
        img = pages[(doc, page)].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        bx, ln = cell_box[(staff, cell)], lines[staff]
        sp = float(np.mean(np.diff(ln)))
        box = sp_.get("box")
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        if kind == "label":
            cx = bx[0] + 5 * sp
            wx0, wx1 = max(int(bx[0] - 22 * sp), 0), int(bx[0] + 9 * sp)
            wy0, wy1 = int(ln[0] - 2.5 * sp), int(ln[-1] + 2.5 * sp)
        else:
            if box is None:
                skipped.append((sub, "no box"))
                continue
            cx = (box[0] + box[2]) / 2
            pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
            wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        dy, ratio, neg = local_lines_fit(ink, cx, ln)
        fc = {"line_offset_spaces": round(dy, 2), "line_ratio": round(ratio, 2),
              "line_ratio_half_off": round(neg, 2),
              "passes": bool(ratio >= 2.0 and neg < ratio / 1.5)}
        # the control must be able to FAIL: the same lines shifted half a space past the best fit
        fc["ratio_with_lines_shifted_half_a_space"] = round(fixed_ratio(ink, cx, ln, dy + 0.5), 2)
        fc["shifted_lines_would_pass"] = bool(fc["ratio_with_lines_shifted_half_a_space"] >= 2.0)
        if not fc["passes"]:
            skipped.append((sub, f"frame control {fc}"))
            continue
        n += 1
        if kind == "label":
            bracket(img, wx1 - 70, int(ln[0] - 0.8 * sp), wx1 - 8, int(ln[-1] + 0.8 * sp), (220, 0, 0), arm=26)
        else:
            bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp), int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
            bracket(img, int(box[0]) - 6, int(box[1]) - 6, int(box[2]) + 6, int(box[3]) + 6,
                    (0, 70, 230), arm=18, thick=5)
        crop = Image.fromarray(img[max(wy0, 0):wy1, max(wx0, 0):wx1])
        crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
        tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
        ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
        tile.paste(crop, (0, 130))
        name = f"tile_{n:02d}.png"
        tile.save(OUT / name)
        manifest["tiles"].append({
            "n": n, "file": name, "doc": doc, "kind": kind, "subject": sub,
            "question": kind, "tile_is_for": sp_["purpose"],
            "our_reading": sp_.get("our_reading"), "rule": sp_.get("rule"),
            "page_pdf_index": page, "frame_control": fc,
            "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (OUT / "answers.template.json").write_text(json.dumps(
        {"verbatim": "", "tiles": [{"n": t["n"], "sean": "", "scored": ""} for t in manifest["tiles"]]}, indent=1))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)
    for s in skipped:
        print("skipped", s)


main()
