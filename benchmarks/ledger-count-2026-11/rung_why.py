"""ROADMAP 2.312 Part 1 step 1 -- for a seeded 30 real far heads whose ledger finder saw no line (`no_rungs`, `no_line_at_the_note_box`): is a line printed, and what does the finder return on the raw ink?

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/rung_why.py HEADS.json OUTDIR [N=30] [SEED=2312]

For each case: the page ink (grey, as scanned) at large scale with the staff lines and one thin box; and, from the SAME ledger finder the reader uses
(`ledger_grid.measure_ledger_rungs`) called on the page ink at the head's x with no other head's box removed: the rung rows it finds on the head's side, and
`rows`: per row between the staff edge and the head's far edge, the longest dark run through the box's column and how far it runs past the box left / right (in spaces).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.omr.annotate import ledger_grid as lg
from checksheet import page_image
from ledger_heights import load


def real_refused(h):
    g = int(round(h["geom"]))
    far = g <= -2 or g >= 10
    reason = ((h.get("ledger_refusal") or {}).get("detail") or {}).get("ledger_reason", "?").split(" (")[0]
    nan = h.get("not_a_note")
    moved = ((h.get("pitch") or {}).get("reason") or "") in ("reowned", "reowned_by_ledger_reading")
    return far and h["ledger_row"] is None and reason in ("no_rungs", "no_line_at_the_note_box") and not moved and not (nan and nan[1] is True)


def runs_past_box(gray, y, box, sp):
    """dark run through row y in the box's column band: (left reach, right reach) past the box in spaces."""
    thr = 128
    row = gray[int(y) - 1:int(y) + 2, :].min(axis=0) < thr
    x0, x1 = int(box[0]), int(box[2])
    cx = (x0 + x1) // 2
    if not row[cx]:
        # nearest dark column inside the box
        inside = [c for c in range(x0, x1) if row[c]]
        if not inside:
            return None
        cx = inside[len(inside) // 2]
    lo = cx
    while lo > 0 and row[lo - 1]:
        lo -= 1
    hi = cx
    while hi + 1 < row.size and row[hi + 1]:
        hi += 1
    return round((x0 - lo) / sp, 2), round((hi + 1 - x1) / sp, 2)


def main(heads_json, outdir, n=30, seed=2312):
    heads = json.load(open(heads_json))
    pool = sorted((h for h in heads if real_refused(h)), key=lambda h: h["key"])
    print("real heads, no line found:", len(pool), "(no_rungs %d, no_line_at_the_note_box %d)" % (
        sum(1 for h in pool if ((h["ledger_refusal"]["detail"]).get("ledger_reason", "")).startswith("no_rungs")),
        sum(1 for h in pool if ((h["ledger_refusal"]["detail"]).get("ledger_reason", "")).startswith("no_line"))))
    pick = random.Random(seed).sample(pool, min(n, len(pool)))
    sl = load("litolff")[0]["staff_lines"]
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles, out = [], []
    for i, h in enumerate(pick, 1):
        p, s, st, c, g = (int(x) for x in h["key"].split("/")[1:])
        ys = sl["staff/%d/%d/%d" % (p, s, st)]["value"]
        sp = (ys[4] - ys[0]) / 4.0
        b = h["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        img = page_image("litolff", p)
        gray = np.array(img.convert("L"))
        above = cy < ys[0]
        edge = ys[0] if above else ys[4]
        found = lg.measure_ledger_rungs(gray, [float(v) for v in ys], cx, head_y=cy, head_box_x=(b[0], b[2]),
                                        collapse_edges_box=tuple(b)).get("above" if above else "below", [])
        rows = []
        lo, hi = (int(cy - 0.8 * sp), int(edge - 0.5 * sp)) if above else (int(edge + 0.5 * sp), int(cy + 0.8 * sp))
        for y in range(min(lo, hi), max(lo, hi), max(1, int(sp / 8))):
            r = runs_past_box(gray, y, b, sp)
            if r and (r[0] > 0.15 or r[1] > 0.15):
                rows.append((round((y - edge) / sp, 2), r))
        reason = h["ledger_refusal"]["detail"].get("ledger_reason", "?")
        out.append(dict(i=i, key=h["key"], reason=reason, side="above" if above else "below",
                        rungs_found_raw_ink=[round((float(y) - edge) / sp, 2) for y in found],
                        rows_with_ink_past_box=rows[:12], head_offset_sp=round((cy - edge) / sp, 2)))
        # tile: page ink, staff lines drawn thin red, thin box
        W = 520
        k = 46.0 / sp
        half = (W / k) / 2
        up, dn = (7.5, 3.5) if above else (3.5, 7.5)
        x0, x1 = int(cx - half), int(cx + half)
        y0, y1 = int(cy - up * sp), int(cy + dn * sp)
        crop = img.crop((x0, y0, x1, y1)).convert("RGB")
        d = ImageDraw.Draw(crop)
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
        crop = crop.resize((W, int(crop.height * k)))
        t = Image.new("RGB", (W, crop.height + 16), "white")
        t.paste(crop, (0, 0))
        ImageDraw.Draw(t).text((4, crop.height + 2), "%d %s %s" % (i, h["key"][6:], reason.split(" (")[0]), fill=(0, 0, 0))
        tiles.append(t)
    for si in range(0, len(tiles), 9):
        grp = tiles[si:si + 9]
        cols = 3
        rows_n = (len(grp) + cols - 1) // cols
        hh = max(t.height for t in grp)
        sh = Image.new("RGB", (cols * 526 + 6, rows_n * (hh + 6) + 6), "white")
        for j, t in enumerate(grp):
            sh.paste(t, (6 + (j % cols) * 526, 6 + (j // cols) * (hh + 6)))
        sh.save(outdir / ("why_%d.png" % (si // 9 + 1)))
    json.dump(out, open(outdir / "why.json", "w"), indent=1)
    for o in out:
        print(o["i"], o["key"], o["side"], o["reason"][:28], "head", o["head_offset_sp"], "rungs(raw)", o["rungs_found_raw_ink"], "rows", o["rows_with_ink_past_box"][:4])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:5]))
