"""ROADMAP 2.41 -- three readings of a notehead's centre, side by side.

Sean, 2026-09-30: "I am worried that the ledger lines and other ink are not
as reliable as pure geometry. If the center of each note head can be
determined by the ink of the note head, it could be measured from the
center of the staff. I'm not sure if that is more reliable or not."

MEASUREMENT ONLY -- nothing under tools/ is touched, nothing is wired.
Reads a record via `tools.omr.staged.record_io.load_record` ONLY, for
`glyph_box`/`staff_lines`/`staff_spacing` observations (all already in PAGE
PIXEL frame -- see `record.py` Q.STAFF_LINES's own comment, "5 y positions,
page px" -- so no cell-frame/canonical-frame conversion is needed anywhere
in this script). The ink raster used for readings B and C is NOT the
record's `cell.image_no_staff` (that array is never serialised to the
record file -- CLAUDE.md §4b/§9, ~115 MB/page, roadmap 1.1 persists a
summary instead) but a fresh 600 dpi render of the SAME page via PyMuPDF,
in the SAME page-pixel frame `bbox_page_px` already uses -- the same
approach `probe/crop_2.39b.py` takes for its crops, extended here with a
thresholded ink mask and a local staff-line suppression (below).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN:
  - The template's tilt angle (18 degrees) is this script's own choice --
    the brief names Bravura's proportions but the conventions registry
    (`tools/omr/conventions.py`) has no notehead width/tilt entry (checked,
    absent). Falsified by a sample crop where the ink's own long axis is
    not close to 18 degrees.
  - Staff-line suppression here is a LOCAL long-horizontal-run opening
    (`scipy.ndimage.binary_opening`, kernel width ~1.3 staff spaces),
    applied only within a few px of each FILED line y. It is not the same
    algorithm GATHER's own `image_no_staff` uses (that algorithm is not
    reused here -- it lives inside `preprocessing.py` bound to the
    detector's own cell-cut pipeline) -- falsified by a plate where a
    genuine thick notehead sits so close to a line that this opening
    erases real head ink along with the line.
  - The ink threshold (gray < 170) is a fixed constant, not measured per
    page -- falsified by a page whose scan contrast puts real ink above it
    or noise below it.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, ".")
from tools.omr.staged import geometry as GEOM  # noqa: E402
from tools.omr.staged import record_io  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────
# Record access
# ─────────────────────────────────────────────────────────────────────────

def _rows(record: dict, quantity: str, subject: str, kind: str = "observations"):
    return [r for r in record[kind]
            if r["quantity"] == quantity and r["subject"] == subject]


def load_noteheads(record_path: str) -> Tuple[List[dict], Dict[str, dict]]:
    """Every REGULAR notehead's glyph_box row, plus a `{staff_key: (line_ys,
    spacing)}` map, both read via `record_io.load_record` only."""
    data = record_io.load_record(record_path)
    record = data["record"]
    staves: Dict[str, dict] = {}
    heads: List[dict] = []
    box_rows = [r for r in record["observations"] if r["quantity"] == "glyph_box"]
    for row in box_rows:
        name = row["value"][0]
        if not GEOM.is_regular_notehead(name):
            continue
        detail = row.get("detail") or {}
        page_box = detail.get("bbox_page_px")
        if not page_box:
            continue
        parts = row["subject"].split("/")
        page, system, staff_idx, cell, glyph = (int(x) for x in parts[1:6])
        staff_key = f"staff/{page}/{system}/{staff_idx}"
        heads.append({
            "subject": row["subject"], "name": name,
            "page": page, "staff_key": staff_key,
            "bbox_page_px": [float(v) for v in page_box],
            "hollow": name.startswith("noteheadHalf"),
        })
        staves.setdefault(staff_key, None)
    for staff_key in list(staves):
        page, system, staff_idx = (int(x) for x in staff_key.split("/")[1:4])
        lines_rows = _rows(record, "staff_lines", staff_key)
        sp_rows = _rows(record, "staff_spacing", staff_key)
        if not lines_rows or not sp_rows:
            staves[staff_key] = None
            continue
        line_ys = sorted(float(v) for v in lines_rows[-1]["value"])
        spacing = float(sp_rows[-1]["value"])
        staves[staff_key] = {"line_ys": line_ys, "spacing": spacing}
    heads = [h for h in heads if staves.get(h["staff_key"])]
    return heads, staves


# ─────────────────────────────────────────────────────────────────────────
# Page raster: render + ink mask + local staff-line suppression
# ─────────────────────────────────────────────────────────────────────────

INK_THRESHOLD = 170  # gray < this counts as ink


def render_page_ink(pdf_path: str, page_index: int, dpi: int = 600
                    ) -> np.ndarray:
    doc = fitz.open(pdf_path)
    pm = doc[page_index].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
    doc.close()
    return arr  # grayscale, 0=black .. 255=white


def suppress_staff_lines(ink: np.ndarray, staves: Dict[str, dict],
                          heads_by_staff: Dict[str, List[dict]]
                         ) -> np.ndarray:
    """`ink` is a boolean array (True==ink). Returns a COPY with staff-line
    ink erased near each staff's filed line y's -- a long horizontal run
    (`binary_opening`, wide kernel) close to a filed line is a staff line;
    ink that does not survive that opening (a notehead blob, a stem) is
    left untouched even if it happens to touch the same row."""
    out = ink.copy()
    H, W = ink.shape
    for staff_key, geo in staves.items():
        if geo is None:
            continue
        spacing = geo["spacing"]
        kernel_w = max(3, int(round(spacing * 1.3)))
        xs = [h["bbox_page_px"] for h in heads_by_staff.get(staff_key, [])]
        if not xs:
            continue
        x0 = max(0, int(min(b[0] for b in xs) - spacing * 2))
        x1 = min(W, int(max(b[2] for b in xs) + spacing * 2))
        if x1 <= x0:
            continue
        band = max(2, int(round(spacing * 0.15)))
        for ly in geo["line_ys"]:
            y0 = max(0, int(round(ly)) - band)
            y1 = min(H, int(round(ly)) + band + 1)
            if y1 <= y0:
                continue
            strip = out[y0:y1, x0:x1]
            opened = ndimage.binary_opening(
                strip, structure=np.ones((1, kernel_w), dtype=bool))
            out[y0:y1, x0:x1] = strip & ~opened
    return out


# ─────────────────────────────────────────────────────────────────────────
# Template: filled tilted oval (black head) or ring (hollow head)
# ─────────────────────────────────────────────────────────────────────────

TILT_DEGREES = 18.0
OVAL_W_SPACES = 1.18
OVAL_H_SPACES = 1.0
RING_OUTER_W_SPACES = 1.18
RING_OUTER_H_SPACES = 1.0
RING_INNER_FRAC = 0.55  # inner ellipse radius as a fraction of the outer
STEM_ALLOWANCE_W_SPACES = 0.15  # central vertical stripe excluded


def _ellipse_mask(shape: Tuple[int, int], cx: float, cy: float,
                   half_w: float, half_h: float, angle_deg: float
                  ) -> np.ndarray:
    H, W = shape
    ys, xs = np.mgrid[0:H, 0:W]
    dx = xs - cx
    dy = ys - cy
    th = math.radians(angle_deg)
    rx = dx * math.cos(th) + dy * math.sin(th)
    ry = -dx * math.sin(th) + dy * math.cos(th)
    return (rx / half_w) ** 2 + (ry / half_h) ** 2 <= 1.0


def template_score(ink: np.ndarray, cx: float, cy: float, spacing: float,
                    hollow: bool, window_radius_px: int
                   ) -> Optional[float]:
    """Mean ink fill under the template centred at `(cx, cy)`, within a
    local crop of `ink` (for speed); `None` off-raster. The stem allowance
    excludes a thin central vertical stripe from both fill and area."""
    H, W = ink.shape
    ix0 = max(0, int(cx) - window_radius_px)
    ix1 = min(W, int(cx) + window_radius_px)
    iy0 = max(0, int(cy) - window_radius_px)
    iy1 = min(H, int(cy) + window_radius_px)
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    local = ink[iy0:iy1, ix0:ix1]
    lcx, lcy = cx - ix0, cy - iy0
    hw = OVAL_W_SPACES * spacing / 2.0
    hh = OVAL_H_SPACES * spacing / 2.0
    stem_hw = STEM_ALLOWANCE_W_SPACES * spacing / 2.0
    outer = _ellipse_mask(local.shape, lcx, lcy, hw, hh, TILT_DEGREES)
    ys, xs = np.mgrid[0:local.shape[0], 0:local.shape[1]]
    stem_col = np.abs(xs - lcx) <= stem_hw
    if hollow:
        inner = _ellipse_mask(local.shape, lcx, lcy, hw * RING_INNER_FRAC,
                              hh * RING_INNER_FRAC, TILT_DEGREES)
        mask = outer & ~inner & ~stem_col
    else:
        mask = outer & ~stem_col
    area = mask.sum()
    if area == 0:
        return None
    return float(local[mask].sum()) / float(area)


# ─────────────────────────────────────────────────────────────────────────
# Reading A -- detector box centre, rounded
# ─────────────────────────────────────────────────────────────────────────

def reading_a(bbox: List[float], line_ys: List[float], spacing: float
             ) -> Tuple[float, int]:
    cy = (bbox[1] + bbox[3]) / 2.0
    top = line_ys[0]
    half_step = spacing / 2.0
    pos_float = (cy - top) / half_step
    return pos_float, int(round(pos_float))


# ─────────────────────────────────────────────────────────────────────────
# Reading B -- continuous template fit, bounded search around detector centre
# ─────────────────────────────────────────────────────────────────────────

MAX_DY_SPACES = 0.6
MAX_DX_SPACES = 0.4
STEP_SPACES = 0.05


def reading_b(ink: np.ndarray, bbox: List[float], line_ys: List[float],
              spacing: float, hollow: bool) -> Dict[str, Any]:
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    top = line_ys[0]
    half_step = spacing / 2.0
    window_radius_px = int(round(spacing * 1.2))
    n_dy = int(round(MAX_DY_SPACES / STEP_SPACES))
    n_dx = int(round(MAX_DX_SPACES / STEP_SPACES))
    best = None
    for iy in range(-n_dy, n_dy + 1):
        dy_sp = iy * STEP_SPACES
        ncy = cy + dy_sp * spacing
        for ix in range(-n_dx, n_dx + 1):
            dx_sp = ix * STEP_SPACES
            ncx = cx + dx_sp * spacing
            score = template_score(ink, ncx, ncy, spacing, hollow,
                                   window_radius_px)
            if score is None:
                continue
            if best is None or score > best[2]:
                best = (dx_sp, dy_sp, score)
    if best is None:
        return {"ok": False, "pos_float": None, "pos_round": None,
                "fill": None}
    dx_sp, dy_sp, fill = best
    b_cy = cy + dy_sp * spacing
    pos_float = (b_cy - top) / half_step
    return {"ok": True, "dx_sp": round(dx_sp, 3), "dy_sp": round(dy_sp, 3),
            "fill": round(fill, 4), "pos_float": pos_float,
            "pos_round": int(round(pos_float)),
            "cx": cx + dx_sp * spacing, "cy": b_cy}


# ─────────────────────────────────────────────────────────────────────────
# Reading C -- same template, scored only at discrete grid positions
# ─────────────────────────────────────────────────────────────────────────

#: Half-steps searched EACH SIDE of the detector's own rough position (not
#: an absolute grid from the staff's top line -- see reading_c's own
#: comment). 4 half-steps = 2 staff spaces: generous ledger range without
#: reaching a neighbouring system on either measured plate (CONVENTION
#: ASSUMED -- not measured against a minimum inter-system gap; falsified
#: by a plate where two systems sit closer than ~2 sp apart at the same x).
C_EXTEND_POSITIONS = 4
C_AMBIGUOUS_MARGIN = 0.05


def reading_c(ink: np.ndarray, bbox: List[float], line_ys: List[float],
              spacing: float, hollow: bool, fixed_cx: Optional[float] = None,
              anchor_pos: Optional[int] = None) -> Dict[str, Any]:
    cx = fixed_cx if fixed_cx is not None else (bbox[0] + bbox[2]) / 2.0
    top = line_ys[0]
    half_step = spacing / 2.0
    window_radius_px = int(round(spacing * 1.2))
    if anchor_pos is None:
        cy = (bbox[1] + bbox[3]) / 2.0
        anchor_pos = int(round((cy - top) / half_step))
    candidates = []
    # ⚠️ Bounded AROUND the detector's own rough position, not an absolute
    # grid from the top line -- an unbounded scan reaches into the next
    # staff/system's ink and "wins" there (measured: an early unbounded
    # version picked position -8/+13 against a detector centre of +9,
    # i.e. a different staff's head entirely). C_EXTEND_POSITIONS is the
    # ledger range PAST the note's own neighbourhood, not past the staff
    # in absolute terms.
    lo = anchor_pos - C_EXTEND_POSITIONS
    hi = anchor_pos + C_EXTEND_POSITIONS
    for pos in range(lo, hi + 1):
        ccy = top + pos * half_step
        score = template_score(ink, cx, ccy, spacing, hollow,
                               window_radius_px)
        if score is None:
            continue
        candidates.append((pos, score))
    if not candidates:
        return {"ok": False, "pos_round": None, "fill": None,
                "ambiguous": None}
    candidates.sort(key=lambda c: -c[1])
    best_pos, best_score = candidates[0]
    second_score = candidates[1][1] if len(candidates) > 1 else 0.0
    ambiguous = (best_score - second_score) < C_AMBIGUOUS_MARGIN
    return {"ok": True, "pos_round": best_pos, "fill": round(best_score, 4),
            "ambiguous": ambiguous,
            "runner_up_pos": candidates[1][0] if len(candidates) > 1 else None,
            "margin": round(best_score - second_score, 4)}


# ─────────────────────────────────────────────────────────────────────────
# Two-head fit: does the ink support ONE head or TWO, on one stem?
# ─────────────────────────────────────────────────────────────────────────

def two_head_fit(ink: np.ndarray, cx: float, line_ys: List[float],
                  spacing: float, hollow: bool, pos_low: int, pos_high: int
                 ) -> Dict[str, Any]:
    """Try placing two templates at staff-grid slots >=2 apart (a third or
    more) on the SAME x column, and compare the summed two-head score
    against the single best one-head score over the same y-range."""
    top = line_ys[0]
    half_step = spacing / 2.0
    window_radius_px = int(round(spacing * 1.2))
    single_best = None
    scores_by_pos = {}
    for pos in range(pos_low, pos_high + 1):
        ccy = top + pos * half_step
        s = template_score(ink, cx, ccy, spacing, hollow, window_radius_px)
        if s is None:
            continue
        scores_by_pos[pos] = s
        if single_best is None or s > single_best[1]:
            single_best = (pos, s)
    best_pair = None
    for p1 in scores_by_pos:
        for p2 in scores_by_pos:
            if p2 - p1 < 2:
                continue
            total = scores_by_pos[p1] + scores_by_pos[p2]
            if best_pair is None or total > best_pair[2]:
                best_pair = (p1, p2, total)
    return {
        "single_best_pos": single_best[0] if single_best else None,
        "single_best_score": round(single_best[1], 4) if single_best else None,
        "two_head_positions": (best_pair[0], best_pair[1]) if best_pair else None,
        "two_head_total_score": round(best_pair[2], 4) if best_pair else None,
        "two_head_mean_score": round(best_pair[2] / 2.0, 4) if best_pair else None,
        "supports_two_heads": bool(
            best_pair and single_best
            and (best_pair[2] / 2.0) > (single_best[1] - 0.05)
            and scores_by_pos.get(best_pair[0], 0) > 0.4
            and scores_by_pos.get(best_pair[1], 0) > 0.4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Main: measure one page
# ─────────────────────────────────────────────────────────────────────────

def measure_page(pdf_path: str, record_path: str, page_index: int,
                  dpi: int = 600) -> Dict[str, Any]:
    heads, staves = load_noteheads(record_path)
    page_heads = [h for h in heads if h["page"] == page_index]
    heads_by_staff: Dict[str, List[dict]] = {}
    for h in page_heads:
        heads_by_staff.setdefault(h["staff_key"], []).append(h)

    gray = render_page_ink(pdf_path, page_index, dpi=dpi)
    raw_ink = gray < INK_THRESHOLD
    clean_ink = suppress_staff_lines(raw_ink, staves, heads_by_staff)

    results = []
    for h in page_heads:
        geo = staves[h["staff_key"]]
        line_ys, spacing = geo["line_ys"], geo["spacing"]
        bbox = h["bbox_page_px"]
        hollow = h["hollow"]
        a_pos_float, a_pos = reading_a(bbox, line_ys, spacing)
        b = reading_b(clean_ink, bbox, line_ys, spacing, hollow)
        fixed_cx = b["cx"] if b["ok"] else (bbox[0] + bbox[2]) / 2.0
        c = reading_c(clean_ink, bbox, line_ys, spacing, hollow,
                      fixed_cx=fixed_cx, anchor_pos=a_pos)
        inside_staff = 0 <= a_pos <= 8
        row = {
            "subject": h["subject"], "name": h["name"], "hollow": hollow,
            "staff_key": h["staff_key"], "bbox_page_px": bbox,
            "spacing": spacing,
            "inside_staff": inside_staff,
            "a_pos_float": round(a_pos_float, 4), "a_pos": a_pos,
            "b_ok": b["ok"], "b_pos": b.get("pos_round"),
            "b_pos_float": (round(b["pos_float"], 4) if b.get("pos_float")
                           is not None else None),
            "b_fill": b.get("fill"), "b_dx_sp": b.get("dx_sp"),
            "b_dy_sp": b.get("dy_sp"),
            "c_ok": c["ok"], "c_pos": c.get("pos_round"),
            "c_fill": c.get("fill"), "c_ambiguous": c.get("ambiguous"),
            "c_margin": c.get("margin"),
        }
        results.append(row)

    return {
        "pdf": pdf_path, "record": record_path, "page": page_index,
        "n_regular_noteheads": len(page_heads),
        "rows": results,
        "_ink_cache_key": id(clean_ink),  # not serialised; for crop reuse
    }


def summarize(rows: List[dict]) -> Dict[str, Any]:
    def bucket(r):
        inside = "inside" if r["inside_staff"] else "ledger"
        colour = "hollow" if r["hollow"] else "black"
        return f"{inside}/{colour}"

    counts = {"all_agree": 0, "a_only_diff": 0, "b_only_diff": 0,
              "c_only_diff": 0, "all_diff": 0, "ab_agree_c_diff": 0,
              "ac_agree_b_diff": 0, "bc_agree_a_diff": 0,
              "b_or_c_unreadable": 0}
    by_bucket_agree = {}
    by_bucket_total = {}
    disagreements = []
    for r in rows:
        bk = bucket(r)
        by_bucket_total[bk] = by_bucket_total.get(bk, 0) + 1
        if not r["b_ok"] or not r["c_ok"]:
            counts["b_or_c_unreadable"] += 1
            continue
        a, b, c = r["a_pos"], r["b_pos"], r["c_pos"]
        if a == b == c:
            counts["all_agree"] += 1
            by_bucket_agree[bk] = by_bucket_agree.get(bk, 0) + 1
        else:
            disagreements.append(r)
            if a == b and b != c:
                counts["ab_agree_c_diff"] += 1
            elif a == c and a != b:
                counts["ac_agree_b_diff"] += 1
            elif b == c and a != b:
                counts["bc_agree_a_diff"] += 1
            else:
                counts["all_diff"] += 1
    by_bucket = {bk: {"agree": by_bucket_agree.get(bk, 0),
                      "total": by_bucket_total[bk]}
                for bk in by_bucket_total}
    return {"counts": counts, "by_bucket": by_bucket,
            "n_disagreements": len(disagreements),
            "n_total": len(rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("record")
    ap.add_argument("page", type=int)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    result = measure_page(args.pdf, args.record, args.page, dpi=args.dpi)
    result.pop("_ink_cache_key", None)
    summary = summarize(result["rows"])
    result["summary"] = summary
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"page": args.page, "n": result["n_regular_noteheads"],
                      "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
