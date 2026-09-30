"""ROADMAP 2.45 -- print crop of the three doubly-refused eighth rests on
Brahms 1/i Breitkopf p1, system 0, bar 5 (`glyph/1/0/2/5/{0,3,10}` and
`glyph/1/0/3/5/{0,1,2}`), and a frame control before anything is drawn as
evidence (the same precedent as `crop_contested.py`).

Renders at 600 dpi, draws staff 2 (upper) in blue and staff 3 (lower) in
green -- both wide, at least 1000 px, one crop for the pair -- boxes each
rest in red with a caption naming which staff the print's own voices say
owns it.

    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/crop_between_staves_2_45.py \
        --record out/2.45/brahms-p1-arm.json \
        --pdf library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
        --out out/print/2.45/brahms-p1-bar5-between-staves.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _frame_ok(arr, line_ys, margin=8.0):
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = 6
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    c = float(sum(off) / len(off) - sum(on) / len(on))
    return c >= margin, c


TARGETS = ["glyph/1/0/2/5/0", "glyph/1/0/2/5/3", "glyph/1/0/2/5/10",
          "glyph/1/0/3/5/0", "glyph/1/0/3/5/1", "glyph/1/0/3/5/2"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    rec = json.loads(Path(a.record).read_text())["record"]
    boxes = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"] in TARGETS:
            d = o.get("detail") or {}
            boxes[o["subject"]] = [float(v) for v in d["bbox_page_px"]]
    lines = {}
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines" and o["subject"] in (
                "staff/1/0/2", "staff/1/0/3"):
            lines[o["subject"]] = [float(y) for y in o["value"]]

    page_idx = 1
    doc = fitz.open(a.pdf)
    pm = doc[page_idx].get_pixmap(dpi=a.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))
    arr = np.asarray(im.convert("L"), dtype=float)

    ok2, c2 = _frame_ok(arr, lines["staff/1/0/2"])
    ok3, c3 = _frame_ok(arr, lines["staff/1/0/3"])
    print(f"frame control: staff2 contrast={c2:.1f} ok={ok2}  "
         f"staff3 contrast={c3:.1f} ok={ok3}")
    if not (ok2 and ok3):
        print("FRAME CONTROL FAILED -- refusing to crop")
        return 1

    xs = [b[0] for b in boxes.values()] + [b[2] for b in boxes.values()]
    x0, x1 = min(xs) - 90, max(xs) + 90
    y0 = lines["staff/1/0/2"][0] - 60
    y1 = lines["staff/1/0/3"][-1] + 60

    cx0, cy0 = int(max(0, x0)), int(max(0, y0))
    cx1, cy1 = int(min(im.width, x1)), int(min(im.height, y1))
    crop = im.crop((cx0, cy0, cx1, cy1))
    Z = max(1, int(1100 / max(1, crop.width)))
    Z = max(Z, 3)
    crop = crop.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)

    for ly in lines["staff/1/0/2"]:
        y = (ly - cy0) * Z
        dr.line([(0, y), (crop.width, y)], fill=(30, 80, 220), width=2)
    for ly in lines["staff/1/0/3"]:
        y = (ly - cy0) * Z
        dr.line([(0, y), (crop.width, y)], fill=(0, 150, 60), width=2)

    for sub, box in boxes.items():
        bx0, by0, bx1, by1 = [(v - (cx0 if i % 2 == 0 else cy0)) * Z
                              for i, v in enumerate(box)]
        arm_len = max(8, int((bx1 - bx0) * 0.4))
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=(220, 0, 0), width=3)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=(220, 0, 0), width=3)
        gi = sub.rsplit("/", 1)[1]
        dr.text((bx0, by0 - 22), f"g{gi}", fill=(220, 0, 0))

    band_h = 190
    out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
    out_im.paste(crop, (0, band_h))
    cd = ImageDraw.Draw(out_im)
    cd.text((6, 4), "Brahms 1/i Breitkopf p1, system 0, printed bar 13 -- "
                    "3 printed eighth rests between staves 2 and 3",
            fill=(0, 0, 0))
    cd.text((6, 22), "BLUE = staff 2 (upper, violin/oboe register) own lines "
                    "-- GREEN = staff 3 (lower) own lines", fill=(0, 0, 0))
    cd.text((6, 40), "RED boxes = the 3 rests, each detected once per staff "
                    "(6 glyph copies), all refused rest_outside_its_staff",
            fill=(0, 0, 0))
    cd.text((6, 62), "Sean (DECISIONS 2026-09-30): upper staff's 2 voices "
                    "are both already accounted for; the lower staff's "
                    "voice crosses and would be", fill=(0, 0, 0))
    cd.text((6, 78), "missing an eighth at each of these three onsets "
                    "without them -- the rests belong to the LOWER "
                    "(green) staff.", fill=(0, 0, 0))
    cd.text((6, 100), "BLOCKER (named, not built): Q.VOICES correctly "
                    "decides 2 voices on BOTH staves, but Q.METER ABSTAINS "
                    "here (meter_return_not_read)", fill=(0, 0, 0))
    cd.text((6, 116), "-- confirmed on a --pages 0-1 re-gather AND on the "
                    "committed whole-movement record, so this is not a "
                    "single-page artefact. The plate", fill=(0, 0, 0))
    cd.text((6, 132), "prints 6/8 (2.12h/2.12i/2.12l/2.29's own m.8 hemiola / "
                    "m.9 return system); the rule reads the DECIDED meter "
                    "only and never guesses,", fill=(0, 0, 0))
    cd.text((6, 148), "so an ABSTAINED cause means the rule never runs at "
                    "all here (rule 8) -- zero reinstated, not a computed "
                    "mismatch.", fill=(0, 0, 0))
    cd.text((6, 166), "Hand-checked with a hypothetical DECIDED 6/8 (real "
                    "totals): staff 3 (lower) is short 1.5 = the group, "
                    "exactly; staff 2's own separate", fill=(0, 0, 0))
    cd.text((6, 182), "~1.0 gap does not match and does not block -- the "
                    "case WOULD RESOLVE TO THE LOWER STAFF once the m.9 "
                    "return is read.", fill=(0, 0, 0))

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out_im.save(a.out)
    print(f"wrote {a.out}  ({out_im.width}x{out_im.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
