"""ROADMAP 2.6d — crops of `Q.LEDGER_RUNG_INK` measurements, for Sean.

The one-page base-vs-arm re-gather (Brahms Breitkopf 317803 pdf index 1)
credited ZERO steps on this page (`far_no_rungs` stayed 10 == 10): the
compound test (`gather.ledger_rung_ink`: centre + both overhangs dense, the
adjacent band NOT dense) never fired TRUE, though 193 of 547 measured
windows had a dense CENTRE. This crops the CLOSEST near-misses — not "heads
the CV rungs newly decide" (there are none on this page to show) but the
candidates that came nearest to being credited, drawn with the EXACT tested
window — so Sean can say whether the guard rejected real ink correctly or
threw it away.

Banded style of `crop_far_no_rungs_2_6c.py` (`_frame_ok` reused): the
CANDIDATE staff is a shaded band with its lines drawn thick; the head is
bracketed RED; the tested window is a DASHED BLUE rectangle at the measured
position, sized exactly as `gather.ledger_rung_ink` sampled it (converted
back to page pixels the same way `_observe_ledger_rung_ink` writes
`window_page_px`).

    python3 benchmarks/omr-owner-domain-2026-09/crop_cv_rung_2_6d.py \
        --record out/2.6d/arm/brahms-p2.json --pdf <edition.pdf> \
        --tag brahms --n 8

Record read ONLY through `record_io.load_record`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged.record_io import load_record  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from crop_losers_2_6b import _frame_ok  # noqa: E402

OUT_DIR = HERE / "out" / "print"
DPI = 600


def _score(d: dict) -> float:
    """How close this window came to being credited `found=True`: the
    weakest of the three overhang/centre densities, PENALISED if the
    adjacent-band guard alone is what failed it (still worth a look --
    that is exactly the guard Sean is being asked to calibrate)."""
    return min(d.get("center", 0.0), d.get("left", 0.0), d.get("right", 0.0))


def main(argv=None) -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args(argv)

    rec = load_record(a.record)["record"]
    rung_rows = [o for o in rec["observations"]
                if o["quantity"] == "ledger_rung_ink"]
    # credited rows first (there may be none), then by closeness
    rung_rows.sort(key=lambda o: (0 if o["value"] is True else 1,
                                  -_score(o["detail"])))

    box_by_subject: dict = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            box_by_subject[o["subject"]] = o
    geo: dict = {}
    for o in rec["observations"]:
        if o["quantity"] in ("staff_lines", "staff_spacing"):
            geo.setdefault(o["subject"], {})[o["quantity"]] = o["value"]

    doc = fitz.open(a.pdf)
    pages = {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=20)
    manifest, refused, seen = [], [], set()

    for row in rung_rows:
        if len(manifest) >= a.n:
            break
        sub = row["subject"]
        key = (sub, row["detail"].get("candidate"))
        if key in seen:
            continue
        seen.add(key)
        cand = row["detail"].get("candidate")
        win = row["detail"].get("window_page_px")
        box_row = box_by_subject.get(sub)
        if not box_row or not win or cand not in geo \
                or "staff_lines" not in geo[cand]:
            refused.append({"subject": sub, "why": "geometry or box missing"})
            continue
        bb = box_row["detail"]["bbox_page_px"]
        cand_lines = [float(y) for y in geo[cand]["staff_lines"]]
        cand_sp = float(geo[cand]["staff_spacing"])
        p = int(sub.split("/")[1])
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else Image.frombytes(
                      "L", (pm.width, pm.height), pm.samples).convert("RGB"))
            pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
        im, arr = pages[p]
        ok, contrast = _frame_ok(arr, cand_lines, cand_sp)
        shifted = [y + cand_sp / 2.0 for y in cand_lines]
        broken, contrast_b = _frame_ok(arr, shifted, cand_sp)
        if not ok or broken:
            refused.append({"subject": sub, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 1),
                            "contrast_shifted": round(contrast_b, 1)})
            continue
        sp = cand_sp
        ys = [bb[1], bb[3], win[1], win[3]] + cand_lines
        cx0 = int(max(0, min(bb[0], win[0]) - 3 * sp))
        cx1 = int(min(im.width, max(bb[2], win[2]) + 3 * sp))
        cy0 = int(max(0, min(ys) - 1.5 * sp))
        cy1 = int(min(im.height, max(ys) + 1.5 * sp))
        Z = 3
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        top = (min(cand_lines) - cy0) * Z
        bot = (max(cand_lines) - cy0) * Z
        od.rectangle([0, top, crop.width, bot], fill=(0, 160, 60, 55))
        for ly in cand_lines:
            y = (ly - cy0) * Z
            od.line([(0, y), (crop.width, y)], fill=(0, 160, 60, 220), width=3)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        dr = ImageDraw.Draw(crop)
        # the head, bracketed red
        bx0, by0 = (bb[0] - cx0) * Z, (bb[1] - cy0) * Z
        bx1, by1 = (bb[2] - cx0) * Z, (bb[3] - cy0) * Z
        arm = max(10, int((bx1 - bx0) * 0.45))
        for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0), width=5)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0), width=5)
        # the EXACT tested window, dashed blue
        wx0, wy0 = (win[0] - cx0) * Z, (win[1] - cy0) * Z
        wx1, wy1 = (win[2] - cx0) * Z, (win[3] - cy0) * Z
        step = 10
        x = wx0
        while x < wx1:
            dr.line([(x, wy0), (min(x + step, wx1), wy0)], fill=(0, 90, 220),
                    width=3)
            dr.line([(x, wy1), (min(x + step, wx1), wy1)], fill=(0, 90, 220),
                    width=3)
            x += step * 2
        y = wy0
        while y < wy1:
            dr.line([(wx0, y), (wx0, min(y + step, wy1))], fill=(0, 90, 220),
                    width=3)
            dr.line([(wx1, y), (wx1, min(y + step, wy1))], fill=(0, 90, 220),
                    width=3)
            y += step * 2
        d = row["detail"]
        n = len(manifest) + 1
        name = f"2.6d-cv-{a.tag}-{n:02d}.png"
        title = [
            (f"{name}  {sub}  candidate {cand}  step {d.get('step')}"
             f"  pdf idx {p}", (0, 0, 0)),
            (f"Q.LEDGER_RUNG_INK found={row['value']}  centre={d.get('center')}"
             f"  left={d.get('left')}  right={d.get('right')}"
             f"  adjacent={d.get('adjacent')}", (80, 0, 120)),
            ("Q: inside the DASHED BLUE box -- a printed ledger line, thin "
             "and reaching past the RED-bracketed head on both sides, or "
             "not?", (0, 0, 0)),
        ]
        band = 22 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (t, col) in enumerate(title):
            cd.text((6, 4 + i * 22), t, fill=col, font=font)
        out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name, "subject": sub, "page": p,
            "candidate": cand, "step": d.get("step"),
            "found": row["value"], "measurement": d,
            "head_page_box": [round(v, 1) for v in bb],
            "window_page_px": [round(v, 1) for v in win],
            "frame_contrast": round(contrast, 1),
            "frame_contrast_shifted_half_space": round(contrast_b, 1),
            "question": ("is there a printed ledger line inside the dashed "
                        "blue window, thin, reaching past the head on both "
                        "sides?"),
            "VERDICT_none_yet": None})

    print(f"crops {len(manifest)}  refused {len(refused)}")
    (OUT_DIR / f"2.6d-cv-{a.tag}-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6d",
        "record": a.record, "pdf": a.pdf, "dpi": DPI,
        "population_ledger_rung_ink_rows": len(rung_rows),
        "credited_true": sum(1 for r in rung_rows if r["value"] is True),
        "crops": manifest, "refused": refused}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
