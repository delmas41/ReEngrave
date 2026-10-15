"""ROADMAP 2.126 blind tiles: the beam/flag cases after the fix, plus controls, one bar per tile.

    python3 benchmarks/omr-beam-confirm-2026-10/make_tiles_2_126.py ARM0.json ARM6.json OUTDIR

Reads the two small ARM records (Brahms 317803 pdf pages 0 and 6, gathered with the four 2.126 flags on) and cuts, from the print at 600 dpi:
  * one tile per case: the chord q86+q93 (one stem, one beam), the chord q110+q118, q1009 (one flag), and Brahms p6 sys0 staff11 cell5 bar 102;
  * three CONTROLS the flags do not touch: a beamed eighth the beam reader joined, a flagged eighth the tip reader counted, a plain quarter.
RED corners = the bar (following the staff). BLUE corners = the note(s) asked about. A big tile number. NOTHING of ours is drawn on the print;
the key (what the record says, which tile is a control) is written to tiles_2_126_MANIFEST_HIDDEN.json beside FINDINGS, which Sean never sees. Tiles are shuffled with a fixed
seed so the controls are not at the end. Frame control (can fail): the staff lines carry >= 2x the ink of the gaps AND the same test shifted
half a space fails; a tile that fails it is skipped.
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

PDF = "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
OUT = Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

CASES = [  # (name, page, system, staff, cell, [glyph subjects of the note(s)])
    ("q86+q93 chord (beam_certain_not_joined)", 0, 0, 0, 4, ["glyph/0/0/0/4/2", "glyph/0/0/0/4/9"]),
    ("q110+q118 chord (no stem found)", 0, 0, 0, 5, ["glyph/0/0/0/5/4", "glyph/0/0/0/5/12"]),
    ("q1009 (flag_ink_unread)", 0, 0, 9, 3, ["glyph/0/0/9/3/3"]),
    ("p6 sys0 staff11 cell5 bar 102 (flag missed)", 6, 0, 11, 5, ["glyph/6/0/11/5/0"]),
    # two notes the same flags CHANGED on page 6 that no one has judged: decided quarter at base, decided eighth with the flags on
    ("p6 sys0 staff10 cell5 (unjudged side effect: quarter -> eighth)", 6, 0, 10, 5, ["glyph/6/0/10/5/1"]),
    ("p6 sys0 staff9 cell4 (unjudged side effect: quarter -> eighth)", 6, 0, 9, 4, ["glyph/6/0/9/4/0"]),
]


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


def standing(verdicts):
    """{(subject, quantity): the live verdict} -- the last one no other verdict supersedes."""
    by = {}
    for v in verdicts:
        by.setdefault((v["subject"], v["quantity"]), []).append(v)
    out = {}
    for k, vs in by.items():
        sup = {x.get("supersedes") for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in sup] or vs
        out[k] = live[-1]
    return out


def load(path):
    doc = load_record(path)
    rec = doc["record"] if "record" in doc else doc
    st = standing(v for v in rec["verdicts"] if v["quantity"] in ("duration", "head_stem"))
    boxes, cell_box, lines = {}, {}, {}
    for o in rec["observations"]:
        sub = o["subject"]
        if o["quantity"] == "glyph_box":
            b = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(b, list) and len(b) == 4:
                boxes[sub] = [float(x) for x in b]
        elif o["quantity"] == "cell_box" and sub.startswith("cell/"):
            p = sub.split("/")
            cell_box[tuple(int(x) for x in p[1:5])] = o["value"]
        elif o["quantity"] == "staff_lines" and sub.startswith("staff/"):
            p = sub.split("/")
            lines[tuple(int(x) for x in p[1:4])] = o["value"]
    return st, boxes, cell_box, lines


def pick_controls(st, boxes, page, avoid_cells):
    """three decided durations the 2.126 flags do not touch: beamed (read), flagged (counted), plain quarter."""
    want = {"beamed eighth (beam read, joined)": [], "flagged eighth (hooks counted)": [], "plain quarter, no beam, no flag": []}
    for (sub, q), v in st.items():
        if q != "duration" or v["outcome"] != "decided" or not sub.startswith(f"glyph/{page}/") or sub not in boxes:
            continue
        p = sub.split("/")
        cell = tuple(int(x) for x in p[1:5])
        if cell in avoid_cells or int(p[4]) < 2:           # not the first bars of a system (clef / key crowd them)
            continue
        d, val = v.get("detail") or {}, v.get("value") or {}
        w = val.get("written")
        if d.get("head_is_open") or d.get("dots_attached"):
            continue
        hs = st.get((sub, "head_stem"))
        if hs is None or hs["outcome"] != "decided":
            continue
        if v.get("reason") == "head_and_marks" and d.get("beam_evidence") == "read" and w == 0.5 and d.get("beams_by_stem", 0) >= 1:
            want["beamed eighth (beam read, joined)"].append((cell, sub))
        elif v.get("reason") == "hooks_counted" and w == 0.5:
            want["flagged eighth (hooks counted)"].append((cell, sub))
        elif v.get("reason") == "head_and_marks" and d.get("beam_evidence") == "none_over_this_note" and w == 1.0 \
                and not d.get("yolo_beams") and not d.get("flags_attached") and d.get("stems_attached") == 1:
            want["plain quarter, no beam, no flag"].append((cell, sub))
    out = []
    for label, cands in want.items():
        cands.sort()
        if cands:
            out.append((label,) + cands[len(cands) // 2])
    return out


def main():
    arm0, arm6 = sys.argv[1], sys.argv[2]
    data = {0: load(arm0), 6: load(arm6)}
    plan = []
    used = set()
    for name, page, s, st_i, c, subs in CASES:
        stt, boxes, _cb, _ln = data[page]
        plan.append(("case", name, page, (page, s, st_i, c), [boxes[x] for x in subs],
                     {x: {k: stt[(x, "duration")].get(k) for k in ("outcome", "reason", "value")} for x in subs if (x, "duration") in stt}))
        used.add((page, s, st_i, c))
    for page in (0,):
        stt, boxes, _cb, _ln = data[page]
        for label, cell, sub in pick_controls(stt, boxes, page, used):
            plan.append(("control", label, page, cell, [boxes[sub]],
                         {sub: {k: stt[(sub, "duration")].get(k) for k in ("outcome", "reason", "value")}}))
            used.add(cell)
    order = list(range(len(plan)))
    random.Random(2126).shuffle(order)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
    except Exception:
        font = ImageFont.load_default()
    manifest = {"dpi": 600, "question": (
        "In the bar inside the RED corners, look at the note inside the BLUE corners (a chord is one stem and one value). What is its value: "
        "an eighth (beamed or flagged), a quarter, a dotted eighth, a dotted quarter, or something else? Say if you cannot tell."),
        "tiles": []}
    pages = {}
    n = 0
    for i in order:
        role, name, page, cell, boxes, key = plan[i]
        _st, _b, cell_box, lines = data[page]
        bx = cell_box.get(cell)
        ln = lines.get(cell[:3])
        if bx is None or ln is None:
            print("no geometry", name, cell)
            continue
        if page not in pages:
            pages[page] = np.asarray(Image.fromarray(render_page(PDF, page, dpi=600).rgb).convert("RGB"))
        img = pages[page].copy()
        ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
        sp = float(np.mean(np.diff(ln)))
        fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
        if not fc["passes"] or neg["passes"]:
            print("frame control REFUSED", name, fc, neg)
            continue
        pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
        wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
        wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
        # the note may stand far above or below the staff on ledger lines: the window always holds the blue box with 2 spaces to spare
        wy0 = min(wy0, int(min(b[1] for b in boxes) - 2.0 * sp))
        wy1 = max(wy1, int(max(b[3] for b in boxes) + 2.0 * sp))
        n += 1
        bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp), int(bx[2]) - 6, int(ln[-1] + 1.3 * sp), (220, 0, 0))
        ux0, uy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        ux1, uy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        bracket(img, int(ux0) - 8, int(uy0) - 8, int(ux1) + 8, int(uy1) + 8, (0, 70, 230), arm=18, thick=5)
        crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
        crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
        tile = Image.new("RGB", (900, 150 + crop.height), (255, 255, 255))
        ImageDraw.Draw(tile).text((20, 12), f"Tile {n}", fill=(0, 0, 0), font=font)
        tile.paste(crop, (0, 150))
        fn = f"tile_{n:02d}.png"
        tile.save(OUT / fn)
        manifest["tiles"].append({"n": n, "file": fn, "role": role, "what": name, "page": page, "cell": list(cell), "record_says": key,
                                  "frame_control": fc, "frame_control_negative": neg, "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    # the key lives beside FINDINGS, never in the gallery Sean opens
    Path("benchmarks/omr-beam-confirm-2026-10/tiles_2_126_MANIFEST_HIDDEN.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
