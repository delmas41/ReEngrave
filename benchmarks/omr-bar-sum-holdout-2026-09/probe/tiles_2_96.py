"""ROADMAP 2.96 print tiles: the top causes of a held bar, one bar per tile.

    python3 .../tiles_2_96.py <dump-dir> OUTDIR

`<dump-dir>` holds `{lit,brah}-2.96.held.json` (held_funnel_2_96.py) and
`{lit,brah}-part.json` (classify_held_2_96.py). The records are loaded ONLY for
page geometry (cell boxes, staff lines, glyph boxes): nothing is re-decided.

Each tile: one BAR cut from the plate at the gather's 600 dpi (render_page's
deskewed frame), phone-sized (900 px wide), a big tile number on a banner, a RED
corner bracket on the bar (following the staff), BLUE corner brackets on the
SUBJECT of the claimed cause. Nothing of ours is written on the image; our
reading is in manifest.json only.

Frame control (it can fail): the five staff lines the record filed must carry
>= 2x the ink of the rows between them AND the same test shifted half a space
must FAIL. A tile whose control fails is skipped and the next candidate taken.
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
RECS = {
    "brah": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261011-night.record.json",
    "lit": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-20261011-night.record.json",
}
DUMP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# (cause token, [(movement, how many)], plain description of what the blue marks)
PLAN = [
    ("N", [("brah", 2), ("lit", 1)]),
    ("W", [("brah", 2), ("lit", 1)]),
    ("I:eighth", [("brah", 2), ("lit", 1)]),
    ("D", [("brah", 3)]),
    ("F~", [("lit", 3)]),
]
WANT = {"N": "the notes we did not write because their value was undecided",
        "W": "a whole rest we left at four beats",
        "I:eighth": "ink in the bar that no box accounts for",
        "D": "a dot we saw and did not settle",
        "F~": "the note whose value we think we read one step wrong"}


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


def frame_control(ink, box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


def culprit_f(bar, T):
    """Chord events whose single head-fill/stem misread (quarter<->half,
    half<->whole) would land the bar (single stream)."""
    div = bar["detail"]["divisions"]
    s = bar["streams"][0]
    tot = sum(e["units"] / div for e in s)
    out = []
    for e in s:
        b = e["units"] / div
        if e["kind"] != "chord":
            continue
        for new in (2 * b, b / 2):
            if max(b, new) > 1.0 + 1e-9 and abs(tot - b + new - T) < 1e-6:
                out.append((e, new))
    return out


def subject_boxes(tok, bar, T, part_row, geom_extra):
    """-> (list of page-px boxes, plain-text reading for the manifest)"""
    boxes, reading = [], ""
    if tok == "N":
        for r in bar["refused_in_cell"]:
            if r["refusal"] == "duration_narrowed" and r.get("page_px"):
                boxes.append(r["page_px"])
                c = [x["value"]["beats"] for x in
                     (r.get("duration") or {}).get("candidates") or []]
                reading += f" head candidates {c};"
        reading = ("refused duration_narrowed (not written), bar "
                   f"{part_row['residual']:+} q short:" + reading)
    elif tok == "W":
        for s in bar["streams"]:
            for e in s:
                if e["kind"] == "rest":
                    boxes += [p for p in e["page_px"] if p]
        reading = ("lone dotless 4-beat rest not marked as a measure rest in a "
                   f"{bar['detail']['want_quarters']}-quarter bar; system meter "
                   f"{(bar.get('system_meter') or {}).get('outcome')}/"
                   f"{(bar.get('system_meter') or {}).get('reason')}")
    elif tok == "I:eighth":
        boxes = [u["box"] for u in (bar.get("ink") or {}).get("unexplained") or []
                 if u["cls"] == "eighth"]
        reading = (f"bar short {part_row['residual']:+} q; unexplained eighth-rest-"
                   "shaped ink (no standing box covers it)")
    elif tok == "D":
        boxes = [geom_extra[d["subject"]] for d in bar.get("dots") or []
                 if d["subject"] in geom_extra]
        reading = (f"bar {part_row['residual']:+} q short; Q.AUG_DOT row(s) in the "
                   "cell whose Q.DOT_ROLE is not decided: "
                   + str([(d.get("role") or {}).get("outcome") for d in bar["dots"]]))
    elif tok == "F~":
        for e, new in culprit_f(bar, T):
            boxes += [p for p in e["page_px"] if p]
            reading += f" {e['type']} read, a re-read to {new} q lands the bar;"
        reading = "ARITHMETIC ONLY (no record row points at it):" + reading
    return boxes, reading


def main():
    manifest = {"dpi": 600,
                "question": ("For the bar inside the RED corners: what is printed in "
                             "it, in order (notes and rests, with their values)? Then "
                             "look at the BLUE corners: what is there, and is anything "
                             "in the bar missing from or different at that place?"),
                "tiles": []}
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    data = {}
    for k in ("lit", "brah"):
        held = json.load(open(DUMP / f"{k}-2.96.held.json"))
        part = json.load(open(DUMP / f"{k}-part.json"))
        data[k] = ({tuple(b["cell"]): b for b in held["bars"]},
                   {tuple(r["cell"]): r for r in part["rows"]}, part)
    recs = {}
    pages = {}
    n = 0
    for tok, plan in PLAN:
        for mv, count in plan:
            by, rows, _part = data[mv]
            lead_ok = (lambda r, t=tok: r["cause"] == t and (r["tier"] == "evidenced" or t == "F~"))
            cands = sorted(c for c, r in rows.items() if lead_ok(r)
                           and by[c]["n_streams"] == 1)
            if tok == "N":
                # prefer a bar the record's own candidates land UNIQUELY
                pass
            if not cands:
                print("no candidates", tok, mv)
                continue
            if mv not in recs:
                doc = load_record(RECS[mv])
                recs[mv] = doc["record"] if "record" in doc else doc
            rec = recs[mv]
            extra = {}
            if tok == "D":
                want = {d["subject"] for c in cands for d in by[c].get("dots") or []}
                for o in rec["observations"]:
                    if o["quantity"] == "glyph_box" and o["subject"] in want:
                        extra[o["subject"]] = o["detail"]["bbox_page_px"]
            qs = [(i + 0.5) / count for i in range(count)]
            picked = 0
            used_pages = set()
            for q in qs:
                start = int(q * len(cands))
                for off in range(len(cands)):
                    c = cands[(start + off) % len(cands)]
                    if (mv, c) in [(t["movement"], tuple(t["_cell"])) for t in manifest["tiles"]]:
                        continue
                    bar, row = by[c], rows[c]
                    T = row["T"]
                    page, system, staff, cell = c
                    if (mv, page) in used_pages and off < len(cands) - 1 and len(cands) > 40:
                        continue
                    geo = geometry(rec, page, system)
                    cell_box, lines = geo
                    if (staff, cell) not in cell_box or staff not in lines:
                        continue
                    boxes, reading = subject_boxes(tok, bar, T, row, extra)
                    if not boxes:
                        continue
                    if (mv, page) not in pages:
                        pages[(mv, page)] = np.asarray(Image.fromarray(
                            render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
                    img = pages[(mv, page)].copy()
                    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
                    bx = cell_box[(staff, cell)]
                    ln = lines[staff]
                    sp = float(np.mean(np.diff(ln)))
                    fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
                    if not fc["passes"] or neg["passes"]:
                        print("skipped (frame control)", mv, c, fc, neg)
                        continue
                    pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
                    wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
                    wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
                    n += 1
                    bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp),
                            int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
                    for b in boxes:
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
                    manifest["tiles"].append({
                        "n": n, "file": name, "movement": mv, "cell": list(c),
                        "_cell": list(c), "measure": row["measure"], "part": row["part"],
                        "claimed_cause": tok, "tier": row["tier"], "marks": WANT[tok],
                        "our_reading": reading, "bar_quarters_in_force": T,
                        "residual_quarters_short_positive": row["residual"],
                        "frame_control": fc, "frame_control_negative": neg,
                        "page_box_600dpi": [wx0, wy0, wx1, wy1]})
                    used_pages.add((mv, page))
                    picked += 1
                    break
            print(tok, mv, "picked", picked)
    for t in manifest["tiles"]:
        t.pop("_cell", None)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
