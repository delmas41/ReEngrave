"""ROADMAP 2.136 step 2 blind tiles: bars `OMR_INFER_CARRIED_METER_FIX` settles that Sean has NOT seen.

    python3 tiles_step2_2_136.py STEP2_OUT_DIR TILES_DIR KEY_JSON

Reads STEP2_OUT_DIR/{lit,brah}.json (from step2_2_136.py), picks bars that only the fix settles
(INFER's rule declined them with the flag OFF), excludes every cell already in
out/print/2.136-review/manifest.json, cuts the 2.134/2.136 tile (600 dpi, 900 px, big tile number,
RED corners = the bar, BLUE corners = each note asked about, NOTHING of ours drawn) and writes the
hidden KEY (what the fix settled each note to, which fault freed the bar, the controls' readings) to
KEY_JSON in the benchmark folder, NOT beside the tiles. Frame control as in 2.136 (staff lines carry
>= 2x the ink of the gaps AND the half-space-shifted test fails); a failing tile is skipped for the
next candidate. Geometry is read once per movement from the record via load_record.
"""
import gc
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
DOCS = {
    "brah": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
             LIB + "_shared-records/brahms1-breitkopf-mvt1-whole-20261014-night.record.json"),
    "lit": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
            LIB + "_shared-records/beethoven5-litolff-mvt1-whole-20261014-night.record.json"),
}
STEP2, OUT, KEY = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
SEEN = {tuple(t["cell"]) for t in json.load(open("out/print/2.136-review/manifest.json"))["tiles"]}
PLAN = {"brah": {"W1": 4, "W2": 3}, "lit": {"any": 3}}
SPARE = 3          # extra candidates per slot for frame-control refusals


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


def spread(items, k):
    if len(items) <= k:
        return list(items)
    step = len(items) / k
    return [items[int(i * step)] for i in range(k)]


def cause(was_declined):
    return {"meter_not_from_the_print": "W1", "heads_not_this_staffs_own": "W2"}.get(was_declined, "other")


def candidates_for(label):
    d = json.load(open(STEP2 / f"{label}.json"))
    off = {tuple(r["cell"]): r for r in d["rows"] if r["flag"] == "0"}
    out = []
    for a in d["added"]:
        c = tuple(a["cell"])
        if "new" not in a or not a["fully_released"] or c in SEEN or not (1 <= len(a["new"]) <= 3):
            continue
        out.append({"cell": c, "new": a["new"], "cause": cause(a["was_declined"]),
                    "was_declined": a["was_declined"]})
    out.sort(key=lambda r: r["cell"])
    return out


def pick(label):
    pool = candidates_for(label)
    chosen = []
    for kind, k in PLAN[label].items():
        sub = [r for r in pool if kind == "any" or r["cause"] == kind]
        chosen += [(kind, r) for r in spread(sub, k + SPARE)]
    return chosen


def read_geometry(label, cells, ctl_wanted):
    """cell_box, staff_lines, glyph boxes for `cells`; and (if asked) decided-pair control bars."""
    doc = load_record(DOCS[label][1])
    rec = doc["record"] if "record" in doc else doc
    geo = {}
    need = {c for c in cells}
    for o in rec["observations"]:
        p = o["subject"].split("/")
        if len(p) < 4:
            continue
        if o["quantity"] == "cell_box" and p[0] == "cell" and len(p) > 4:
            k = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
            if k in need:
                geo[(k, "box")] = o["value"]
        elif o["quantity"] == "staff_lines" and p[0] == "staff":
            geo[((int(p[1]), int(p[2]), int(p[3])), "lines")] = o["value"]
        elif o["quantity"] == "glyph_box" and p[0] == "glyph" and len(p) > 5 \
                and (int(p[1]), int(p[2]), int(p[3]), int(p[4])) in need:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                geo[(o["subject"], "px")] = bp
    ctl = []
    if ctl_wanted:
        by_cell, sup = {}, set()
        for v in rec["verdicts"]:
            if v["quantity"] != "duration":
                continue
            if v.get("supersedes"):
                sup.add(v["supersedes"])
            p = v["subject"].split("/")
            by_cell.setdefault((int(p[1]), int(p[2]), int(p[3]), int(p[4])), []).append(v)
        for c, vs in sorted(by_cell.items()):
            allv = [v for v in vs if v["id"] not in sup]
            # the bar may hold decided rests, nothing narrowed; exactly two decided NOTES
            if c in SEEN or c[3] < 2 or any(v["outcome"] != "decided" for v in allv):
                continue
            live = [v for v in allv if isinstance(v["value"], dict) and not v["value"].get("is_rest")]
            if len(live) != 2 or not all(v["decider"] == "adjudicate_duration" for v in live):
                continue
            b = [(v["value"].get("beats"), v["value"].get("beam_levels"), v["value"].get("dots"))
                 for v in live]
            if b[0] == b[1] and b[0][2] in (0, None) and b[0][0] in (0.5, 1.0):
                ctl.append({"cell": c, "glyphs": [v["subject"] for v in live],
                            "reading": b[0], "kind": "eighths" if b[0][0] == 0.5 else "quarters"})
        for c in {x["cell"] for x in ctl}:
            need.add(c)
        for o in rec["observations"]:
            p = o["subject"].split("/")
            if len(p) < 4:
                continue
            k = (int(p[1]), int(p[2]), int(p[3]), int(p[4])) if len(p) > 4 else None
            if k in need and o["quantity"] == "cell_box" and p[0] == "cell":
                geo[(k, "box")] = o["value"]
            elif k in {x["cell"] for x in ctl} and o["quantity"] == "glyph_box" and p[0] == "glyph":
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    geo[(o["subject"], "px")] = bp
    del rec, doc
    gc.collect()
    return geo, ctl


def main():
    items = []                     # (movement, role, cell, boxes, key)
    geos, ctls = {}, {}
    for label in ("brah", "lit"):
        chosen = pick(label)
        geos[label], ctls[label] = read_geometry(label, {r["cell"] for _, r in chosen}, label == "brah")
        for kind, r in chosen:
            boxes = []
            for g in r["new"]:
                k = g.split("/")
                px = geos[label].get((g, "px"))
                boxes.append(px)
            items.append((label, "settled_bar", r["cell"], boxes, {
                "slot": kind, "cause_freed_by": r["cause"], "was_declined_flag_off": r["was_declined"],
                "settled_to_beats_beamlevels": r["new"]}))
    # controls: one two-eighths and one two-quarters decided bar (Brahms), spread
    for kind in ("eighths", "quarters"):
        pool = [c for c in ctls["brah"] if c["kind"] == kind]
        print("control pool", kind, len(pool))
        for c in (spread(pool, 4)[1:3] or spread(pool, 4)[:1]):
            boxes = [geos["brah"].get((g, "px")) for g in c["glyphs"]]
            items.append(("brah", "control_decided_pair", c["cell"], boxes, {
                "our_reading_beats_beamlevels_dots": c["reading"], "what": f"two decided {kind}"}))

    rnd = random.Random(21362)
    order = list(range(len(items)))
    rnd.shuffle(order)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
    except Exception:
        font = ImageFont.load_default()
    quota = {"brah_W1": 4, "brah_W2": 3, "lit_any": 3, "control": 2}
    controls_seen = {"eighths": 0, "quarters": 0}
    used = {k: 0 for k in quota}
    public = {"dpi": 600, "question": (
        "In the bar inside the RED corners, the notes inside the BLUE corners: reading left to right, "
        "what is the value of each: an eighth (beamed or flagged), a sixteenth, a quarter, a dotted eighth, "
        "a dotted quarter, or something else? Say if you cannot tell."), "tiles": []}
    key = {"question_note": "hidden key; Sean's tiles carry no key", "tiles": []}
    pages = {}
    n = 0
    for i in order:
        label, role, c, boxes, k = items[i]
        slot = ("control" if role != "settled_bar"
                else f"{label}_{k['slot']}")
        if used.get(slot, 0) >= quota[slot]:
            continue
        if role != "settled_bar":
            if controls_seen[k["what"].split()[-1]] >= 1:
                continue
        page, system, staff, cell = c
        bx = geos[label].get((c, "box"))
        ln = geos[label].get(((page, system, staff), "lines"))
        if bx is None or ln is None or any(b is None for b in boxes):
            print("no geometry", label, c)
            continue
        if (label, page) not in pages:
            pages = {(label, page): np.asarray(Image.fromarray(
                render_page(DOCS[label][0], page, dpi=600).rgb).convert("RGB"))}
        img = pages[(label, page)].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        sp = float(np.mean(np.diff(ln)))
        fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
        if not fc["passes"] or neg["passes"]:
            print("frame control REFUSED", label, c, fc, neg)
            continue
        used[slot] += 1
        if role != "settled_bar":
            controls_seen[k["what"].split()[-1]] += 1
        n += 1
        pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
        wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp), int(bx[2]) - 6,
                int(ln[-1] + 1.3 * sp), (220, 0, 0))
        for b in boxes:
            bracket(img, int(b[0]) - 8, int(b[1]) - 8, int(b[2]) + 8, int(b[3]) + 8,
                    (0, 70, 230), arm=18, thick=5)
        crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
        crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
        tile = Image.new("RGB", (900, 150 + crop.height), (255, 255, 255))
        ImageDraw.Draw(tile).text((20, 12), f"Tile {n}", fill=(0, 0, 0), font=font)
        tile.paste(crop, (0, 150))
        name = f"tile_{n:02d}.png"
        tile.save(OUT / name)
        public["tiles"].append({"n": n, "file": name, "blue_notes": len(boxes)})
        key["tiles"].append({
            "n": n, "file": name, "movement": label, "cell": list(c), "role": role, "key": k,
            "blue_boxes_px": [[round(v, 1) for v in b] for b in boxes],
            "frame_control": fc, "frame_control_negative": neg,
            "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(public, indent=1))
    KEY.write_text(json.dumps(key, indent=1, default=str))
    print("wrote", n, "tiles;", used, "->", OUT, "key", KEY)


main()
