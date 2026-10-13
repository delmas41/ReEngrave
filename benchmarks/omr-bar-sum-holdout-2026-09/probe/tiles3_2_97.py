"""ROADMAP 2.97 blind tiles: bars the arm newly settled, one bar per tile.

   python3 tiles_2_97.py OUTDIR lit=ARM.pkl [brah=ARM.pkl ...]

Per tile: the bar (RED corners, following the staff), the settled heads
(BLUE corners), a big number on a banner, nothing of ours on the image. The
question is one line: "values of the bracketed notes?" Our values (and which
part -- single / chord / columns -- produced them) are in manifest.json ONLY;
answers.template.json is for Sean's reply. Frame control as 2.96's: the five
staff lines must carry >= 2x the ink of the gaps AND the same test shifted
half a space must FAIL, else the candidate is skipped.
"""
import collections
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
import os  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Outcome, Q, Subject  # noqa: E402

NEWHELD = json.load(open(os.environ['NEWHELD'])) if os.environ.get('NEWHELD') else {}
ONLY = [tuple(int(x) for x in k.split('/')) for k in os.environ.get('ONLY_BARS', '').split(',') if k]

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
LOGS = dict(a.split("=", 1) for a in sys.argv[2:])
PLAN = [("eighth", 6), ("newheld", 4)]


def part_of(v):
    if v.decider == "reconcile_duration":
        if (v.detail or {}).get("chord_of"):
            return "chord"
        if (v.detail or {}).get("settled_alongside"):
            return "single"          # 'alongside' settles a narrowed head
        return None
    if v.decider == "infer:collapse_narrowed_by_bar":
        if (v.detail or {}).get("bar_unknown_events", 1) >= 2:
            return "columns"
        return "single"
    return None


def bars_of(log, mv=None):
    """{bar: (part, [heads])}: 'eighth' = a surviving settlement to an
    eighth-or-shorter (cites eighth_evidence); 'newheld' = a narrowed head
    that BASE had settled to an eighth by the old single rule (bars the arm
    newly holds; picked in the NEWHELD json)."""
    out = {}
    for v in list(log._vrd.values()):
        cur = log.verdict(Q.DURATION, v.subject)
        if cur is None or cur.id != v.id:
            continue
        s = v.subject
        key = (s.page, s.system, s.staff, s.cell)
        if v.outcome is Outcome.DECIDED and part_of(v) is not None \
                and int((v.value or {}).get("beam_levels") or 0) > 0:
            out.setdefault(key, ["eighth", []])[1].append((s, v, log._vrd.get(v.supersedes)))
        elif v.outcome is Outcome.NARROWED and mv and "/".join(map(str, key)) in NEWHELD.get(mv, {}) \
                and v.reason == "beam_discounted_uncertain":
            out.setdefault(key, ["newheld", []])[1].append((s, v, v))
    return out


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


def main():
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    except Exception:
        font = ImageFont.load_default()
    pool = collections.defaultdict(list)       # part -> [(mv, key, heads, log)]
    logs = {}
    for mv, path in LOGS.items():
        logs[mv] = pickle.load(open(path, "rb"))
        for key, (p, heads) in sorted(bars_of(logs[mv], mv).items()):
            if not ONLY or key in ONLY:
                pool[p].append((mv, key, heads))
    print({p: len(v) for p, v in pool.items()})
    manifest = {"question": "Values of the bracketed notes? (e.g. 4 / 8 / 16, Dot 4 = dotted quarter)",
                "tiles": []}
    pages = {}
    n = 0
    for part, want in PLAN:
        c = pool.get(part, [])
        picked = 0
        # spread over the list and over the movements
        order = [c[int((i + 0.5) * len(c) / max(len(c), 1))] for i in range(len(c))] if c else []
        order = sorted(range(len(c)), key=lambda i: (i * 7919) % max(len(c), 1))
        used_mv = collections.Counter()
        for i in order:
            if picked >= want:
                break
            mv, key, heads = c[i]
            if False:
                continue
            log = logs[mv]
            page, system, staff, cell = key
            from tools.omr.staged import consequences as C2
            if not ONLY:
                nts = [q for q in C2._standing(log, R.cell(page, system, staff, cell), Q.DURATION)
                       if q.outcome in (Outcome.DECIDED, Outcome.NARROWED)
                       and C2._left_the_bar(log, q.subject) is None]
                if not C2._bar_heads_are_clean(log, R.cell(page, system, staff, cell), nts):
                    continue
            cb = log.rows(Q.CELL_BOX, R.cell(page, system, staff, cell))
            sl = log.rows(Q.STAFF_LINES, R.staff(page, system, staff))
            if not cb or not sl:
                continue
            bx, ln = cb[-1].value, sl[-1].value
            # ONE bracket per settled EVENT: the union of its heads' boxes
            # (a head boxed twice, or a chord's heads, is one mark to read).
            from tools.omr.staged import record as R2
            ev = log.verdict(Q.EVENT, R2.cell(page, system, staff, cell))
            ev_of = {}
            for k, e in enumerate((ev.value or {}).get("events", ()) if ev else ()):
                for g in e.get("glyphs", ()):
                    ev_of[g] = k
            groups = collections.defaultdict(list)
            for s, v, old in heads:
                rows = log.rows(Q.GLYPH_BOX, s)
                b = (rows[-1].detail or {}).get("bbox_page_px") if rows else None
                if b:
                    groups[ev_of.get(s.glyph, -1 - s.glyph)].append([float(x) for x in b])
            boxes = [[min(b[0] for b in g), min(b[1] for b in g),
                      max(b[2] for b in g), max(b[3] for b in g)] for g in groups.values()]
            if not boxes:
                continue
            if (mv, page) not in pages:
                pages[(mv, page)] = np.asarray(Image.fromarray(
                    render_page(PDFS[mv], page, dpi=600).rgb).convert("RGB"))
            img = pages[(mv, page)].copy()
            ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
            fc, neg = frame_control(ink, bx, ln), frame_control(ink, bx, ln, 0.5)
            if not fc["passes"] or neg["passes"]:
                print("skipped (frame control)", mv, key, fc, neg)
                continue
            sp = float(np.mean(np.diff(ln)))
            pad = int(max(2.5 * sp, (14 * sp - (bx[2] - bx[0])) / 2))
            wx0, wx1 = int(bx[0]) - pad, int(bx[2]) + pad
            wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
            n += 1
            bracket(img, int(bx[0]) + 6, int(ln[0] - 1.3 * sp), int(bx[2]) - 6,
                    int(ln[-1] + 1.3 * sp), (220, 0, 0))
            for b in boxes:
                bracket(img, int(b[0]) - 6, int(b[1]) - 6, int(b[2]) + 6,
                        int(b[3]) + 6, (0, 70, 230), arm=18, thick=5)
            crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
            crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))),
                               Image.LANCZOS)
            tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
            ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
            tile.paste(crop, (0, 130))
            tile.save(OUT / f"tile_{n:02d}.png")
            manifest["tiles"].append({
                "n": n, "file": f"tile_{n:02d}.png", "movement": mv,
                "bar": list(key), "part": part,
                "settled": [{"subject": s.to_key(), "ours": (v.value or {}).get("beats") if v.value else "narrowed in the arm; base wrote an eighth",
                             "was_candidates": [x.value.get("beats") for x in (old.candidates if old else [])
                                                if isinstance(x.value, dict)],
                             "decider": v.decider} for s, v, old in heads],
                "frame_control": fc, "frame_control_negative": neg})
            used_mv[mv] += 1
            picked += 1
        print(part, "picked", picked)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (OUT / "answers.template.json").write_text(json.dumps(
        {str(t["n"]): "" for t in manifest["tiles"]}, indent=1))
    print("wrote", len(manifest["tiles"]), "tiles to", OUT)


main()
