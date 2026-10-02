#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02, Sean): measure the real notehead
TILT before building any geometry template -- "the oval should be at a
45% angle for the note head -- right?" Never assumed; measured per doc.

For ~20-50 CLEAN on-staff heads per document (ANY isolation level --
unlike the exemplar-averaging path, a single head's own ink shape does
not need an isolated window to measure its own orientation), filled and
hollow separately:

  * OUTER tilt: `cv2.fitEllipse` on the largest ink contour inside the
    head's own local window -- the angle of its major axis, converted to
    "degrees up-and-to-the-right from horizontal" (a real notehead's long
    axis tilts so the RIGHT end sits higher on the page, lower y).
  * HOLLOW SLIT tilt (hollow heads only): same fit, on the largest WHITE
    (background) contour fully enclosed by the ink ring -- the open
    centre of a half/whole note.

Reports median + IQR per (doc, kind, feature). MEASUREMENT ONLY -- reads
the committed records, writes nothing back.

    python3 benchmarks/omr-local-staff-2026-09/measure_head_tilt.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402
from tools.omr.annotate.ledger_shape_trace import _mask_stem_columns  # noqa: E402

MAX_HEADS_PER_KIND = 50

# A real notehead oval (filled ~1.3x1.0 sp, hollow similar) has
# eccentricity around 1.2-1.4. A blob fused with its own stem (not fully
# masked by the heuristic fallback) reads far more elongated than that
# -- excluded from the TILT statistic (counted, not silently dropped):
# its "angle" is the STEM's own near-vertical orientation, not the
# oval's (measured directly on the first pass of this script: unmasked
# blobs of eccentricity 4-17 produced near-random angles that washed the
# whole median toward 0).
MAX_EXPECTED_ECCENTRICITY = 2.0


def _angle_up_right(ellipse_angle_deg: float) -> float:
    """`cv2.fitEllipse`'s own angle is the rotation of the major axis
    from the vertical (0..180, clockwise, image y-down). Converted here
    to "degrees the long axis tilts up-to-the-right from horizontal",
    signed, in (-90, 90] -- 0 = perfectly horizontal, positive = the
    RIGHT end is higher on the page (lower y), matching how a tilted
    notehead is normally described."""
    a = ellipse_angle_deg % 180.0
    # cv2's angle is from the vertical; convert to from-horizontal.
    from_horizontal = 90.0 - a
    # Image y grows DOWNWARD, so a positive from_horizontal (axis leaning
    # toward the top-right quadrant in cv2's own convention) already
    # means "right end higher" -- no extra sign flip needed, verified
    # against a hand-built synthetic ellipse at the bottom of this file's
    # own `__main__` self-check.
    if from_horizontal > 90.0:
        from_horizontal -= 180.0
    if from_horizontal <= -90.0:
        from_horizontal += 180.0
    return from_horizontal


def _largest_contour(mask: np.ndarray) -> Optional[np.ndarray]:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def _fit_angle(mask: np.ndarray, max_ecc: Optional[float] = None) -> Optional[float]:
    c = _largest_contour(mask)
    if c is None or len(c) < 5:
        return None
    (_cx, _cy), (ew, eh), angle = cv2.fitEllipse(c)
    if max_ecc is not None:
        ecc = max(ew, eh) / max(1.0, min(ew, eh))
        if ecc > max_ecc:
            return None
    return _angle_up_right(angle)


def measure_head(gray: np.ndarray, box, spacing: float) -> dict:
    """`{"outer": angle|None, "slit": angle|None, "kind": "filled"|"hollow"}`
    for ONE head, read from its own local window (reuses the same window
    sizing `head_template` already uses, so the measurement is on
    EXACTLY the ink the matcher will later see)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    from tools.omr.staged.geometry import (
        STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES,
    )
    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    half_w = ht.WINDOW_HALF_WIDTH_HEAD_WIDTHS * head_w * 0.6  # tight -- just the head
    half_h = head_h * 0.75
    h, w = gray.shape
    ix0, ix1 = max(0, int(cx - half_w)), min(w, int(cx + half_w))
    iy0, iy1 = max(0, int(cy - half_h)), min(h, int(cy + half_h))
    if ix1 <= ix0 or iy1 <= iy0:
        return dict(outer=None, slit=None, kind="filled")
    window = gray[iy0:iy1, ix0:ix1]
    thr = lg._otsu_threshold(window)
    ink = _mask_stem_columns(window <= thr, spacing)
    unfiltered_angle = _fit_angle(ink)
    outer_angle = _fit_angle(ink, max_ecc=MAX_EXPECTED_ECCENTRICITY)
    excluded_as_elongated = outer_angle is None and unfiltered_angle is not None

    inner_mask = (~ink)
    # Keep only white runs NOT touching the window border (an enclosed
    # slit, never the page background bleeding in from outside the head).
    bh, bw = inner_mask.shape
    border = np.zeros_like(inner_mask)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    num, labels = cv2.connectedComponents(inner_mask.astype(np.uint8))
    touches_border = set(np.unique(labels[border]))
    enclosed = np.zeros_like(inner_mask)
    for lbl in range(1, num):
        if lbl in touches_border:
            continue
        enclosed |= (labels == lbl)
    ink_frac = float(ink.mean())
    kind = "hollow" if (enclosed.any() and ink_frac < 0.75) else "filled"
    slit_angle = _fit_angle(enclosed) if kind == "hollow" else None
    return dict(outer=outer_angle, slit=slit_angle, kind=kind,
               excluded_as_elongated=excluded_as_elongated)


def collect_doc_measurements(doc_id: str) -> List[dict]:
    loaded = ts.load_doc(doc_id)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    far_rows = score._far_head_rows(doc_id, loaded)
    far_pages = sorted({r["page"] for r in far_rows}) or [0]

    out = []
    for page in far_pages:
        gray = pages.get(page)
        boxes = sht._page_glyph_boxes(rec).get(page, [])
        by_subject = {s: (cls, box) for (s, cls, box) in boxes}
        for o in rec.observations:
            if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
                continue
            sub = o["subject"]
            if int(sub.split("/")[1]) != page:
                continue
            pos = float(o["value"])
            if lg.far_head_needs_ledger_read(int(round(pos))):
                continue
            entry = by_subject.get(sub)
            if entry is None:
                continue
            _cls, box = entry
            parts = sub.split("/")
            staff_key = f"staff/{parts[1]}/{parts[2]}/{parts[3]}"
            line_rows = rec.obs(Q.STAFF_LINES, staff_key)
            if not line_rows:
                continue
            global_lines = [float(y) for y in line_rows[-1]["value"]]
            lines = score.frame_lines_for_head(gray, global_lines, box)
            spacing = (max(lines) - min(lines)) / 4.0
            if spacing <= 0:
                continue
            m = measure_head(gray, box, spacing)
            m["subject"] = sub
            out.append(m)
    return out


def main() -> int:
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        measurements = collect_doc_measurements(doc_id)
        for kind in ("filled", "hollow"):
            of_kind = [m for m in measurements if m["kind"] == kind][:MAX_HEADS_PER_KIND]
            outer = np.array([m["outer"] for m in of_kind if m["outer"] is not None])
            slit = np.array([m["slit"] for m in of_kind if m.get("slit") is not None])
            n_excluded = sum(1 for m in of_kind if m.get("excluded_as_elongated"))
            print(f"  {kind}: n={len(of_kind)}  "
                  f"(excluded as stem-elongated, ecc>{MAX_EXPECTED_ECCENTRICITY}: {n_excluded})")
            if outer.size:
                q1, med, q3 = np.percentile(outer, [25, 50, 75])
                print(f"    outer tilt   median={med:.1f} deg  IQR=[{q1:.1f}, {q3:.1f}]  n={outer.size}")
            else:
                print("    outer tilt   no measurable heads")
            if slit.size:
                q1, med, q3 = np.percentile(slit, [25, 50, 75])
                print(f"    slit  tilt   median={med:.1f} deg  IQR=[{q1:.1f}, {q3:.1f}]  n={slit.size}")
            elif kind == "hollow":
                print("    slit  tilt   no measurable slits")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
