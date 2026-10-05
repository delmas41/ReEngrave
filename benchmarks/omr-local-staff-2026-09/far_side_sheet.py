#!/usr/bin/env python3
"""lane-ledger-far-side-rule (2026-10-04): crop sheet of every head the
far-side rule changes (fix1 -> fix1 + far_side_ledger).

One row per changed head, two panels: BEFORE (fix1) and AFTER (fix1 + rule),
cut from the PDF raster at the gather's own DPI, 110 px per staff space
(x7 on Litolff).  Red corner brackets = the detector box.  ORANGE = a rung the
reader COUNTED in that arm.  MAGENTA DASHED = a rung the ink offers at the
head's far side that this arm did NOT count (BEFORE: the far-side line the
fix-1 reader dropped; AFTER: none are dropped by the rule -- it only adds).
Every orange/magenta line is pixel-checked: ink fraction on the row vs 0.5 sp
off it (+-1 px), over the head span (box +-0.5 sp) and over the better stub
zone beside the box.  A frame control (staff outer line vs 0.5 sp beyond)
must read on > off.

    python3 benchmarks/omr-local-staff-2026-09/far_side_sheet.py \
        --sheet out/print/ledgers/far_side_rule
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402

import edge_census as ec  # noqa: E402
import far_edge_crops as fec  # noqa: E402
import score_far_side as sf  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

ORANGE, MAGENTA, RED = (255, 140, 0), (230, 0, 200), (200, 0, 0)
PX = 110.0
WIN_W, WIN_H = 7.0, 7.0


def counted_rungs(h, n_counted):
    """Page ys of the first `n_counted` ledgers of the production walk."""
    ys = sorted(float(v) for v in h["lines"])
    x0, y0, x1, y1 = h["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    side = "above" if cy < ys[0] else "below"
    others = [b for s, b in h["boxes"] if s != h["subject"]] + [b for _s, b in h["acc"]]
    items = lg.measure_ledger_rungs(
        h["gray"], ys, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1),
        collapse_edges_box=tuple(h["box"]), restore_masked_staff_side_rungs=True).get(side, [])
    return items[:n_counted]


def panel(h, before_pos, after_pos, which, rungs, dropped, label):
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    ys = sorted(float(v) for v in h["lines"])
    sp = (ys[-1] - ys[0]) / 4.0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    ax0, ay0 = int(round(cx - WIN_W / 2 * sp)), int(round(cy - WIN_H / 2 * sp))
    ax1, ay1 = int(round(cx + WIN_W / 2 * sp)), int(round(cy + WIN_H / 2 * sp))
    H, W = gray.shape
    crop = np.full((ay1 - ay0, ax1 - ax0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(ax0, 0), max(ay0, 0), min(ax1, W), min(ay1, H)
    crop[sy0 - ay0:sy1 - ay0, sx0 - ax0:sx1 - ax0] = gray[sy0:sy1, sx0:sx1]
    tw, th = int(round(WIN_W * PX)), int(round(WIN_H * PX))
    big = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_CUBIC)
    img = Image.fromarray(big).convert("RGB")
    d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - ax0) * tw / (ax1 - ax0), (y - ay0) * th / (ay1 - ay0))  # noqa: E731
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    for y, nm in rungs:
        _, py = P(0, y)
        d.line([(0, py), (tw, py)], fill=ORANGE, width=2)
        d.text((tw - 52, py - 30), nm, fill=ORANGE, font=font)
    for y, nm in dropped:
        _, py = P(0, y)
        for xs in range(0, tw, 28):
            d.line([(xs, py), (xs + 14, py)], fill=MAGENTA, width=3)
        d.text((tw - 52, py + 4), nm, fill=MAGENTA, font=font)
    L, g, wd = 0.28 * PX, 5, 3
    bx0, by0 = P(x0, y0)
    bx1, by1 = P(x1, y1)
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        px, py = px - dx * g, py - dy * g
        d.line([(px, py), (px + dx * L, py)], fill=RED, width=wd)
        d.line([(px, py), (px, py + dy * L)], fill=RED, width=wd)
    d.rectangle([0, 0, tw - 1, 36], fill=(255, 255, 255))
    d.text((6, 4), label, fill=(0, 0, 0), font=font)
    d.rectangle([0, 0, tw - 1, th - 1], outline=(120, 120, 120), width=2)
    return img


def main():
    from PIL import Image, ImageDraw, ImageFont
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = sf.run(heads)
    for arm in ("default", "fix1", "fix1_far"):          # CONTROL
        for d in ts.DOCS:
            vs = [r["v"] for r in res[arm][d].values()]
            print(f"control {arm:9} {d:20} {ec.tally(vs)} n={len(vs)}")
    changed = [(d, h) for d in ts.DOCS for h in heads[d]
               if res["fix1"][d][h["subject"]]["pos"] != res["fix1_far"][d][h["subject"]]["pos"]]
    print("changed heads:", [h["subject"] for _d, h in changed])
    outdir = Path(sys.argv[sys.argv.index("--sheet") + 1]) if "--sheet" in sys.argv else None
    rows, key = [], []
    for d, h in changed:
        s = h["subject"]
        b, a = res["fix1"][d][s], res["fix1_far"][d][s]
        ys = sorted(float(v) for v in h["lines"])
        sp = (ys[-1] - ys[0]) / 4.0
        sign = -1.0 if (h["box"][1] + h["box"][3]) / 2.0 < ys[0] else 1.0
        edge = ys[0] if sign < 0 else ys[-1]
        others = [bx for ss, bx in h["boxes"] if ss != s] + [bx for _s, bx in h["acc"]]
        ev = lg.far_side_ledger_evidence(
            h["gray"], tuple(h["box"]), sign, sp, edge,
            [bx for ss, bx in h["boxes"] if ss != s], others)
        n = ev["n"]
        walked = counted_rungs(h, n - 1)
        near = [(y, f"L{i+1}") for i, y in enumerate(walked)]
        far = [(ev["y"], f"L{n}")]
        pb = panel(h, b["pos"], a["pos"], "before", near, far,
                   f"BEFORE (fix 1): {b['pos']}  [{b['v']}]")
        pa = panel(h, b["pos"], a["pos"], "after", near + far, [],
                   f"AFTER (+ far-side rule): {a['pos']}  [{a['v']}]")
        rows.append((s, d, pb, pa, h["truth"]))
        # pixel check: every drawn line, ink on the row vs 0.5 sp off it
        px = []
        for y, nm in near + far:
            pn = fec.pixel_numbers(h["gray"], y, h["box"], sp)
            px.append(dict(line=nm, y=round(float(y), 1), span_on=round(pn["span_on"], 2),
                           span_off=round(pn["span_off"], 2), stub_on=round(pn["stub_on"], 2),
                           stub_off=round(pn["stub_off"], 2), stub_side=pn["stub_side"]))
        fc = fec._frame_control(h, sp)
        key.append(dict(subject=s, doc=d, reference=h["truth"], before=b["pos"], after=a["pos"],
                        far_rung_ordinal=n, far_rung_y=ev["y"], far_rung_jut=ev["jut"],
                        pixel_check=px, frame_control=fc, px_per_sp=PX,
                        source_scale=PX / sp, sp=sp))
    if outdir is None:
        return
    outdir.mkdir(parents=True, exist_ok=True)
    tw, th = int(WIN_W * PX), int(WIN_H * PX)
    pad, top = 20, 90
    Wd = 2 * tw + 3 * pad
    Ht = top + len(rows) * (th + 50) + pad
    sheet = Image.new("RGB", (Wd, Ht), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    dr.text((pad, 14), "Red brackets = the note.  ORANGE = ledgers counted.  MAGENTA dashed = a line at the "
            "note's far side NOT counted.", fill=(0, 0, 0), font=f)
    dr.text((pad, 50), "Left: before the rule.  Right: after.  Reference position under each row.",
            fill=(0, 0, 0), font=f)
    for i, (s, d, pb, pa, truth) in enumerate(rows):
        y = top + i * (th + 50)
        sheet.paste(pb, (pad, y + 40))
        sheet.paste(pa, (2 * pad + tw, y + 40))
        dr.text((pad, y + 6), f"{s}   reference {truth}", fill=(0, 0, 0), font=f)
    out = outdir / "far_side_sheet.png"
    sheet.save(out)
    (outdir / "far_side_key.json").write_text(json.dumps(key, indent=1, default=str))
    print("sheet:", out.resolve())
    for k in key:
        print(k["subject"], "ref", k["reference"], "before", k["before"], "after", k["after"],
              "frame", k["frame_control"])
        for p in k["pixel_check"]:
            print("   ", p)


if __name__ == "__main__":
    main()
