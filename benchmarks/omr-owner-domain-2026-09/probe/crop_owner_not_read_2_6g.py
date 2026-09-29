"""ROADMAP 2.6g — crops of the 16 sampled `owner_not_read` (`far_no_rungs`)
heads from `probe_owner_not_read_2_6g.py`'s crop-data JSON. PDF-only: no
record access here (the one record read already happened in the probe).

Banded style of `crop_far_no_rungs_2_6c.py` (GREEN = upper candidate,
ORANGE = lower, colour follows POSITION not role): both candidate staves
shaded, subject bracketed RED with thick corner arms. Adds, for THIS lane's
own question:

  * every detector `ledgerLine` `Q.GLYPH_BOX` in the same system, drawn as a
    thin CYAN box (so a box that exists but was refused, too far, or
    unmatched to either ladder is visible, not just the ones `ladder_side`
    counted);
  * every `Q.LEDGER_RUNG_INK` (CV) window this subject's contest tested,
    drawn dashed BLUE per (candidate, step), labelled with its four
    densities -- the SAME window `gather.ledger_rung_ink` sampled, at the
    position `_observe_ledger_rung_ink` wrote to `window_page_px`.

Frame control reused from `crop_losers_2_6b._frame_ok` (0 refused of N
attempted is not a pass -- see the manifest's own field).

    python3 benchmarks/omr-owner-domain-2026-09/probe/crop_owner_not_read_2_6g.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from crop_losers_2_6b import _frame_ok  # noqa: E402

DATA = HERE.parent / "out" / "owner-not-read-2.6g-crop-data.json"
PDF = REPO_ROOT / ("library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-"
                    "1870--imslp984073.pdf")
OUT_DIR = HERE.parent / "out" / "print"
DPI = 600


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    data = json.loads(DATA.read_text())
    jobs = data["jobs"]

    doc = fitz.open(PDF)
    pages = {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=18)
    manifest, refused = [], []

    for job in jobs:
        sub = job["subject"]
        p = int(sub.split("/")[1])
        bb = job["head_box"]["bbox_page_px"]
        cands = list(job["candidate_geometry"].items())
        if len(cands) != 2 or any(
                "staff_lines" not in g for _c, g in cands):
            refused.append({"subject": sub, "why": "geometry missing"})
            continue
        cands.sort(key=lambda cg: min(cg[1]["staff_lines"]))
        (upper_key, upper_g), (lower_key, lower_g) = cands

        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else Image.frombytes(
                      "L", (pm.width, pm.height), pm.samples).convert("RGB"))
            pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
        im, arr = pages[p]

        lines = {upper_key: [float(y) for y in upper_g["staff_lines"]],
                 lower_key: [float(y) for y in lower_g["staff_lines"]]}
        sp = {upper_key: float(upper_g["staff_spacing"]),
              lower_key: float(lower_g["staff_spacing"])}
        shifted = {k: [y + sp[k] / 2.0 for y in v] for k, v in lines.items()}
        ok = {k: _frame_ok(arr, lines[k], sp[k]) for k in lines}
        broken = {k: _frame_ok(arr, shifted[k], sp[k]) for k in lines}
        if not all(v[0] for v in ok.values()) or any(
                v[0] for v in broken.values()):
            refused.append({"subject": sub, "why": "FRAME CONTROL FAILED",
                            "contrast": {k: round(v[1], 1)
                                         for k, v in ok.items()},
                            "contrast_shifted": {k: round(v[1], 1)
                                                 for k, v in broken.items()}})
            continue

        windows = job["ledger_rung_ink_rows"]
        led_boxes = [b for b in job["nearby_detector_ledger_boxes"]
                     if b["bbox_page_px"][0] <= bb[2] + 20 * sp[upper_key]
                     and b["bbox_page_px"][2] >= bb[0] - 20 * sp[upper_key]]

        sp0 = sp[upper_key]
        ys = ([bb[1], bb[3]] + lines[upper_key] + lines[lower_key]
              + [w["window_page_px"][1] for w in windows]
              + [w["window_page_px"][3] for w in windows])
        xs = ([bb[0], bb[2]]
              + [w["window_page_px"][0] for w in windows]
              + [w["window_page_px"][2] for w in windows]
              + [b["bbox_page_px"][0] for b in led_boxes]
              + [b["bbox_page_px"][2] for b in led_boxes])
        cx0 = int(max(0, min(xs) - 6 * sp0))
        cx1 = int(min(im.width, max(xs) + 6 * sp0))
        cy0 = int(max(0, min(ys) - 1.5 * sp0))
        cy1 = int(min(im.height, max(ys) + 1.5 * sp0))
        Z = 2
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        small = ImageFont.load_default(size=16)
        for key, rgb, label in ((upper_key, (0, 160, 60), "GREEN upper"),
                                (lower_key, (235, 130, 0), "ORANGE lower")):
            top = (min(lines[key]) - cy0) * Z
            bot = (max(lines[key]) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=rgb + (55,))
            for ly in lines[key]:
                y = (ly - cy0) * Z
                od.line([(0, y), (crop.width, y)], fill=rgb + (220,), width=3)
            od.text((6, top + 2), f"{label} {key} "
                    f"exp={job['ledger_sides'].get(key, {}).get('expected')}"
                    f" found={job['ledger_sides'].get(key, {}).get('found')}",
                    fill=rgb + (255,), font=small)
        # detector ledgerLine boxes nearby, thin cyan
        for b in led_boxes:
            x0, y0, x1, y1 = b["bbox_page_px"]
            dx0, dy0 = (x0 - cx0) * Z, (y0 - cy0) * Z
            dx1, dy1 = (x1 - cx0) * Z, (y1 - cy0) * Z
            od.rectangle([dx0, dy0, dx1, dy1], outline=(0, 200, 200, 255),
                        width=3)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        dr = ImageDraw.Draw(crop)
        # the CV windows, dashed blue, labelled
        for w in windows:
            wx0, wy0, wx1, wy1 = w["window_page_px"]
            wx0, wy0 = (wx0 - cx0) * Z, (wy0 - cy0) * Z
            wx1, wy1 = (wx1 - cx0) * Z, (wy1 - cy0) * Z
            step = 8
            x = wx0
            while x < wx1:
                dr.line([(x, wy0), (min(x + step, wx1), wy0)],
                        fill=(0, 90, 220), width=2)
                dr.line([(x, wy1), (min(x + step, wx1), wy1)],
                        fill=(0, 90, 220), width=2)
                x += step * 2
            y = wy0
            while y < wy1:
                dr.line([(wx0, y), (wx0, min(y + step, wy1))],
                        fill=(0, 90, 220), width=2)
                dr.line([(wx1, y), (wx1, min(y + step, wy1))],
                        fill=(0, 90, 220), width=2)
                y += step * 2
            lab = (f"{w['candidate'].split('/')[-1]} step{w['step']} "
                  f"c={w['center']} l={w['left']} r={w['right']} "
                  f"adj={w['adjacent']}")
            dr.text((wx0 + 2, wy0 - 16), lab, fill=(0, 60, 160), font=small)
        # the head, bracketed red
        bx0, by0 = (bb[0] - cx0) * Z, (bb[1] - cy0) * Z
        bx1, by1 = (bb[2] - cx0) * Z, (bb[3] - cy0) * Z
        arm = max(10, int((bx1 - bx0) * 0.5))
        for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0), width=6)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0), width=6)
        n = len(manifest) + 1
        name = f"2.6g-owner-not-read-{n:02d}.png"
        title = [
            (f"{name}  {sub}  pdf idx {p}  twin={job['twin']} "
             f"({job['twin_status']})", (0, 0, 0)),
            ("glyph_owner ABSTAINED far_no_rungs; CYAN box = a detector "
             "ledgerLine nearby; DASHED BLUE = a CV window tested (all "
             "found=False here)", (80, 0, 120)),
            ("Q: UPPER (green) / LOWER (orange) / not a note -- are there "
             "PRINTED ledger lines either reader should have caught?",
             (0, 0, 0)),
        ]
        band = 20 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (t, col) in enumerate(title):
            cd.text((6, 4 + i * 20), t, fill=col, font=font)
        out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name, "subject": sub,
            "twin": job["twin"], "twin_status": job["twin_status"],
            "page": p, "upper_staff": upper_key, "lower_staff": lower_key,
            "ledger_sides": job["ledger_sides"],
            "n_detector_ledger_boxes_nearby": len(led_boxes),
            "n_cv_windows_tested": len(windows),
            "frame_contrast": {k: round(v[1], 1) for k, v in ok.items()},
            "frame_contrast_shifted_half_space": {
                k: round(v[1], 1) for k, v in broken.items()},
            "question": ("UPPER (green) / LOWER (orange) / not a note -- "
                        "are there ledger lines either reader should have "
                        "caught?"),
            "VERDICT_none_yet": None})

    print(f"crops {len(manifest)}  refused {len(refused)}")
    (OUT_DIR / "2.6g-owner-not-read-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6g", "record": data["record"], "pdf": str(PDF),
        "dpi": DPI, "seed": data["seed"], "targets": data["targets"],
        "crops": manifest, "refused": refused}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
