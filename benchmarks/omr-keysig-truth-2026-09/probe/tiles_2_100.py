"""ROADMAP 2.100 blind print tiles: what key signature is this, and what is the bracketed mark?

    python3 .../tiles_2_100.py PLAN.json OUTDIR

PLAN.json: {"records": {"lit": REC, "brah": REC}, "tiles": [[mv, glyph_subject, purpose], ...]}.
The records are loaded ONLY for page geometry (nothing is re-decided).

Each tile: ONE staff's header (clef through the first bar's start) cut from the
plate at the gather's 600 dpi, 900 px wide (phone), a big tile number on a
banner, a RED corner bracket on the stretch from the clef to the last key
accidental the record filed, a BLUE corner bracket on the marked box. Nothing of
ours is written on the image: what we read and what the tile is FOR is in
manifest.json only. Order is shuffled (fixed seed) so the answer does not follow
the kind.

Frame control (it can fail): the five staff lines the record filed must carry
>= 2x the ink of the rows between them AND the same test shifted half a space
must be clearly worse; a tile whose control fails is skipped and reported.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.adjudicators import key_slots as KS  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
plan = json.load(open(sys.argv[1]))
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


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


def frame_control(ink, cx, lines):
    sp = float(np.mean(np.diff(lines)))
    x0, x1 = int(cx - 4 * sp), int(cx + 4 * sp)
    best = (0.0, 0.0)
    for dy in np.arange(-0.7, 0.71, 0.05):
        rows = [y + dy * sp for y in lines]
        mids = [(a + b) / 2 + dy * sp for a, b in zip(lines[:-1], lines[1:])]
        r = _band(ink, x0, x1, rows) / max(_band(ink, x0, x1, mids), 1e-6)
        if r > best[1]:
            best = (float(dy), r)
    rows = [y + (best[0] + 0.5) * sp for y in lines]
    mids = [(a + b) / 2 + (best[0] + 0.5) * sp for a, b in zip(lines[:-1], lines[1:])]
    neg = _band(ink, x0, x1, rows) / max(_band(ink, x0, x1, mids), 1e-6)
    return {"line_offset_spaces": round(best[0], 2), "line_ratio": round(best[1], 2),
            "line_ratio_half_off": round(neg, 2),
            "passes": bool(best[1] >= 2.0 and neg < best[1] / 1.5)}


def main():
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    manifest = {"dpi": 600,
                "question": ("What key signature is this (how many flats or "
                             "sharps, or none)? And what is the mark inside "
                             "the BLUE corners (a flat, a rest, a note, a "
                             "number, something else)? The RED corners only "
                             "show where we looked for the key."),
                "tiles": []}
    recs, pages = {}, {}
    for mv, path in plan["records"].items():
        doc = load_record(path)
        recs[mv] = doc["record"] if "record" in doc else doc
    items = list(plan["tiles"])
    random.Random(2100).shuffle(items)
    n = 0
    for mv, sub, purpose in items:
        rec = recs[mv]
        p = sub.split("/")
        page, system, staff = int(p[1]), int(p[2]), int(p[3])
        obs = {}
        lines = None
        cellbox = None
        cell_rows = []
        space = 0
        for o in rec["observations"]:
            s = o["subject"]
            if s == f"staff/{page}/{system}/{staff}" and o["quantity"] == "staff_lines":
                lines = o["value"]
            elif s == f"cell/{page}/{system}/{staff}/0":
                if o["quantity"] == "cell_box":
                    cellbox = o["value"]
                elif o["quantity"] == "cell_staff_space":
                    space = float(o["value"])
            elif s.startswith(f"glyph/{page}/{system}/{staff}/0/") and o["quantity"] == "glyph_box":
                obs[s] = o
                cell_rows.append(o)
        if lines is None or cellbox is None or sub not in obs:
            print("no geometry", sub)
            continue
        boxes = KS.boxes_of_rows(cell_rows) if hasattr(KS, "boxes_of_rows") else None
        if boxes is None:
            class _R:  # minimal row for key_slots.boxes_of
                def __init__(self, o):
                    self.id, self.value = o["id"], o["value"]
            boxes = KS.boxes_of([_R(o) for o in cell_rows])
        win = KS.key_slot_window(boxes, space)
        by_id = {o["id"]: o for o in cell_rows}
        if (mv, page) not in pages:
            pages[(mv, page)] = np.asarray(Image.fromarray(
                render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
        img = pages[(mv, page)].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        sp = float(np.mean(np.diff(lines)))
        mark = obs[sub]["detail"]["bbox_page_px"]
        fc = frame_control(ink, (mark[0] + mark[2]) / 2, lines)
        if not fc["passes"]:
            print("skipped (frame control)", sub, fc)
            continue
        x0 = int(cellbox[0])
        wx0, wx1 = max(x0 - int(1.0 * sp), 0), int(max(x0 + 15 * sp, mark[2] + 3 * sp))
        wy0, wy1 = int(lines[0] - 4.0 * sp), int(lines[-1] + 4.0 * sp)
        n += 1
        red = None
        if win is not None:
            pb = [by_id[i]["detail"]["bbox_page_px"] for i in win.members if i in by_id]
            if win.clef and win.clef in by_id:
                pb.append(by_id[win.clef]["detail"]["bbox_page_px"])
            if pb:
                red = [min(b[0] for b in pb), min(b[1] for b in pb),
                       max(b[2] for b in pb), max(b[3] for b in pb)]
                bracket(img, int(red[0]) - 8, int(red[1]) - 8, int(red[2]) + 8,
                        int(red[3]) + 8, (220, 0, 0), arm=30, thick=5)
        bracket(img, int(mark[0]) - 6, int(mark[1]) - 6, int(mark[2]) + 6,
                int(mark[3]) + 6, (0, 70, 230), arm=16, thick=5)
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
            "tile_is_for": purpose, "class": obs[sub]["value"][0],
            "key_window_found": win is not None,
            "key_slots": None if win is None else win.slots,
            "frame_control": fc, "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
