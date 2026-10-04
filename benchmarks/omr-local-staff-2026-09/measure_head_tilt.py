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
from typing import List, Optional, Tuple

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


def _fit_axes(mask: np.ndarray, max_ecc: Optional[float] = None
             ) -> Optional[Tuple[float, float]]:
    """`(long, short)` axes of the fitted ellipse (major axis first, the
    one `_angle_up_right` is the tilt of) -- used to size a drawn template's inner slit from the
    SAME fit the angle came from, never a separately-guessed fraction."""
    c = _largest_contour(mask)
    if c is None or len(c) < 5:
        return None
    (_cx, _cy), (ew, eh), _angle = cv2.fitEllipse(c)
    if max_ecc is not None:
        ecc = max(ew, eh) / max(1.0, min(ew, eh))
        if ecc > max_ecc:
            return None
    # cv2 returns the UNROTATED box (width, height), which for a fitted
    # wide head is (minor, major) -- swapped. The tilt is the MAJOR axis's
    # angle, so report (long, short). 2026-10-04: the raw order was drawn
    # as (width, height) -> upright ovals.
    return (float(max(ew, eh)), float(min(ew, eh)))


#: Page-level thickness cache (`sht.measure_line_thickness_px`, already
#: validated against this same raster in the geometry-template lane --
#: Litolff ~3-4px, Brahms ~5-7px). A per-HEAD re-measurement inside the
#: tight tilt window was tried first and is NOT used: on a window this
#: small, an edge column can itself sit inside the oval's own ink or
#: catch unrelated dark noise, occasionally returning a run as tall as
#: the whole window -- which then masked EVERY pixel out (measured
#: directly: several heads came back with `ink.sum() == 0` after that
#: first version's masking). The page-level measurement is the SAME
#: number every head on that page already gets via the per-page
#: geometry-template path, reused here rather than re-derived.
_PAGE_THICKNESS_CACHE: dict = {}


def _page_line_thickness_px(doc_id: str, page: int, gray: np.ndarray,
                            rec, boxes) -> float:
    key = (doc_id, page)
    if key in _PAGE_THICKNESS_CACHE:
        return _PAGE_THICKNESS_CACHE[key]
    nb_boxes = [b for (_s, cls, b) in boxes if "notehead" in cls.lower()]
    sample_ranges = [(b[0] - 40, b[0] - 10) for b in nb_boxes[:30]]
    staff_keys = {f"staff/{p}/{s}/{st}"
                 for (sub, _c, _b) in boxes
                 for p, s, st in [sub.split("/")[1:4]]}
    page_lines = []
    for sk in sorted(staff_keys)[:1]:
        lr = rec.obs(Q.STAFF_LINES, sk)
        if lr:
            page_lines = [float(y) for y in lr[-1]["value"]]
            break
    thickness = sht.measure_line_thickness_px(gray, page_lines, sample_ranges) \
        if page_lines and sample_ranges else None
    thickness = thickness or 4.0
    _PAGE_THICKNESS_CACHE[key] = thickness
    return thickness


def _mask_staff_line_rows(ink: np.ndarray, line_rows_local: List[float],
                          thickness_px: float, protect_cols: "Tuple[int, int] | None" = None
                          ) -> np.ndarray:
    """Manager review 2026-10-02: `fitEllipse` on head ink with the
    STAFF LINES left in is pulled flat by the horizontal line through or
    beside the head -- zero those rows out before any contour fit.

    ⚠️ 2026-10-02, second pass (measured directly, this file's own
    FINDINGS): on a space THIS tight, BOTH neighbouring staff lines sit
    inside even the tight tilt window (measured: lines_local at window-
    relative rows ~5 and ~20 of a 26-27-row window) -- their rows
    OVERLAP the oval's own top/bottom extent, so blanking the full row
    width chops both tips off the oval, leaving a thin, wildly-eccentric
    residual (several heads measured `ecc` 3-13 after that first-pass
    mask, versus a real oval's ~1.1-1.6). Fixed the same way a ledger's
    own stub is isolated elsewhere in this codebase: `protect_cols`
    (the oval's own expected column range, `GEOM_HEAD_WIDTH_SPACES`'s
    half-width around the window centre) is NEVER blanked, however close
    a line sits -- only the columns OUTSIDE it (where the line is
    unambiguously just the line, never the oval's own ink) are masked."""
    out = ink.copy()
    half = max(1, int(round(thickness_px / 2.0)) + 1)
    h, w = out.shape
    pc0, pc1 = protect_cols if protect_cols is not None else (0, w)
    pc0, pc1 = max(0, pc0), min(w, pc1)
    for ly in line_rows_local:
        ly_i = int(round(ly))
        r0, r1 = max(0, ly_i - half), min(h, ly_i + half + 1)
        if pc0 > 0:
            out[r0:r1, :pc0] = False
        if pc1 < w:
            out[r0:r1, pc1:] = False
    return out


def measure_head(gray: np.ndarray, box, spacing: float,
                 global_lines: List[float], thickness_px: float) -> dict:
    """`{"outer": angle|None, "slit": angle|None, "kind": "filled"|"hollow"}`
    for ONE head, read from its own local window (reuses the same window
    sizing `head_template` already uses, so the measurement is on
    EXACTLY the ink the matcher will later see). Staff lines AND the
    stem column are masked out before any ellipse fit -- see
    `_mask_staff_line_rows` above (manager review 2026-10-02)."""
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
    lines_local = [ly - iy0 for ly in global_lines if iy0 - 2 <= ly <= iy1 + 2]
    center_col = cx - ix0
    protect_half = ht.GEOM_HEAD_WIDTH_SPACES / 2.0 * spacing
    protect_cols = (int(round(center_col - protect_half)),
                   int(round(center_col + protect_half)))

    thr = lg._otsu_threshold(window)
    ink_raw = window <= thr
    ink_no_lines = _mask_staff_line_rows(ink_raw, lines_local, thickness_px,
                                        protect_cols=protect_cols)
    ink = _mask_stem_columns(ink_no_lines, spacing)
    unfiltered_angle = _fit_angle(ink)
    outer_angle = _fit_angle(ink, max_ecc=MAX_EXPECTED_ECCENTRICITY)
    excluded_as_elongated = outer_angle is None and unfiltered_angle is not None
    outer_axes = _fit_axes(ink, max_ecc=MAX_EXPECTED_ECCENTRICITY)

    # The slit search uses the ORIGINAL (line-masked only, stem NOT
    # re-masked into "ink") background -- a slit is bounded by the ring
    # of ink the stem may touch, so stem masking must not punch a hole
    # into the ring that would falsely enclose the window's own outside.
    inner_mask = (~ink_no_lines)
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
    ink_frac = float(ink_no_lines.mean())
    kind = "hollow" if (enclosed.any() and ink_frac < 0.75) else "filled"
    slit_angle = _fit_angle(enclosed) if kind == "hollow" else None
    slit_axes = _fit_axes(enclosed) if kind == "hollow" else None
    return dict(outer=outer_angle, slit=slit_angle, kind=kind,
               excluded_as_elongated=excluded_as_elongated,
               outer_axes=outer_axes, slit_axes=slit_axes,
               window_ink=ink, window_enclosed=enclosed)


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
        thickness_px = _page_line_thickness_px(doc_id, page, gray, rec, boxes)
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
            m = measure_head(gray, box, spacing, lines, thickness_px)
            m["subject"] = sub
            m["in_space"] = (int(round(pos)) % 2) != 0
            out.append(m)
    return out


def summarize(doc_id: str, measurements: List[dict]) -> dict:
    """Per-doc summary: OUTER tilt restricted to IN-SPACE heads only
    (Sean, 2026-10-02: "use heads in spaces... to avoid the bias
    entirely" -- no staff line can be near the head's own middle there,
    belt-and-suspenders on top of the line-masking above). SLIT tilt
    uses every hollow head (lines are masked regardless of parity)."""
    out: dict = {}
    for kind in ("filled", "hollow"):
        of_kind = [m for m in measurements if m["kind"] == kind]
        in_space = [m for m in of_kind if m.get("in_space")]
        outer = np.array([m["outer"] for m in in_space if m["outer"] is not None])
        slit = np.array([m["slit"] for m in of_kind if m.get("slit") is not None])
        n_excluded = sum(1 for m in in_space if m.get("excluded_as_elongated"))
        print(f"  {kind}: n_total={len(of_kind)} n_in_space={len(in_space)}  "
              f"(excluded as stem-elongated, ecc>{MAX_EXPECTED_ECCENTRICITY}: {n_excluded})")
        entry = {}
        if outer.size:
            q1, med, q3 = np.percentile(outer, [25, 50, 75])
            print(f"    outer tilt (in-space only)  median={med:.1f} deg  "
                  f"IQR=[{q1:.1f}, {q3:.1f}]  n={outer.size}")
            entry["outer_tilt_deg"] = float(med)
            entry["outer_n"] = int(outer.size)
            axes = [m["outer_axes"] for m in in_space
                   if m.get("outer_axes") is not None and m["outer"] is not None]
            if axes:
                aw = np.median([a[0] for a in axes])
                ah = np.median([a[1] for a in axes])
                print(f"    outer axes (median, px, this doc's own spacing)  "
                      f"{aw:.1f} x {ah:.1f}")
                entry["outer_axes_px"] = (float(aw), float(ah))
        else:
            print("    outer tilt   no measurable heads")
        if slit.size:
            q1, med, q3 = np.percentile(slit, [25, 50, 75])
            print(f"    slit  tilt   median={med:.1f} deg  IQR=[{q1:.1f}, {q3:.1f}]  n={slit.size}")
            entry["slit_tilt_deg"] = float(med)
            entry["slit_n"] = int(slit.size)
            slit_axes = [m["slit_axes"] for m in of_kind
                        if m.get("slit_axes") is not None and m["slit"] is not None
                        and all(np.isfinite(a) and a > 0 for a in m["slit_axes"])]
            if slit_axes:
                sw = np.median([a[0] for a in slit_axes])
                sh = np.median([a[1] for a in slit_axes])
                print(f"    slit  axes (median, px)  {sw:.1f} x {sh:.1f}")
                entry["slit_axes_px"] = (float(sw), float(sh))
                outer_axes_for_ratio = entry.get("outer_axes_px")
                if outer_axes_for_ratio:
                    # The slit's size relative to the OUTER oval's own
                    # size, at the SAME (this doc's own) spacing -- the
                    # ratio a geometry template draws, never an absolute
                    # pixel count that would not transfer to a different
                    # spacing.
                    entry["slit_to_outer_ratio"] = (
                        sw / outer_axes_for_ratio[0], sh / outer_axes_for_ratio[1],
                    )
        elif kind == "hollow":
            print("    slit  tilt   no measurable slits")
        out[kind] = entry
    return out


def main() -> int:
    all_summaries = {}
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        measurements = collect_doc_measurements(doc_id)
        all_summaries[doc_id] = summarize(doc_id, measurements)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
