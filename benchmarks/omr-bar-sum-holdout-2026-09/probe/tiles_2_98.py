"""ROADMAP 2.98 blind print tiles: bars the lone-whole-rest rule released.

    python3 .../tiles_2_98.py OUTDIR  (reads out/2.98/{lit,brah}-*.json)

One bar per tile, cut from the plate at the gather's 600 dpi, phone-sized
(900 px wide), a big tile number, a RED corner bracket on the bar (following
the staff), BLUE corner brackets on the whole rest we sized. NOTHING of ours is
on the image; our reading (what meter the file wrote, how the rest was sized,
whether the meter was read or carried) is in manifest.json only.

Question for Sean (every tile): is the bracketed rest a whole-bar rest, and
what meter is this bar in?

Frame control (it can fail): the staff lines the record filed must carry >= 2x
the ink of the rows between them AND the same test shifted half a space must
FAIL; a tile whose control fails is skipped.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record import meter_at  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
RECS = {
    "brah": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261011-night.record.json",
    "lit": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-20261011-night.record.json",
}
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
DUMP = Path("benchmarks/omr-bar-sum-holdout-2026-09/out/2.98")


def held(label, arm):
    d = json.load(open(DUMP / f"{label}-{arm}.json"))
    return {tuple(h[:4]) + (h[4],): h for h in d["held_list"]}


def index(rec):
    """ONE pass over the record: per (page, system) the cell boxes, staff
    lines, restWhole glyph boxes, and the system's latest meter verdict."""
    cb, ln, gb, mt = {}, {}, {}, {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q not in ("cell_box", "staff_lines", "glyph_box"):
            continue
        p = o["subject"].split("/")
        if len(p) < 4:
            continue
        key = (int(p[1]), int(p[2]))
        if q == "cell_box" and p[0] == "cell":
            cb.setdefault(key, {})[(int(p[3]), int(p[4]))] = o["value"]
        elif q == "staff_lines" and p[0] == "staff":
            ln.setdefault(key, {})[int(p[3])] = o["value"]
        elif q == "glyph_box" and p[0] == "glyph" and o["value"][0] == "restWhole":
            gb.setdefault(key, []).append(
                (int(p[3]), int(p[4]), o["detail"]["bbox_page_px"]))
    for v in rec["verdicts"]:
        if v["quantity"] == "meter" and v["subject"].startswith("system/"):
            p = v["subject"].split("/")
            mt[(int(p[1]), int(p[2]))] = v          # last row wins
    return cb, ln, gb, mt


def bracket(arr, x0, y0, x1, y1, colour, arm=40, thick=6):
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


def spread(seq, k):
    if not seq or k <= 0:
        return []
    return [seq[min(len(seq) - 1, int((i + 0.5) * len(seq) / k))] for i in range(k)]


def after_change(key, mt):
    """Is this bar the first or second bar of a later meter segment?"""
    page, system, staff, cell, part = key
    v = mt.get((page, system)) or {}
    val = v.get("value") if v.get("outcome") == "decided" else None
    if not isinstance(val, dict):
        return False
    return any(cell - int(sg.get("from_cell", 0)) in (0, 1)
               for sg in (val.get("segments") or [])
               if int(sg.get("from_cell", 0)) > 0)


def choose(label, mt):
    base = held(label, "twin0_lone0")
    arm = held(label, "twin1_lone1") if label == "lit" else held(label, "twin0_lone1")
    out_all = sorted(k for k in base if k not in arm)
    if label == "lit":
        only_twin = held(label, "twin1_lone0")
        by2 = sorted(k for k in base if k not in only_twin)
        rest = [k for k in out_all if k not in by2]
        return [(k, "part2_twin") for k in spread(by2, 3)] + \
               [(k, "lone_only") for k in rest][:1] + \
               [(k, "lone") for k in spread(rest[1:], 0)]
    changed = [k for k in out_all if after_change(k, mt)]
    plain = [k for k in out_all if k not in changed]
    return ([(k, "right_after_a_meter_change") for k in spread(changed, 2)]
            + [(k, "lone") for k in spread(plain, 4)])


def main():
    manifest = {"dpi": 600,
                "question": ("Look at the REST inside the BLUE corners, in the bar "
                             "inside the RED corners. Is it a whole-bar rest (one "
                             "rest that stands for the whole bar)? And what meter "
                             "is this bar in?"),
                "tiles": []}
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    n = 0
    pages = {}
    global IDX
    for mv in ("lit", "brah"):
        doc = load_record(RECS[mv])
        rec = doc["record"] if "record" in doc else doc
        IDX = index(rec)
        picks = choose(mv, IDX[3])
        if not picks:
            print("nothing released on", mv)
            continue
        # a bar right after a printed meter change goes first on Brahms
        scored = []
        for (key, why) in picks:
            scored.append((key, why))
        for (key, why) in scored:
            page, system, staff, cell, part = key
            cell_box = IDX[0].get((page, system), {})
            lines = IDX[1].get((page, system), {})
            boxes = IDX[2].get((page, system), [])
            mv_verdict = IDX[3].get((page, system))
            if (staff, cell) not in cell_box or staff not in lines:
                print("no geometry", mv, key)
                continue
            rest_boxes = [b for (s, c, b) in boxes if s == staff and c == cell]
            if not rest_boxes:
                print("no rest box", mv, key)
                continue
            if (mv, page) not in pages:
                pages[(mv, page)] = np.asarray(Image.fromarray(
                    render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
            img = pages[(mv, page)].copy()
            ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
            bx, ln = cell_box[(staff, cell)], lines[staff]
            sp = float(np.mean(np.diff(ln)))
            fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
            if not fc["passes"] or neg["passes"]:
                print("skipped (frame control)", mv, key, fc, neg)
                continue
            pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
            wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
            wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
            n += 1
            bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp),
                    int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
            for b in rest_boxes:
                bracket(img, int(b[0]) - 6, int(b[1]) - 6, int(b[2]) + 6,
                        int(b[3]) + 6, (0, 70, 230), arm=18, thick=5)
            crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
            crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))),
                               Image.LANCZOS)
            tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
            ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
            tile.paste(crop, (0, 130))
            name = f"tile_{n:02d}.png"
            tile.save(OUT / name)
            sysm = (mv_verdict or {})
            here = meter_at(sysm.get("value"), cell) if sysm.get("outcome") == "decided" else None
            segs = [s.get("from_cell") for s in
                    ((sysm.get("value") or {}).get("segments") or [])] \
                if isinstance(sysm.get("value"), dict) else []
            manifest["tiles"].append({
                "n": n, "file": name, "movement": mv, "page": page,
                "system": system, "staff": staff, "cell": cell, "part": part,
                "released_by": why,
                "system_meter_outcome": sysm.get("outcome"),
                "system_meter_reason": sysm.get("reason"),
                "meter_filed_at_this_bar": here,
                "meter_segments_from_cell": segs,
                "our_reading": ("lone dotless whole rest = the bar, sized to the "
                                "meter the file has in force"
                                + (" (CARRIED: the system's own meter did not settle)"
                                   if here is None else " (the system's meter declared)")),
                "frame_control": fc, "frame_control_negative": neg,
                "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
