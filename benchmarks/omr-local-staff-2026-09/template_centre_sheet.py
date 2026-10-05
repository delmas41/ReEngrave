#!/usr/bin/env python3
"""lane-ledger-template-centre: crop sheet of every head whose reading the
template centre CHANGES (F1; F2 and F3 change none) plus the 9 census
through-line heads, each as before / after / reference.

  red box          the detector's box
  blue outline     the template oval at its matched position (round 4 matcher)
  green            the row the through-the-middle probe is centred on
                   (long = this arm's probe row, +-0.15 sp band drawn as ticks)
  orange           ledgers COUNTED by the reader
  magenta dashed   rungs DROPPED, labelled with the rule
  grey dotted      the staff's outer line (where ledgers count from)
  green ticks (reference tile, margin) nominal ledger rows + nominal head row

BEFORE = F0 (fix 1, probe at the box middle); AFTER = F1 (probe at the
template centre); REFERENCE = the print with the reference pitch's nominal
position. Real print at the gather's DPI, x3 or more (nearest neighbour).

    python3 benchmarks/omr-local-staff-2026-09/template_centre_sheet.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import template_centre as tc  # noqa: E402
import edge_census as ec  # noqa: E402
import edge_fix_sheet as efs  # noqa: E402
import template_review_r4 as r4  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT = HERE.parents[1] / "out" / "print" / "ledgers" / "template_centre"
FIX1 = dict(near_edge_ledgers=True, restore_masked_near_edge=True)
GREEN, BLUE = (0, 150, 0), (30, 80, 255)


def oval_poly(ctx, fit, spacing):
    shape = ctx["shape"]
    cx, cy = fit["tmpl_cx"], fit["tmpl_cy"]
    if shape.get("mask") is not None:
        return ht.mask_outline_poly(shape["mask"], cx, cy, spacing)
    return ht.geometry_outline_poly(cx, cy, spacing, shape["tilt_deg"], shape["width_sp"],
                                    shape["height_sp"])


def tile(h, label, pos, counted, dropped, ref, edge, sp, sign, tag, poly, probe_y):
    scale = max(3, int(round(48.0 / sp)))
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    cx = (x0 + x1) / 2.0
    ys = [y0, y1, edge] + counted + [d[0] for d in dropped] + [probe_y]
    lo, hi = min(ys) - 0.9 * sp, max(ys) + 0.9 * sp
    half = 3.4 * sp
    cx0, cx1 = int(cx - half), int(cx + half)
    cy0, cy1 = int(lo), int(hi)
    crop = gray[cy0:cy1, cx0:cx1]
    im = Image.fromarray(crop).convert("RGB").resize(
        (crop.shape[1] * scale, crop.shape[0] * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    f = efs._font(12)
    Y = lambda y: (y - cy0 + 0.5) * scale  # noqa: E731
    X = lambda x: (x - cx0 + 0.5) * scale  # noqa: E731
    for xx in range(0, im.width, 8):
        d.line([(xx, Y(edge)), (xx + 3, Y(edge))], fill=(120, 120, 120), width=1)
    for y in counted:
        d.line([(X(cx - 1.1 * sp), Y(y)), (X(cx + 1.1 * sp), Y(y))], fill=(255, 140, 0), width=2)
    for k, (y, rule) in enumerate(dropped):
        xa, xb = X(cx - 1.1 * sp), X(cx + 1.1 * sp)
        xx = xa
        while xx < xb:
            d.line([(xx, Y(y)), (min(xx + 9, xb), Y(y))], fill=(230, 0, 200), width=2)
            xx += 15
        d.text((4, Y(y) - 14 + 11 * (k % 2)), rule, fill=(230, 0, 200), font=f)
    pts = [(X(px), Y(py)) for px, py in poly]
    d.line(pts + [pts[0]], fill=BLUE, width=2)
    d.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(255, 0, 0), width=2)
    if tag != "reference":
        tol = tc.ec.lg.MIDDLE_ROW_TOL_SPACES * sp
        d.line([(X(cx - 1.3 * sp), Y(probe_y)), (X(cx + 1.3 * sp), Y(probe_y))], fill=GREEN, width=2)
        for dy in (-tol, tol):
            for xx in (cx - 1.3 * sp, cx + 1.3 * sp):
                d.line([(X(xx), Y(probe_y + dy)), (X(xx) + 6, Y(probe_y + dy))], fill=GREEN, width=1)
    if tag == "reference":
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


def inside_oval(poly, x, y):
    """Is (x, y) inside the polygon (ray casting)?"""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            inside = not inside
    return inside


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fitted = tc.all_fits()
    ec.install()
    rows = []
    try:
        for doc, dd in fitted.items():
            for h in dd["heads"]:
                fit = dd["fits"][h["subject"]]
                b = efs.read_arm(h, **FIX1)
                a = efs.read_arm(h, head_center_y=fit["tmpl_cy"], **FIX1)
                changed = b[0] != a[0]
                if changed or h["subject"] in tc.CENSUS_9:
                    rows.append((doc, h, fit, b, a, changed, dd["ctx"]))
    finally:
        ec.uninstall()
    report, groups = [], {"changed": [], "census": []}
    for doc, h, fit, b, a, changed, ctx in rows:
        ys = sorted(h["lines"])
        sp = (ys[-1] - ys[0]) / 4.0
        x0, y0, x1, y1 = h["box"]
        sign = -1.0 if (y0 + y1) / 2 < ys[0] else 1.0
        edge = ys[0] if sign < 0 else ys[-1]
        edge_pos = 0 if sign < 0 else 8
        ref = h["truth"][0]
        poly = oval_poly(ctx, fit, sp)
        trio = []
        for tag, (pos, reason, tr), probe in (("before F0", b, (y0 + y1) / 2.0),
                                              ("after F1", a, fit["tmpl_cy"])):
            counted, dropped = efs.arm_lines(h, pos, tr, sign, edge_pos)
            trio.append(tile(h, f"{doc[:8]} {h['subject']}", pos, counted, dropped, ref, edge,
                             sp, sign, tag, poly, probe))
            inside = inside_oval(poly, (x0 + x1) / 2.0, probe)
            for colour, ylist in (("orange", counted), ("magenta", [y for y, _ in dropped])):
                for y in ylist:
                    on, off = efs.ink_pair(h["gray"], y, x0, x1, sp)
                    report.append(dict(head=h["subject"], arm=tag, colour=colour, y=round(y, 1),
                                       ink_on=round(on, 2), ink_off=round(off, 2)))
            report.append(dict(head=h["subject"], arm=tag, colour="green", y=round(probe, 1),
                               inside_oval_at_box_x=inside))
        trio.append(tile(h, f"{doc[:8]} {h['subject']}", None, [], [], ref, edge, sp, sign,
                         "reference", poly, (y0 + y1) / 2.0))
        groups["changed" if changed else "census"].append(trio)
    for name, tiles_rows in groups.items():
        if not tiles_rows:
            continue
        W = max(t.width for r in tiles_rows for t in r)
        heights = [max(t.height for t in r) for r in tiles_rows]
        S = Image.new("RGB", (3 * (W + 6), sum(heights) + 6 * len(heights)), (235, 235, 235))
        y = 0
        for r, hh in zip(tiles_rows, heights):
            for i, t in enumerate(r):
                S.paste(t, (i * (W + 6), y))
            y += hh + 6
        p = OUT / f"sheet_{name}.png"
        S.save(p)
        print("wrote", p, S.size, len(tiles_rows), "heads")
    (OUT / "pixel_check.json").write_text(json.dumps(report, indent=1))
    print(f"{'head':18} {'arm':10} {'colour':8} {'y':>8} {'ink_on':>6} {'ink_off':>7} oval")
    for r in report:
        print(f"{r['head']:18} {r['arm']:10} {r['colour']:8} {r['y']:>8} {r.get('ink_on', '')!s:>6} "
              f"{r.get('ink_off', '')!s:>7} {r.get('inside_oval_at_box_x', '')}")


if __name__ == "__main__":
    main()
