"""ROADMAP 2.42 print check -- crop every STACKED-HEAD GROUP the new arm's
record carries: staff lines drawn (blue), every box in its own colour (green
= kept, red = refused `stacked_head_duplicate`, grey = a group member this
rule did not touch), and the fitted slot centres marked with a yellow
crosshair at each DECIDED position.

Reads the record via `record_io.load_record` ONLY (never re-gathers), and
renders the source PDF fresh at 600 dpi (`tools.omr.preprocessing.
render_page`) for the crop pixels themselves -- the record never carries
`image_no_staff`. `bbox_page_px` (every `Q.GLYPH_BOX` row already carries it)
is the ONLY page-frame fact this script needs; the crosshair's own page
position is recovered from the SAME per-cell canonical->page affine
`crop_pairs.py` (2.40) already established, fit from this cell's own
`Q.GLYPH_BOX` rows rather than assumed.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import record_io  # noqa: E402


def load(record_path: str) -> Dict[str, Any]:
    return record_io.load_record(record_path)["record"]


def rows(rec: Dict[str, Any], quantity: str, kind: str = "observations"):
    return [r for r in rec.get(kind, []) if r["quantity"] == quantity]


def latest_verdicts(rec: Dict[str, Any], quantity: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for v in rows(rec, quantity, kind="verdicts"):
        out[v["subject"]] = v
    return out


def staff_of(cell_key: str) -> str:
    parts = cell_key.split("/")
    return "/".join(["staff"] + parts[1:4])


def build_groups(rec: Dict[str, Any]) -> Dict[Tuple[str, str, str], List[dict]]:
    """`(cell_key, stem_id, side) -> [Q.STACKED_HEAD_FIT observation, ...]`."""
    groups: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for r in rows(rec, "stacked_head_fit"):
        subj = r["subject"]
        cell_key = "/".join(subj.split("/")[:5])
        d = r.get("detail") or {}
        key = (cell_key, d.get("stem"), d.get("side"))
        groups[key].append(r)
    return groups


class PageRenderCache:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._cache: Dict[int, Any] = {}

    def get(self, page_index: int):
        if page_index not in self._cache:
            print(f"rendering page {page_index} at 600 dpi ...")
            pi = render_page(self.pdf_path, page_index, dpi=600)
            arr = getattr(pi, "rgb", None)
            if arr is None:
                arr = getattr(pi, "binary")
            arr_np = np.asarray(arr)
            if arr_np.ndim == 2:
                gray = arr_np.astype(float)
                base_rgb = np.stack([arr_np] * 3, axis=-1)
            else:
                gray = arr_np.mean(axis=2)
                base_rgb = arr_np
            img = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")
            self._cache[page_index] = (img, gray)
        return self._cache[page_index]


_affine_cache: Dict[str, Optional[dict]] = {}


def cell_affine(rec: Dict[str, Any], cell_key: str) -> Optional[dict]:
    if cell_key in _affine_cache:
        return _affine_cache[cell_key]
    xs_c, xs_p, ys_c, ys_p = [], [], [], []
    prefix = cell_key + "/"
    for r in rows(rec, "glyph_box"):
        if not r["subject"].startswith(prefix):
            continue
        v = r["value"]
        bpp = (r.get("detail") or {}).get("bbox_page_px")
        if not bpp or not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        xs_c.append(v[1]); xs_p.append(bpp[0])
        ys_c.append(v[2]); ys_p.append(bpp[1])
    if len(xs_c) < 2:
        _affine_cache[cell_key] = None
        return None
    A = np.vstack([np.array(xs_c), np.ones(len(xs_c))]).T
    (inv_up_x, x0p), *_ = np.linalg.lstsq(A, np.array(xs_p), rcond=None)
    A2 = np.vstack([np.array(ys_c), np.ones(len(ys_c))]).T
    (inv_up_y, y0p), *_ = np.linalg.lstsq(A2, np.array(ys_p), rcond=None)
    result = dict(inv_up_x=float(inv_up_x), x0p=float(x0p),
                  inv_up_y=float(inv_up_y), y0p=float(y0p))
    _affine_cache[cell_key] = result
    return result


def canon_to_page(aff: dict, x: float, y: float) -> Tuple[float, float]:
    return (aff["x0p"] + x * aff["inv_up_x"], aff["y0p"] + y * aff["inv_up_y"])


def ink_pct(gray: np.ndarray, box: Tuple[float, float, float, float]) -> Optional[float]:
    x0, y0, x1, y1 = (int(v) for v in box)
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(gray.shape[1], x1); y1 = min(gray.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return None
    region = gray[y0:y1, x0:x1]
    return float((region < 150).mean()) * 100.0


def crop_group(rec: Dict[str, Any], cache: PageRenderCache, page_index: int,
              cell_key: str, members: List[dict],
              refused_reasons: Dict[str, dict], out_path: Path, tag: str
              ) -> dict:
    boxes_by_subj: Dict[str, dict] = {r["subject"]: r for r in rows(rec, "glyph_box")}
    stkey = staff_of(cell_key)
    line_ys = None
    spacing = None
    for r in rows(rec, "staff_lines"):
        if r["subject"] == stkey:
            line_ys = r["value"]
    for r in rows(rec, "staff_spacing"):
        if r["subject"] == stkey:
            spacing = r["value"]
    spacing = spacing or 60.0

    page_img, gray = cache.get(page_index)
    aff = cell_affine(rec, cell_key)

    page_boxes = []
    for m in members:
        subj = m["subject"]
        g = boxes_by_subj.get(subj)
        if g is None:
            continue
        bpp = (g.get("detail") or {}).get("bbox_page_px")
        if not bpp:
            continue
        page_boxes.append((subj, bpp))
    if not page_boxes:
        return {}

    all_x = [b[0] for _, b in page_boxes] + [b[2] for _, b in page_boxes]
    all_y = [b[1] for _, b in page_boxes] + [b[3] for _, b in page_boxes]
    pad = 3.0 * spacing
    cx0 = max(0, int(min(all_x) - pad))
    cx1 = min(page_img.width, int(max(all_x) + pad))
    cy0 = max(0, int(min(all_y) - pad))
    cy1 = min(page_img.height, int(max(all_y) + pad))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 10))
        cy1 = max(cy1, int(max(line_ys) + 10))
    crop = page_img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    headw = page_boxes[0][1][2] - page_boxes[0][1][0]
    scale = max(1.0, 70.0 / max(1.0, headw))
    if scale > 1.0:
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)),
                           Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    if line_ys:
        for ly in line_ys:
            x0c, y0c = to_crop(cx0, ly)
            x1c, y1c = to_crop(cx1, ly)
            draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

    fit_by_subj = {m["subject"]: m for m in members}
    legend = []
    ink_report = {}
    for i, (subj, bpp) in enumerate(page_boxes):
        refused = refused_reasons.get(subj)
        color = (220, 20, 20) if refused else (20, 160, 60)
        bx0, by0 = to_crop(bpp[0], bpp[1])
        bx1, by1 = to_crop(bpp[2], bpp[3])
        draw.rectangle([bx0, by0, bx1, by1], outline=color, width=2)
        # ⚠️ TWO DIFFERENT NUMBERS, LABELLED APART. `pct` is this script's
        # OWN crude raw-darkness measure over the full detector box -- a
        # rough visual cross-check, NOT what the decision read. `decided`
        # is `Q.STACKED_HEAD_FIT.detail["ink"]`, the ACTUAL staff-line-
        # erased fill the keep/refuse choice was made from (measured at the
        # FITTED standard box, not the raw detector box) -- reporting only
        # `pct` here once made a refused box look wrong when the real
        # decision was right (Brahms `glyph/1/0/2/0/35`: raw 97% vs kept
        # 80%, decided 0.94 vs 1.00 -- the raw measure disagrees with the
        # decision because it is a DIFFERENT window over DIFFERENT ink).
        pct = ink_pct(gray, bpp)
        decided = (fit_by_subj.get(subj, {}).get("detail") or {}).get("ink")
        ink_report[subj] = {"raw_box_pct": pct, "decided_ink": decided}
        short = subj.split("/")[-1]
        decided_txt = f"{decided:.2f}" if decided is not None else "none"
        tagtxt = (f"g{short}:{'REFUSED' if refused else 'kept'}:"
                 f"decided={decided_txt}/raw={pct:.0f}%")
        legend.append(tagtxt)

    # fitted slot centres -- yellow crosshair, in PAGE frame via the cell's
    # own canonical->page affine (None where too few glyph_box rows exist to
    # fit one -- drawn without a crosshair rather than guessed).
    if aff is not None:
        seen_positions = set()
        for m in members:
            val = m["value"]
            if not isinstance(val, (list, tuple)) or len(val) != 4:
                continue
            slot_pos = val[2]
            if slot_pos in seen_positions:
                continue
            seen_positions.add(slot_pos)
            d = m.get("detail") or {}
            # x from this member's own box (same side/x column); y from the
            # fitted half-step position against the STAFF's own top line.
            subj = m["subject"]
            g = boxes_by_subj.get(subj)
            if g is None:
                continue
            gx, gy, gw, gh = g["value"][1:5]
            cx_canon = gx + gw / 2.0
            top_y = min(line_ys) if line_ys else None
            # half_step in PAGE px: spacing (page) / 2
            half_step_page = spacing / 2.0
            if top_y is None:
                continue
            fitted_cy_canon = None
            # Recover the CANONICAL y the slot corresponds to via the
            # affine's own y-mapping inverted from the PAGE-frame top line.
            # page_y = y0p + y_canon * inv_up_y  =>  y_canon = (page_y -
            # y0p) / inv_up_y. The fitted position is defined in PAGE
            # half-steps (this script's own top_y/half_step_page), so the
            # crosshair is placed directly in PAGE frame -- no canonical
            # round-trip needed for y.
            page_cy = top_y + slot_pos * half_step_page
            page_cx, _ = canon_to_page(aff, cx_canon, gy)
            px, py = to_crop(page_cx, page_cy)
            r = 8
            draw.line([(px - r, py), (px + r, py)], fill=(230, 210, 0), width=3)
            draw.line([(px, py - r), (px, py + r)], fill=(230, 210, 0), width=3)

    label = f"{tag} | " + " ".join(legend)
    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), label[:180], fill=(0, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
    return {"tag": tag, "file": str(out_path), "members": list(ink_report),
           "ink": ink_report, "legend": legend}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("record")
    ap.add_argument("page", type=int)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--changed-only", action="store_true",
                    help="only groups with >=1 refused member")
    ap.add_argument("--sample", type=int, default=None,
                    help="random sample of N groups instead of all")
    ap.add_argument("--seed", type=int, default=2042)
    args = ap.parse_args(argv)

    rec = load(args.record)
    refused = {s: v for s, v in latest_verdicts(rec, "notehead_is_not_a_notehead").items()
              if v["reason"] == "stacked_head_duplicate"}
    groups = build_groups(rec)
    keys = sorted(groups)
    if args.changed_only:
        keys = [k for k in keys
               if any(m["subject"] in refused for m in groups[k])]
    if args.sample is not None:
        rng = random.Random(args.seed)
        keys = rng.sample(keys, min(args.sample, len(keys)))

    cache = PageRenderCache(args.pdf)
    out_dir = Path(args.out_dir)
    manifest = []
    for i, key in enumerate(keys):
        cell_key, stem_id, side = key
        members = groups[key]
        tag = f"G{i+1:02d}-{cell_key.replace('/', '-')}-{side}"
        out_path = out_dir / f"{tag}.png"
        result = crop_group(rec, cache, args.page, cell_key, members,
                            refused, out_path, tag)
        if result:
            manifest.append(result)
            print(tag, result["legend"])
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=1, default=str)
    print(f"{len(manifest)} crops written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
