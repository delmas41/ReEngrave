#!/usr/bin/env python3
"""Render one FULL-WIDTH STAFF STRIP per pair, marking BOTH heads.

⚠️ THE QUESTION IS ABOUT TWO HEADS, SO TWO HEADS ARE MARKED. The sibling lane
asks *"is this stroke this head's stem"* and marks one head; this lane asks
*"do these two heads share ONE stem"*, which cannot be posed with a single
mark. RED is the head the record leaves STEMLESS, BLUE the head it already
joins to the stroke. The colours are not stated to the adjudicator as meaning
anything -- the manifest holds which is which.

⚠️ EVERYTHING ELSE IS THE SIBLING'S AND IS IMPORTED, NOT RESTATED: the strip
geometry, the NEAREST upscale, the margin-tick convention, the corner-bracket
marking (an annotation over the ink is an annotation over the evidence), and
above all `_frame_ok`, whose own docstring records that it must be asked of the
PAGE and not of the strip. A second copy of a control that has already been
got wrong once would be free to get it wrong again.

⚠️ THE RECORD IS STREAMED. The Breitkopf record is 443 MB and the sibling's
tool `json.load`s it; that is affordable there and is not something to copy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stream_array  # noqa: E402

_SIB = (Path(__file__).resolve().parents[1].parent
        / "omr-stem-attribution-2026-09" / "crop_strips.py")
_spec = importlib.util.spec_from_file_location("_sibling_crop", _SIB)
_sib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sib)

PAD_Y_SPACES = _sib.PAD_Y_SPACES
MARGIN_FRAC = _sib.MARGIN_FRAC
PX_PER_SPACE = _sib.PX_PER_SPACE
CONTEXT_X_SPACES = _sib.CONTEXT_X_SPACES
_frame_ok = _sib._frame_ok
_page_image = _sib._page_image

RED = [220, 0, 0]
BLUE = [0, 90, 220]


def _corner_marks(img, page_box, x0, y0, sc, colour):
    """Four corner brackets OUTSIDE the box, so the ink stays unobscured."""
    h, w = img.shape[:2]
    gap = PX_PER_SPACE * 0.22
    arm = int(PX_PER_SPACE * 0.40)
    th = max(2, int(PX_PER_SPACE * 0.07))
    bx0 = int((page_box[0] - x0) * sc - gap)
    bx1 = int((page_box[2] - x0) * sc + gap)
    by0 = int((page_box[1] - y0) * sc - gap)
    by1 = int((page_box[3] - y0) * sc + gap)

    def paint(ya, yb, xa, xb):
        ya, yb = max(0, ya), min(h, yb)
        xa, xb = max(0, xa), min(w, xb)
        if yb > ya and xb > xa:
            img[ya:yb, xa:xb] = colour

    for cx, dx in ((bx0, 1), (bx1, -1)):
        for cy, dy in ((by0, 1), (by1, -1)):
            paint(cy if dy > 0 else cy - th, cy + th if dy > 0 else cy,
                  cx if dx > 0 else cx - arm, cx + arm if dx > 0 else cx)
            paint(cy if dy > 0 else cy - arm, cy + arm if dy > 0 else cy,
                  cx if dx > 0 else cx - th, cx + th if dx > 0 else cx)
    return 0 <= (bx0 + bx1) // 2 < w


def _geometry(record, cells_wanted):
    """staff lines / spacing / the page boxes of each wanted cell, streamed."""
    lines_of, spacing_of, cellbox_of = {}, {}, {}
    for o in stream_array(record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            try:
                spacing_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if not (bp and len(bp) == 4):
                continue
            parts = o["subject"].split("/")
            if len(parts) < 5:
                continue
            key = "cell/" + "/".join(parts[1:5])
            if key in cells_wanted:
                cellbox_of.setdefault(key, []).append([float(x) for x in bp])
    return lines_of, spacing_of, cellbox_of


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    # ⚠️ A ZOOM IS A SECOND VIEW, NEVER A REPLACEMENT. The wide strip is an
    # instruction from a paid-for mistake (a numeral and a dotted half note
    # each read as a hollow head with no stem at tile magnification), so the
    # wide render is always taken; this narrows the SAME window for a pair the
    # wide view leaves ambiguous, and both are kept.
    ap.add_argument("--context-x", type=float, default=CONTEXT_X_SPACES)
    ap.add_argument("--pad-y", type=float, default=PAD_Y_SPACES)
    ap.add_argument("--only", nargs="*", default=None,
                    help="restrict to these subject keys")
    a = ap.parse_args()

    import numpy as np
    from PIL import Image

    sample = json.loads(Path(a.sample).read_text())
    rows = sample["rows"]
    if a.only:
        keep = set(a.only)
        rows = [r for r in rows
                if r["subject"] in keep or r["mate"] in keep]
    print(f"{sample['label']}: {len(rows)} pairs "
          f"({sample['n_candidates']} candidates, "
          f"{sample['n_controls_drawn']} controls)", flush=True)

    cells = {"cell/" + "/".join(r["subject"].split("/")[1:5]) for r in rows}
    lines_of, spacing_of, cellbox_of = _geometry(a.record, cells)

    pages = sorted({int(r["subject"].split("/")[1]) for r in rows})
    imgs = {p: _page_image(a.pdf, p, a.dpi) for p in pages}
    print(f"  rendered pages {pages}", flush=True)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles, refused = [], []
    for r in rows:
        parts = r["subject"].split("/")
        page, sysx, stx, cellx = (int(parts[1]), int(parts[2]),
                                  int(parts[3]), int(parts[4]))
        staff_key = f"staff/{page}/{sysx}/{stx}"
        cell_key = f"cell/{page}/{sysx}/{stx}/{cellx}"
        lines, sp = lines_of.get(staff_key), spacing_of.get(staff_key)
        if not lines or not sp:
            refused.append({"subject": r["subject"], "why": "no staff geometry"})
            continue
        boxes = cellbox_of.get(cell_key) or []
        if not boxes:
            refused.append({"subject": r["subject"], "why": "no page boxes"})
            continue

        red, blue = r["red_page_box"], r["blue_page_box"]
        bx0 = min(min(b[0] for b in boxes), red[0], blue[0])
        bx1 = max(max(b[2] for b in boxes), red[2], blue[2])
        hcx = (red[0] + red[2]) / 2.0
        pad_x = 4.0 * sp
        if a.context_x >= CONTEXT_X_SPACES:
            x0 = max(0, int(min(bx0 - pad_x, hcx - a.context_x * sp)))
            x1 = int(max(bx1 + pad_x, hcx + a.context_x * sp))
        else:
            # ZOOM: the window is the two heads plus the named reach.
            x0 = max(0, int(min(red[0], blue[0]) - a.context_x * sp))
            x1 = int(max(red[2], blue[2]) + a.context_x * sp)
        y0 = max(0, int(min(min(lines) - a.pad_y * sp, red[1], blue[1])))
        y1 = int(max(max(lines) + a.pad_y * sp, red[3], blue[3]))

        arr = imgs[page]
        crop = arr[y0:y1, x0:x1]
        if crop.size == 0:
            refused.append({"subject": r["subject"], "why": "empty crop"})
            continue
        ok, d = _frame_ok(arr, lines, sp)       # ⚠️ the PAGE, not the crop
        if not ok:
            refused.append({"subject": r["subject"],
                            "why": f"frame control failed (delta {d:.1f})"})
            continue

        img = (crop if crop.ndim == 3
               else np.stack([crop] * 3, axis=-1)).astype(np.uint8)
        sc = PX_PER_SPACE / sp
        pil = Image.fromarray(img).resize(
            (max(1, int(img.shape[1] * sc)), max(1, int(img.shape[0] * sc))),
            Image.NEAREST)
        img = np.asarray(pil).copy()
        h, w = img.shape[:2]

        hx = int((hcx - x0) * sc)
        band = max(2, int(h * MARGIN_FRAC))
        if not (0 <= hx < w):
            refused.append({"subject": r["subject"],
                            "why": "the marked head is outside its own bar"})
            continue
        tw = max(2, int(PX_PER_SPACE * 0.06))
        img[0:band, max(0, hx - tw):hx + tw] = RED
        img[h - band:h, max(0, hx - tw):hx + tw] = RED

        in_red = _corner_marks(img, red, x0, y0, sc, RED)
        in_blue = _corner_marks(img, blue, x0, y0, sc, BLUE)
        if not (in_red and in_blue):
            refused.append({"subject": r["subject"],
                            "why": "a marked head fell outside the strip"})
            continue

        tid = hashlib.sha1(
            f"{sample['seed']}|{r['subject']}|{r['mate']}|{r['stem']}".encode()
        ).hexdigest()[:10]
        Image.fromarray(img).save(out_dir / f"{tid}.png")
        tiles.append({"id": tid, "subject": r["subject"], "mate": r["mate"],
                      "stem": r["stem"], "stratum": r["stratum"],
                      "x_gap_head_widths": r["x_gap_head_widths"],
                      "dy_head_heights": r["dy_head_heights"],
                      "frame_delta": round(d, 1)})

    man = {"label": sample["label"], "seed": sample["seed"],
           "question": sample["question"],
           "verdicts_allowed": sample["verdicts_allowed"],
           "dpi": a.dpi, "px_per_space": PX_PER_SPACE, "resample": "NEAREST",
           "red_is": "the head the record leaves STEMLESS",
           "blue_is": "the head the record already joins to the stroke",
           "written": len(tiles), "refused": refused, "tiles": tiles}
    Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(a.manifest).write_text(json.dumps(man, indent=1))

    print(f"  wrote {len(tiles)} strips, refused {len(refused)}")
    for x in refused[:8]:
        print(f"    refused {x['subject']}: {x['why']}")
    if not tiles:
        print("⚠️ DEAD: no strip was written.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
