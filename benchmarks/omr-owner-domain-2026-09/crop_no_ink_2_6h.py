"""ROADMAP 2.6h — crops of every `no_ink_under_box` refusal from the
2.6h probe's crop-data JSON. PDF-only: no record access here (the one
record read already happened in the probe).

One band only (this rule needs no cross-staff comparison): the box's own
staff shaded pale grey, its lines drawn, a staff-space ruler down the left
edge. The box bracketed RED with thick corner arms -- Sean's own
correction (`benchmarks/omr-owner-domain-2026-09/FINDINGS.md` §2.6g,
2026-09-23): "there is a staff at the top and a staff at the bottom - i
dont know which staff the cell is focussing on" -- so the crop always
names the staff and draws its five lines, never leaves it in the gap
between two.

Frame control reused from `crop_losers_2_6b._frame_ok` (0 refused of N
attempted is not a pass -- see the manifest's own field).

    python3 benchmarks/omr-owner-domain-2026-09/crop_no_ink_2_6h.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from crop_losers_2_6b import _frame_ok  # noqa: E402

DATA = HERE / "out" / "2.6h" / "no-ink-2.6h-crop-data.json"
OUT_DIR = HERE / "out" / "print" / "2.6h-no-ink"
DPI = 600


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    data = json.loads(DATA.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=16)
    manifest, refused = [], []

    for rec_entry in data["records"]:
        if rec_entry.get("status") != "ok":
            continue
        rows = rec_entry.get("no_ink_under_box_rows", [])
        if not rows:
            continue
        pdf = rec_entry["pdf"]
        doc = fitz.open(pdf)
        pages = {}
        for row in rows:
            sub = row["subject"]
            p = int(sub.split("/")[1])
            bb = row["bbox_page_px"]
            lines = [float(y) for y in row["staff_lines"]]
            sp = float(row["staff_spacing"])
            if not bb or not lines or sp <= 0:
                refused.append({"subject": sub, "why": "geometry missing"})
                continue

            if p not in pages:
                pm = doc[p].get_pixmap(dpi=DPI)
                im = (Image.frombytes("RGB", (pm.width, pm.height),
                                      pm.samples)
                      if pm.n >= 3 else Image.frombytes(
                          "L", (pm.width, pm.height),
                          pm.samples).convert("RGB"))
                pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
            im, arr = pages[p]

            ok, contrast = _frame_ok(arr, lines, sp)
            shifted = [y + sp / 2.0 for y in lines]
            broken, contrast_b = _frame_ok(arr, shifted, sp)
            if not ok or broken:
                refused.append({
                    "subject": sub, "why": "FRAME CONTROL FAILED",
                    "contrast": round(contrast, 1),
                    "contrast_shifted": round(contrast_b, 1)})
                continue

            sp0 = sp
            xs = [bb[0], bb[2]]
            ys = [bb[1], bb[3]] + lines
            cx0 = int(max(0, min(xs) - 6 * sp0))
            cx1 = int(min(im.width, max(xs) + 6 * sp0))
            cy0 = int(max(0, min(ys) - 2.5 * sp0))
            cy1 = int(min(im.height, max(ys) + 2.5 * sp0))
            Z = 3
            crop = im.crop((cx0, cy0, cx1, cy1)).resize(
                ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
            ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            top = (min(lines) - cy0) * Z
            bot = (max(lines) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=(150, 150, 150, 55))
            for ly in lines:
                y = (ly - cy0) * Z
                od.line([(0, y), (crop.width, y)], fill=(60, 60, 60, 220),
                        width=3)
            crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert(
                "RGB")
            dr = ImageDraw.Draw(crop)
            # a staff-space ruler down the left edge
            y = cy0
            while y <= cy1:
                yy = (y - cy0) * Z
                dr.line([(0, yy), (14, yy)], fill=(0, 0, 0), width=2)
                y += sp0
            # the box, bracketed red
            bx0, by0 = (bb[0] - cx0) * Z, (bb[1] - cy0) * Z
            bx1, by1 = (bb[2] - cx0) * Z, (bb[3] - cy0) * Z
            arm = max(10, int((bx1 - bx0) * 0.5))
            for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                   (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0),
                        width=6)
                dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0),
                        width=6)
            ink_raw = row.get("ink_raw") or {}
            ink_net = row.get("ink_net") or {}
            n = len(manifest) + 1
            name = f"2.6h-no-ink-{n:02d}.png"
            title = [
                (f"{name}  {sub}  {rec_entry['label']} pdf idx {p}  "
                 f"class={row['class']}", (0, 0, 0)),
                (f"REFUSED no_ink_under_box  raw.best="
                 f"{ink_raw.get('best')} ({ink_raw.get('best_window')})  "
                 f"net.best={ink_net.get('best')} "
                 f"({ink_net.get('best_window')})", (150, 0, 0)),
                ("Q: is there any real mark under the red box at all?",
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
                "record": rec_entry["label"], "page": p,
                "class": row["class"],
                "ink_raw": ink_raw, "ink_net": ink_net,
                "frame_contrast": round(contrast, 1),
                "frame_contrast_shifted_half_space": round(contrast_b, 1),
                "question": "is there any real mark under the red box at "
                            "all?",
                "VERDICT_none_yet": None})

    print(f"crops {len(manifest)}  refused {len(refused)}")
    (OUT_DIR / "2.6h-no-ink-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6h", "dpi": DPI,
        "crops": manifest, "refused": refused}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
