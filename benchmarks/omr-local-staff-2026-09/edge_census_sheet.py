#!/usr/bin/env python3
"""lane-ledger-edge-census: contact sheet (tiles are real print crops cut from
the gather's own render at 600 dpi, 3x nearest-neighbour).

  red box        the detector's box for the subject head
  blue dotted    the staff's outer line (the edge the ledgers count from)
  orange         rungs the reader KEPT (the ladder derive_far_head_step got)
  magenta dashed rungs DROPPED, labelled with the dropping rule
  label          round-8 answer / undo answer / reference (staff half-steps
                 from the top line; negative = above, 8+ = below)

    python3 benchmarks/omr-local-staff-2026-09/edge_census_sheet.py \
        --json census.json --subjects a,b,c --out sheet.png [--pixel-check]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import edge_census as ec  # noqa: E402

SCALE = 3   # Litolff (15.8 px/sp); other docs scale to ~48 px/sp
RULE_LABEL = {
    "clears_box": "clears-box", "collapse_edges": "edge-collapse",
    "derive_pop": "edge-of-head pop", "exclusion_or_cascade": "other-head/acc excl.",
}


def _font(n=13):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, n)
        except Exception:
            pass
    return ImageFont.load_default()


def ink_fraction(gray, y, x_lo, x_hi):
    """fraction of columns in [x_lo, x_hi) that are dark (Otsu of the strip) at
    row y, taking the best of rows y-1..y+1."""
    h, w = gray.shape
    x_lo, x_hi = max(0, int(x_lo)), min(w, int(x_hi))
    best = 0.0
    strip = gray[max(0, int(y) - 12):int(y) + 13, x_lo:x_hi]
    thr = ec.lg._otsu_threshold(strip)
    for dy in (-1, 0, 1):
        yy = int(round(y)) + dy
        if 0 <= yy < h:
            best = max(best, float((gray[yy, x_lo:x_hi] <= thr).mean()))
    return best


def kept_rungs(row):
    """The ladder derive_far_head_step received, minus the rungs it popped
    (those are drawn magenta as 'edge-of-head pop')."""
    popped = [d["y"] for d in row["drops"] if d["rule"] == "derive_pop"]
    return [y for y in (row["final_ladder"] or [])
            if not any(abs(y - p) < 0.01 for p in popped)]


def tile(h, row, undo_pos, tag="", tile_w=330):
    SCALE = max(1, int(round(48.0 / row["spacing"])))
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    sp = row["spacing"]
    cx = (x0 + x1) / 2.0
    ys = [y0, y1, row["edge"]] + [d["y"] for d in row["drops"]
                                  if d["rule"] != "exclusion_or_cascade" or True]
    ys += list(row["final_ladder"] or [])
    lo = min(ys) - 0.9 * sp
    hi = max(ys) + 0.9 * sp
    half = 3.4 * sp
    cx0, cx1 = int(cx - half), int(cx + half)
    cy0, cy1 = int(lo), int(hi)
    crop = gray[cy0:cy1, cx0:cx1]
    im = Image.fromarray(crop).convert("RGB").resize(
        (crop.shape[1] * SCALE, crop.shape[0] * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(im)
    f = _font(12)

    def Y(y):
        return (y - cy0) * SCALE

    def X(x):
        return (x - cx0) * SCALE

    # staff edge, dotted blue
    for xx in range(0, im.width, 8):
        d.line([(xx, Y(row["edge"])), (xx + 3, Y(row["edge"]))], fill=(40, 90, 255), width=1)
    # kept rungs: orange
    for ry in kept_rungs(row):
        d.line([(X(cx - 1.1 * sp), Y(ry)), (X(cx + 1.1 * sp), Y(ry))],
               fill=(255, 140, 0), width=2)
    # dropped rungs: magenta dashed
    for k, dr in enumerate(row["drops"]):
        yy = Y(dr["y"])
        xa, xb = X(cx - 1.1 * sp), X(cx + 1.1 * sp)
        xx = xa
        while xx < xb:
            d.line([(xx, yy), (min(xx + 9, xb), yy)], fill=(230, 0, 200), width=2)
            xx += 15
        d.text((6, yy - 14 + 11 * (k % 2)), RULE_LABEL[dr["rule"]], fill=(230, 0, 200), font=f)
    # box
    d.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(255, 0, 0), width=2)
    # footer
    foot = Image.new("RGB", (im.width, 46), (255, 255, 255))
    fd = ImageDraw.Draw(foot)
    fd.text((4, 2), f"[{tag}] {row['subject']}", fill=(0, 0, 0), font=f)
    fd.text((4, 17), f"r8 {row['answer']}  undo {undo_pos}  ref {row['truth']}",
            fill=(0, 0, 0), font=f)
    out = Image.new("RGB", (max(im.width, tile_w), im.height + 46), (255, 255, 255))
    out.paste(im, (0, 0))
    out.paste(foot, (0, im.height))
    return out


def sheet(items, path, cols=4):
    tiles = [t for t in items]
    W = max(t.width for t in tiles)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    heights = [max(t.height for t in r) for r in rows]
    S = Image.new("RGB", (cols * (W + 6), sum(heights) + 6 * len(rows)), (235, 235, 235))
    y = 0
    for r, hh in zip(rows, heights):
        for i, t in enumerate(r):
            S.paste(t, (i * (W + 6), y))
        y += hh + 6
    S.save(path)


def _stub_fraction(gray, y, x0, x1, sp):
    """Ink fraction at row y (best of y-1..y+1) over the two STUB zones beside
    the head's box (0.1..1.1 sp out on each side) -- the head's own body is
    not in it, so only a printed stroke reaching past the head can read high."""
    zones = [(x0 - 1.1 * sp, x0 - 0.1 * sp), (x1 + 0.1 * sp, x1 + 1.1 * sp)]
    return max(ink_fraction(gray, y, lo, hi) for lo, hi in zones), \
        [round(ink_fraction(gray, y, lo, hi), 2) for lo, hi in zones]


def pixel_check(h, row):
    """For every line a tile draws: ink fraction in the stub zones beside the
    head (left, right) AT the line, against the same zones read 0.5 sp off the
    line (mean of above and below).  A control that can fail: a line that is
    not on a printed stroke reads as low as its shifted copy."""
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    sp = row["spacing"]

    def both(y):
        on_best, on_lr = _stub_fraction(gray, y, x0, x1, sp)
        offs = [_stub_fraction(gray, y + d * sp, x0, x1, sp)[0] for d in (-0.5, 0.5)]
        return on_best, on_lr, sum(offs) / 2.0

    out = dict(subject=row["subject"], lines=[])
    for ry in kept_rungs(row):
        out["lines"].append(("orange kept", ry) + both(ry))
    for dr in row["drops"]:
        out["lines"].append((f"magenta {dr['rule']}", dr["y"]) + both(dr["y"]))
    out["edge"] = both(row["edge"])
    return out


def main():
    a = sys.argv
    js = a[a.index("--json") + 1]
    out = a[a.index("--out") + 1]
    data = json.load(open(js))
    docs = list(data["rows"])
    heads = {d: {h["subject"]: h for h in ec.load_heads(d)} for d in docs}
    classes = data["classes"]
    picks = []   # (tag, subject, undo label)
    for sub, c in classes.items():
        if c["cls"] in ("E", "E?"):
            und = "/".join(str(u["pos"]) for u in c["edge_undos"] if u)
            picks.append((c["cls"], sub, und))
    for sub, c in classes.items():
        if c["cls"] == "right" and c["breaks"]:
            und = "/".join(sorted({str(b["pos"]) for b in c["breaks"]}))
            band = any(u and u["verdict"] != "right" for u in c["edge_undos"])
            picks.append(("BREAKS" + ("" if band else " (outside band)"), sub, und))
    order = {"E": 0, "E?": 1}
    picks.sort(key=lambda t: (order.get(t[0], 2), t[1]))
    tiles, checks = [], []
    for tag, sub, und in picks:
        for d in docs:
            for r in data["rows"][d]:
                if r["subject"] == sub:
                    tiles.append(tile(heads[d][sub], r, und, tag))
                    checks.append(pixel_check(heads[d][sub], r))
    sheet(tiles, out)
    print("wrote", out, len(tiles), "tiles")
    lines = ["stub-zone ink fraction (0.1..1.1 sp left/right of the box): ON the line [L,R] vs the same zones 0.5 sp OFF it"]
    for c in checks:
        e = c["edge"]
        lines.append(f"{c['subject']}: staff outer line on={e[0]:.2f} {e[1]} off={e[2]:.2f}")
        for name, y, on, lr, off in c["lines"]:
            lines.append(f"    {name:34} y={y:8.1f}  on {on:.2f} {lr}  off {off:.2f}")
    txt = "\n".join(lines)
    print(txt)
    Path(out).with_suffix(".pixel_check.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
