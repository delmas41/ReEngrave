"""ROADMAP 2.136 step 1 blind tiles: the top gate INSIDE `reconcile_duration` -- the
bar holds TWO narrowed events and lands only if BOTH take their unbeamed candidate.

    python3 .../tiles_2_136.py <h134-dump-dir> OUTDIR

Population: out/2.136/brah-gates.json rows with why == needs_two_or_more_events whose
two narrowed events are two single heads (35 Brahms bars). Each has candidates
eighth|quarter (or dotted eighth|dotted quarter) on BOTH heads and no eighth evidence,
so the rule's evidence filter leaves each head ONE admitted length (the unbeamed one),
and the bar lands exactly only when both heads take it. Sean has seen single-head bars
(2.134, 11/11); two-head bars he has NOT.

Tiles: 10 refused bars + 2 CONTROLS (two decided heads in one bar, the same cut), shuffled
with a fixed seed. Each tile: the bar at the gather's 600 dpi, 900 px wide, a big tile
number, RED corners = the bar (following the staff), BLUE corners = each note asked about.
NOTHING of ours is written on the image; the key is in manifest.json only.
Frame control (can fail): staff lines carry >= 2x the ink of the gaps AND the same test
shifted half a space fails; a failing tile is skipped for the next candidate.
Geometry (cell box, staff lines) is read once from the record via load_record.
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

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF = LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
REC = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261014-night.record.json"
HERE = Path(__file__).resolve().parent
GATES = HERE.parent / "out" / "2.136" / "brah-gates.json"
DUMP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
N_TILES, N_CONTROLS = 10, 2


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


def spread(items, k):
    """k items spread evenly over a list sorted by page."""
    if len(items) <= k:
        return list(items)
    step = len(items) / k
    return [items[int(i * step)] for i in range(k)]


def main():
    gates = json.load(open(GATES))
    held = json.load(open(DUMP / "brah-held.json"))
    by = {tuple(b["cell"]): b for b in held["bars"]}
    pop = [r for r in gates["rows"] if r.get("why") == "needs_two_or_more_events"
           and r["n_chord_units"] == 0 and r["n_narrowed"] == 2]
    # two pools by candidate pair, spread over the pages; extras for frame-control refusals
    plan = []
    for pair in ("[[0.5, 1], [1.0, 0]]", "[[0.75, 1], [1.5, 0]]"):
        pool = sorted([r for r in pop if str(r["narrowed_cands"][0][1]) == pair],
                      key=lambda r: tuple(r["cell"]))
        plan += [("refused_pair", r) for r in spread(pool, 9)]
    cand_cells = {tuple(r["cell"]) for _, r in plan}
    # controls: bars with two DECIDED single-head events, never a refused bar
    ctl = []
    for want_type, want_ev in (("quarter", "none_over_this_note"), ("eighth", "read")):
        found = []
        for b in held["bars"]:
            c = tuple(b["cell"])
            if b["n_streams"] != 1 or c in cand_cells or c[3] < 2 or b["kind"] != "held":
                continue
            evs = [e for e in b["streams"][0] if e["kind"] == "chord" and len(e["glyphs"]) == 1
                   and e["type"] == want_type and e["dots"] == 0 and e["page_px"][0]
                   and (e["dur"][0] or {}).get("outcome") == "decided"
                   and (e["dur"][0] or {}).get("reason") == "head_and_marks"
                   and (e["dur"][0] or {}).get("beam_evidence") == want_ev]
            if len(evs) >= 2:
                found.append((c, evs[:2], b))
        found.sort(key=lambda t: t[0])
        for pick in spread(found, 3)[1:2] + spread(found, 3)[2:3]:
            ctl.append((want_type, pick))
    # geometry: the record, once
    need_pages = {tuple(r["cell"])[:2] for _, r in plan} | {c[:2] for _, (c, _e, _b) in ctl}
    cells = {tuple(r["cell"]) for _, r in plan} | {c for _, (c, _e, _b) in ctl}
    geo = {}
    doc = load_record(REC)
    rec = doc["record"] if "record" in doc else doc
    for o in rec["observations"]:
        p = o["subject"].split("/")
        if len(p) > 3 and (int(p[1]), int(p[2])) in need_pages:
            if o["quantity"] == "cell_box" and p[0] == "cell" and len(p) > 4:
                k = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
                if k in cells:
                    geo[(k, "box")] = o["value"]
            elif o["quantity"] == "staff_lines" and p[0] == "staff":
                geo[((int(p[1]), int(p[2]), int(p[3])), "lines")] = o["value"]
            elif o["quantity"] == "glyph_box" and p[0] == "glyph" and len(p) > 5 \
                    and (int(p[1]), int(p[2]), int(p[3]), int(p[4])) in cells:
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    geo[(o["subject"], "px")] = bp
    del rec, doc
    gc.collect()

    items = []
    for _, r in plan:
        c = tuple(r["cell"])
        b = by[c]
        refs = {x["glyph"]: x for x in b["refused_in_cell"] if x["refusal"] == "duration_narrowed"}
        boxes, heads = [], []
        for gi, cands, reason, ev in r["narrowed_cands"]:
            g = f"glyph/{c[0]}/{c[1]}/{c[2]}/{c[3]}/{gi}"
            px = refs[g]["page_px"] if g in refs else geo.get((g, "px"))
            boxes.append(px)
            heads.append({"glyph": g, "candidates_beats_beamlevels": cands, "reason": reason,
                          "eighth_evidence": ev})
        items.append(("refused_pair", c, boxes, {
            "heads": heads, "bar_quarters": r["expected"], "sum_at_best_candidates": r["total"],
            "gate": r["gate"], "why": r["why"],
            "unique_joint_landing": "both heads take the UNBEAMED candidate "
                                    "(the only length either admits without eighth evidence)",
            "measure": r["part_row"]["measure"], "part": r["part_row"]["part"],
            "meter_reason": r.get("meter_reason")}))
    for typ, (c, evs, b) in ctl:
        items.append(("control_decided_pair", c, [e["page_px"][0] for e in evs], {
            "our_reading": [f"{e['type']} dots {e['dots']}" for e in evs],
            "what": f"two decided {typ}s"}))

    rnd = random.Random(2136)
    order = list(range(len(items)))
    rnd.shuffle(order)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
    except Exception:
        font = ImageFont.load_default()
    manifest = {"dpi": 600, "question": (
        "In the bar inside the RED corners, two notes stand inside BLUE corners. Reading left "
        "to right, what is the value of each: an eighth (beamed or flagged), a quarter, a "
        "dotted eighth, a dotted quarter, or something else? Say if you cannot tell."),
        "tiles": []}
    pages = {}
    n = n_ref = n_ctl = 0
    for i in order:
        role, c, boxes, key = items[i]
        if role == "refused_pair" and n_ref >= N_TILES:
            continue
        if role != "refused_pair" and n_ctl >= N_CONTROLS:
            continue
        page, system, staff, cell = c
        bx = geo.get((c, "box"))
        ln = geo.get(((page, system, staff), "lines"))
        if bx is None or ln is None or any(b is None for b in boxes):
            print("no geometry", c)
            continue
        if page not in pages:
            pages = {page: np.asarray(Image.fromarray(
                render_page(PDF, page, dpi=600).rgb).convert("RGB"))}
        img = pages[page].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        sp = float(np.mean(np.diff(ln)))
        fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
        if not fc["passes"] or neg["passes"]:
            print("frame control REFUSED", c, fc, neg)
            continue
        pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
        wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        n += 1
        n_ref += role == "refused_pair"
        n_ctl += role != "refused_pair"
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
        manifest["tiles"].append({
            "n": n, "file": name, "movement": "brah", "cell": list(c), "role": role,
            "key": key, "blue_boxes_left_to_right_px": sorted(
                [[round(v, 1) for v in b] for b in boxes]),
            "frame_control": fc, "frame_control_negative": neg,
            "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles:", n_ref, "refused,", n_ctl, "controls ->", OUT)


main()
