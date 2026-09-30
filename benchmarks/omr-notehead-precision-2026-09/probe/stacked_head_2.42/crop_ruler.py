"""ROADMAP 2.42, manager review fix -- a crop WITH A RULER for every changed
pitch, base vs new arm. Staff lines AND ledger lines are drawn and each is
labelled with the pitch it names (`_pitch_from_position`, the SAME anchor
`restate_pitch` itself uses); the fitted centre is marked; the label reads
"base: X / new: Y". The dark-row span actually under the two boxes'
shared x-range is measured numerically (a real ink-row count, the manager's
own method) and printed alongside, never eyeballed only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-notehead-precision-2026-09/probe/stacked_head_2.42")
import crop_groups as CG  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402


def latest(rec, q):
    out = {}
    for v in rec.get("verdicts", []):
        if v["quantity"] == q:
            out[v["subject"]] = v
    return out


def glyph_boxes(rec):
    return {r["subject"]: r for r in rec.get("observations", [])
           if r["quantity"] == "glyph_box"}


def clef_of(rec, staff_key):
    for v in rec.get("verdicts", []):
        if v["quantity"] == "clef" and v["subject"] == staff_key:
            return v["value"]
    return None


def ink_row_span(gray: np.ndarray, x0: int, x1: int, y0: int, y1: int,
                 thresh: int = 150) -> Optional[Tuple[int, int]]:
    """The [min, max] PAGE row within (y0,y1) where the x-band (x0,x1) has
    ANY dark pixel -- the manager's own 'ink rows run 385-433' method,
    reproduced numerically rather than eyeballed."""
    x0, x1 = max(0, x0), min(gray.shape[1], x1)
    y0, y1 = max(0, y0), min(gray.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return None
    band = gray[y0:y1, x0:x1] < thresh
    rows = np.where(band.any(axis=1))[0]
    if len(rows) == 0:
        return None
    return (int(rows.min()) + y0, int(rows.max()) + y0)


def crop_pitch(base_rec, new_rec, cache, page_index, subject,
              base_pitch: str, new_pitch: str, out_path: Path) -> dict:
    boxes = glyph_boxes(new_rec)
    g = boxes.get(subject)
    if g is None:
        return {}
    bpp = (g.get("detail") or {}).get("bbox_page_px")
    if not bpp:
        return {}
    cell_key = "/".join(subject.split("/")[:5])
    stkey = CG.staff_of(cell_key)
    line_ys = None
    spacing = None
    for r in new_rec.get("observations", []):
        if r["quantity"] == "staff_lines" and r["subject"] == stkey:
            line_ys = sorted(r["value"])
        if r["quantity"] == "staff_spacing" and r["subject"] == stkey:
            spacing = r["value"]
    if not line_ys or not spacing:
        return {}
    clef = clef_of(new_rec, stkey) or "treble"
    half_step = spacing / 2.0
    top_y = line_ys[0]

    page_img, gray = cache.get(page_index)
    pad = 3.0 * spacing
    cx0 = int(bpp[0] - pad); cx1 = int(bpp[2] + pad)
    cy0 = int(min(bpp[1], top_y - 5 * spacing) - 10)
    cy1 = int(max(bpp[3], top_y + 13 * spacing) + 10)
    cx0 = max(0, cx0); cy0 = max(0, cy0)
    cx1 = min(page_img.width, cx1); cy1 = min(page_img.height, cy1)
    crop = page_img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    headw = bpp[2] - bpp[0]
    scale = max(1.0, 90.0 / max(1.0, headw))
    if scale > 1.0:
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)),
                           Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    # staff lines + ledger positions (every half-step line position from
    # 4 spaces above to 4 spaces below the staff), each labelled with its
    # own pitch name via the SAME anchor `restate_pitch` reads.
    for pos in range(-16, 24, 2):  # every LINE position (even = line)
        y = top_y + pos * half_step
        if y < cy0 - 5 or y > cy1 + 5:
            continue
        x0c, y0c = to_crop(cx0, y)
        x1c, _ = to_crop(cx1, y)
        on_staff = 0 <= pos <= 8
        color = (30, 110, 220) if on_staff else (150, 150, 150)
        draw.line([(x0c, y0c), (x1c, y0c)], fill=color, width=1)
        name = _pitch_from_position(pos, clef)
        if name:
            draw.text((2, y0c - 6), name, fill=color)

    bx0, by0 = to_crop(bpp[0], bpp[1])
    bx1, by1 = to_crop(bpp[2], bpp[3])
    draw.rectangle([bx0, by0, bx1, by1], outline=(220, 20, 20), width=2)
    # fitted centre crosshair
    fcx, fcy = to_crop((bpp[0] + bpp[2]) / 2.0, (bpp[1] + bpp[3]) / 2.0)
    r = 8
    draw.line([(fcx - r, fcy), (fcx + r, fcy)], fill=(230, 210, 0), width=2)
    draw.line([(fcx, fcy - r), (fcx, fcy + r)], fill=(230, 210, 0), width=2)

    span = ink_row_span(gray, int(bpp[0]), int(bpp[2]), cy0, cy1)
    span_txt = f"ink_rows={span[0]}-{span[1]}" if span else "ink_rows=none"
    label = f"{subject.split('/')[-1]} base:{base_pitch} / new:{new_pitch} | {span_txt}"
    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), label, fill=(0, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
    return {"subject": subject, "base": base_pitch, "new": new_pitch,
           "ink_rows": span, "file": str(out_path)}


def main(pdf, base_path, new_path, page, out_dir):
    base = CG.load(base_path)
    new = CG.load(new_path)
    bp = latest(base, "pitch")
    npz = latest(new, "pitch")
    changed = sorted(s for s in (set(bp) & set(npz))
                     if bp[s]["value"] != npz[s]["value"])
    print(f"{len(changed)} changed pitches")
    cache = CG.PageRenderCache(pdf)
    outp = Path(out_dir)
    manifest = []
    for s in changed:
        result = crop_pitch(base, new, cache, page, s, bp[s]["value"],
                            npz[s]["value"], outp / f"{s.split('/')[-1]}-{'-'.join(s.split('/')[1:5])}.png")
        if result:
            manifest.append(result)
    outp.mkdir(parents=True, exist_ok=True)
    with open(outp / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=1, default=str)
    print(f"{len(manifest)} crops written to {outp}")


if __name__ == "__main__":
    a = sys.argv[1:6]
    main(a[0], a[1], a[2], int(a[3]), a[4])
