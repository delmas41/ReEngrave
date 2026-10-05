#!/usr/bin/env python3
"""lane-ledger-edge-fix: contact sheet of every head the fix CHANGES.

One row per changed head, three tiles: BEFORE (default reader), AFTER
(Part 1 + Part 2), REFERENCE (the print only, with the reference pitch's
nominal head position and ledger count marked in the margin). Tiles are real
print crops cut from the gather's own render (600 dpi), scaled x3 or more
(nearest neighbour).

  red box          the detector's box for the subject head
  blue dotted      the staff's outer line (where the ledgers count from)
  orange           ledgers COUNTED by the reader (the rungs derive used)
  magenta dashed   rungs still DROPPED, labelled with the rule that drops them
  green ticks      (reference tile, margin) nominal ledger rows + nominal head row

    python3 benchmarks/omr-local-staff-2026-09/edge_fix_sheet.py --out sheet.png
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import edge_census as ec  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

ARM_KW = {"before": {}, "after": dict(near_edge_ledgers=True,
                                      restore_masked_near_edge=True)}


def _font(n=12):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, n)
        except Exception:
            pass
    return ImageFont.load_default()


def read_arm(h, **kw):
    ec.ST.update(record=True, undo=None, main=False, box=None)
    ec.ST["trace"] = dict(clears=[], collapse=[])
    pos, reason = score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True, **kw)
    tr = ec.ST["trace"]
    ec.ST.update(record=False, undo=None, trace=None)
    return pos, reason, tr


def arm_lines(h, pos, tr, sign, edge_pos):
    """(counted ys, dropped [(y, rule)]) for one arm. Counted = the first n
    rungs of the ladder derive received, n from the answer (offset 2n for a
    line, 2n+1 for a space)."""
    ladder = sorted(tr.get("final_ladder") or [], key=lambda v: sign * v)
    if pos is None:
        n = 0
    else:
        off = int(sign * (pos - edge_pos))
        n = off // 2
    counted = ladder[:n]
    dropped = []
    for y in ladder[n:]:
        dropped.append((y, "popped: not a ledger before the head"))
    # bare-ink rungs the walk never kept (other-head mask / clears-box)
    side, s0 = ec.stage0_candidates(h)
    for y in s0:
        if not any(abs(y - r) < 0.35 * 16 for r in ladder):
            dropped.append((y, "not kept (other-head mask / clears-box)"))
    return counted, dropped


def ink_pair(gray, y, x0, x1, sp):
    zones = [(x0 - 0.6 * sp, x0), (x1, x1 + 0.6 * sp)]   # where a ledger juts out of a head

    def frac(yc):
        best = 0.0
        for lo, hi in zones:
            lo, hi = max(0, int(lo)), min(gray.shape[1], int(hi))
            strip = gray[max(0, int(yc) - 12):int(yc) + 13, lo:hi]
            thr = lg._otsu_threshold(strip)
            for dy in (-1, 0, 1):
                yy = int(round(yc)) + dy
                if 0 <= yy < gray.shape[0]:
                    best = max(best, float((gray[yy, lo:hi] <= thr).mean()))
        return best

    on = frac(y)
    off = (frac(y - 0.5 * sp) + frac(y + 0.5 * sp)) / 2.0
    return on, off


def tile(h, label, pos, counted, dropped, ref, edge, sp, sign, tag):
    scale = max(3, int(round(48.0 / sp)))
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    cx = (x0 + x1) / 2.0
    ys = [y0, y1, edge] + counted + [d[0] for d in dropped]
    lo, hi = min(ys) - 0.9 * sp, max(ys) + 0.9 * sp
    half = 3.4 * sp
    cx0, cx1 = int(cx - half), int(cx + half)
    cy0, cy1 = int(lo), int(hi)
    crop = gray[cy0:cy1, cx0:cx1]
    im = Image.fromarray(crop).convert("RGB").resize(
        (crop.shape[1] * scale, crop.shape[0] * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    f = _font(12)
    Y = lambda y: (y - cy0) * scale  # noqa: E731
    X = lambda x: (x - cx0) * scale  # noqa: E731
    for xx in range(0, im.width, 8):
        d.line([(xx, Y(edge)), (xx + 3, Y(edge))], fill=(40, 90, 255), width=1)
    for y in counted:
        d.line([(X(cx - 1.1 * sp), Y(y)), (X(cx + 1.1 * sp), Y(y))], fill=(255, 140, 0), width=2)
    for k, (y, rule) in enumerate(dropped):
        xa, xb = X(cx - 1.1 * sp), X(cx + 1.1 * sp)
        xx = xa
        while xx < xb:
            d.line([(xx, Y(y)), (min(xx + 9, xb), Y(y))], fill=(230, 0, 200), width=2)
            xx += 15
        d.text((4, Y(y) - 14 + 11 * (k % 2)), rule, fill=(230, 0, 200), font=f)
    d.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(255, 0, 0), width=2)
    if tag == "reference":
        # nominal rows: ledgers at edge + sign*k*sp for k=1.., head at ref pos
        edge_pos = 0 if sign < 0 else 8
        steps = abs(ref - edge_pos)
        for k in range(1, steps // 2 + 1):
            yy = edge + sign * k * sp
            d.line([(0, Y(yy)), (14, Y(yy))], fill=(0, 170, 0), width=3)
        yh = edge + sign * steps * sp / 2.0
        d.line([(0, Y(yh)), (30, Y(yh))], fill=(0, 120, 0), width=3)
        d.text((34, Y(yh) - 7), "ref head (nominal)", fill=(0, 120, 0), font=f)
    foot = Image.new("RGB", (im.width, 34), (255, 255, 255))
    fd = ImageDraw.Draw(foot)
    fd.text((4, 2), f"[{tag}] {label}", fill=(0, 0, 0), font=f)
    ans = f"answer {pos}" if tag != "reference" else f"reference {ref}"
    fd.text((4, 17), ans, fill=(0, 0, 0), font=f)
    out = Image.new("RGB", (im.width, im.height + 34), (255, 255, 255))
    out.paste(im, (0, 0))
    out.paste(foot, (0, im.height))
    return out


def main():
    out = sys.argv[sys.argv.index("--out") + 1]
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    ec.install()
    rows = []
    try:
        for d, hs in heads.items():
            for h in hs:
                res = {}
                for arm, kw in ARM_KW.items():
                    res[arm] = read_arm(h, **kw)
                if res["before"][0] != res["after"][0]:
                    rows.append((d, h, res))
    finally:
        ec.uninstall()
    tiles_rows, report = [], []
    for d, h, res in rows:
        ys = sorted(h["lines"])
        sp = (ys[-1] - ys[0]) / 4.0
        x0, y0, x1, y1 = h["box"]
        sign = -1.0 if (y0 + y1) / 2 < ys[0] else 1.0
        edge = ys[0] if sign < 0 else ys[-1]
        edge_pos = 0 if sign < 0 else 8
        ref = h["truth"][0]
        trio = []
        for arm in ("before", "after"):
            pos, reason, tr = res[arm]
            counted, dropped = arm_lines(h, pos, tr, sign, edge_pos)
            trio.append(tile(h, f"{d[:8]} {h['subject']}", pos, counted, dropped,
                             ref, edge, sp, sign, arm))
            for tagname, ylist in (("orange", counted), ("magenta", [y for y, _ in dropped])):
                for y in ylist:
                    on, off = ink_pair(h["gray"], y, x0, x1, sp)
                    report.append((h["subject"], arm, tagname, y, on, off))
        trio.append(tile(h, f"{d[:8]} {h['subject']}", None, [], [], ref, edge, sp,
                         sign, "reference"))
        tiles_rows.append(trio)
    W = max(t.width for r in tiles_rows for t in r)
    heights = [max(t.height for t in r) for r in tiles_rows]
    S = Image.new("RGB", (3 * (W + 6), sum(heights) + 6 * len(heights)), (235, 235, 235))
    y = 0
    for r, hh in zip(tiles_rows, heights):
        for i, t in enumerate(r):
            S.paste(t, (i * (W + 6), y))
        y += hh + 6
    S.save(out)
    print("wrote", out, S.size, len(rows), "heads")
    lines = ["stub-zone ink fraction at each drawn line (the 0.6 sp just outside each side of the head's box, best of rows y-1..y+1)",
             "vs the same zones read 0.5 sp above and below (mean) -- a line off the print reads as low as its shifted copy",
             f"{'head':20} {'arm':7} {'colour':8} {'y':>8} {'on':>5} {'off':>5}"]
    for sub, arm, col, y, on, off in report:
        lines.append(f"{sub:20} {arm:7} {col:8} {y:8.1f} {on:5.2f} {off:5.2f}")
    txt = "\n".join(lines)
    print(txt)
    Path(out).with_suffix(".pixel_check.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
