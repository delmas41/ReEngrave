"""ROADMAP 2.134 blind tiles: the top single-NOTE cause of a held bar, one bar per tile.

    python3 .../tiles_2_134.py <dump-dir> OUTDIR

Top cause (probe/dissect_2_134.py): ONE head, narrowed by the duration reader
(`Q.DURATION` narrowed, reason `beam_discounted_uncertain`: eighth-or-quarter, with
a dot or without), whose own two candidates land the bar. 11 such bars + 3 CONTROLS:
a head the record DECIDED (a beamed eighth, a plain quarter, a dotted quarter) cut
the same way, so Sean's reading of the tiles can fail us.

Geometry (cell box, staff lines) is read from the records once each (load_record,
serially) and the record is dropped before the next; nothing is re-decided.
Each tile: the bar at the gather's 600 dpi, 900 px wide, a big tile number, RED
corners = the bar (following the staff), BLUE corners = the note asked about.
NOTHING of ours is written on the image; the key is in manifest.json only
(tiles are shuffled with a fixed seed so controls are not at the end).
Frame control (can fail): staff lines carry >= 2x the ink of the gaps AND the same
test shifted half a space fails; a failing tile is skipped for the next candidate.
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
PDFS = {
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
SH = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
RECS = {"brah": SH + "brahms1-breitkopf-mvt1-whole-20261014-night.record.json",
        "lit": SH + "beethoven5-litolff-mvt1-whole-20261014-night.record.json"}
DUMP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# Brahms one-head cases chosen to spread pages and the two candidate pairs
# (eighth|quarter and dotted eighth|dotted quarter) and one other reason.
BRAH_N = [(16, 0, 0, 11), (21, 0, 1, 5), (5, 1, 2, 6), (19, 1, 4, 1),
          (17, 0, 6, 5), (26, 1, 8, 4), (14, 1, 7, 0), (9, 0, 11, 0),
          (12, 0, 5, 0), (5, 0, 10, 2), (15, 0, 9, 3), (6, 0, 11, 5)]   # extras: frame control refuses some


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


def pick_controls(mv, held, used):
    """-> list of (kind label, bar, event, glyph page_px) from DECIDED single heads."""
    want = {"brah": [("eighth", 0, "read", "a beamed eighth the beam reader READ"),
                     ("quarter", 1, "none_over_this_note", "a dotted quarter, no beam over it")],
            "lit": [("quarter", 0, "none_over_this_note", "a plain quarter, no beam over it")]}[mv]
    out = []
    pool = [b for b in held["bars"] if b["n_streams"] == 1 and b["kind"] == "held"
            and tuple(b["cell"]) not in used and b["cell"][3] >= 2]   # not a system-start bar (clef/key crowd it)
    for typ, dots, ev, label in want:
        cands = []
        for b in pool:
            for e in b["streams"][0]:
                d = (e.get("dur") or [None])[0]
                if (e["kind"] == "chord" and len(e["glyphs"]) == 1 and e["type"] == typ
                        and e["dots"] == dots and d and d["outcome"] == "decided"
                        and d["reason"] == "head_and_marks" and d["beam_evidence"] == ev
                        and e["page_px"][0]):
                    cands.append((tuple(b["cell"]), b, e))
        cands.sort(key=lambda t: t[0])
        out += [(label,) + cands[len(cands) // 2]] if cands else []
        if cands:
            used.add(cands[len(cands) // 2][0])
    return out


def main():
    plan = []                      # (movement, cell, role, boxes, key-text, answer-key)
    data = {}
    for mv in ("lit", "brah"):
        held = json.load(open(DUMP / f"{mv}-held.json"))
        for b in held["bars"]:
            b["kind"] = "held"
        part = json.load(open(DUMP / f"{mv}-held-part.json"))
        data[mv] = (held, {tuple(r["cell"]): r for r in part["rows"]})
    used = set()
    for mv in ("lit", "brah"):
        held, rows = data[mv]
        by = {tuple(b["cell"]): b for b in held["bars"]}
        if mv == "lit":
            cells = [c for c, r in sorted(rows.items())
                     if r["cause"] == "N" and r["tier"] == "evidenced"
                     and sum(1 for x in by[c]["refused_in_cell"]
                             if x["refusal"] == "duration_narrowed") == 1]
        else:
            cells = [(c[0], c[1], c[2], c[3]) for c in BRAH_N]
            cells = [next(k for k in by if k[0] == c[0] and k[1] == c[1] and k[2] == c[2]
                          and k[3] == c[3]) for c in cells]
        for c in cells:
            b = by[c]
            r = [x for x in b["refused_in_cell"] if x["refusal"] == "duration_narrowed"][0]
            cd = [(k["value"]["beats"], k["value"]["beam_levels"])
                  for k in r["duration"]["candidates"]]
            plan.append((mv, c, "narrowed_head", [r["page_px"]],
                         {"reason": r["duration"]["reason"], "candidates_beats_beamlevels": cd,
                          "bar_quarters": rows[c]["T"], "short_by": rows[c]["residual"],
                          "measure": rows[c]["measure"], "part": rows[c]["part"],
                          "system_meter": (b["system_meter"] or {}).get("outcome")}))
            used.add(c)
        for label, c, b, e in pick_controls(mv, held, used):
            plan.append((mv, c, "control_decided_head", [e["page_px"][0]],
                         {"what": label, "our_reading": f"{e['type']} dots {e['dots']}",
                          "measure": (b.get("report") or {}).get("measure"),
                          "part": (b.get("report") or {}).get("part")}))
    # geometry: one record at a time
    geo = {}
    for mv in ("lit", "brah"):
        need = {(c[0], c[1]): set() for m, c, *_ in plan if m == mv}
        cells = {c for m, c, *_ in plan if m == mv}
        rec_doc = load_record(RECS[mv])
        rec = rec_doc["record"] if "record" in rec_doc else rec_doc
        for o in rec["observations"]:
            p = o["subject"].split("/")
            if len(p) > 3 and (int(p[1]), int(p[2])) in need:
                if o["quantity"] == "cell_box" and p[0] == "cell" and len(p) > 4:
                    k = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
                    if k in cells:
                        geo[(mv, k, "box")] = o["value"]
                elif o["quantity"] == "staff_lines" and p[0] == "staff":
                    geo[(mv, (int(p[1]), int(p[2]), int(p[3])), "lines")] = o["value"]
        del rec, rec_doc
        gc.collect()
    rnd = random.Random(2134)
    order = list(range(len(plan)))
    rnd.shuffle(order)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
    except Exception:
        font = ImageFont.load_default()
    manifest = {"dpi": 600, "question": (
        "In the bar inside the RED corners, look at the note inside the BLUE corners. "
        "What is its value: an eighth (beamed or flagged), a quarter, a dotted eighth, "
        "a dotted quarter, or something else? Say if you cannot tell."), "tiles": []}
    pages = {}
    n = 0
    n_narrowed = 0
    for i in order:
        mv, c, role, boxes, key = plan[i]
        if role == "narrowed_head" and n_narrowed >= 11:
            continue
        page, system, staff, cell = c
        bx = geo.get((mv, c, "box"))
        ln = geo.get((mv, (page, system, staff), "lines"))
        if bx is None or ln is None:
            print("no geometry", mv, c)
            continue
        if (mv, page) not in pages:
            pages = {k: v for k, v in pages.items() if k[0] == mv}
            pages[(mv, page)] = np.asarray(Image.fromarray(
                render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
        img = pages[(mv, page)].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        sp = float(np.mean(np.diff(ln)))
        fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
        if not fc["passes"] or neg["passes"]:
            print("frame control REFUSED", mv, c, fc, neg)
            continue
        pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
        wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        n += 1
        n_narrowed += role == "narrowed_head"
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
        manifest["tiles"].append({"n": n, "file": name, "movement": mv, "cell": list(c),
                                  "role": role, "key": key, "frame_control": fc,
                                  "frame_control_negative": neg,
                                  "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
