#!/usr/bin/env python3
"""Stem/beam/rhythm precision benchmark.

Goal: measure ground-truth accuracy of the classical-CV line detector
(`tools/omr/line_detection.py`) and the rhythm parser
(`tools/omr/rhythm.py`) on a representative cell set.

Three outputs per cell:

  1. **Overlay PNG** — the cell at canonical resolution with
     CV-detected stems (green) and beams (blue) drawn on top. Used
     for visual human verdict.

  2. **Auto stats** — number of CV stems / beams detected per cell,
     and (for catalog-with-XML cells) the XML-canonical stem/beam
     count for cross-check.

  3. **Verdict template JSON** — one entry per cell with empty
     placeholders the human fills in:
       stems_correct, stems_missed, stems_false_positive,
       beams_correct, beams_missed, beams_false_positive
     After the human fills it in, run `score_verdicts.py` to compute
     precision/recall/F1.

For rhythm precision (automatic — no human required), we extract the
canonical XML per-note durations for catalog cells and compare to the
pipeline's emitted durations. Output: per-note match rate.

Usage:
    python3 benchmarks/omr-stem-precision/run_precision_benchmark.py \\
        --out benchmarks/omr-stem-precision/run-001

Picks a curated 10-cell sample by default (see CELL_SAMPLES below).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-imslp-pipeline"))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.line_detection import detect_stems, detect_beams  # noqa: E402
from tools.omr.yolo_detector import YoloDetector  # noqa: E402


# Prod YOLO weights for front-matter masking (Idea 1: mask clefs / keysigs /
# timesigs / accidentals before classical CV runs, so stem & beam detection
# can't pick up clef strokes or accidental bars as false-positive stems).
PROD_WEIGHTS = Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
                    "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")

# YOLO class names whose bboxes should be masked out before CV detection.
# These are the symbols that LIVE at the front of the measure (clefs, key
# sigs, time sigs) plus any inline accidentals — none of these are stems,
# beams, or noteheads, so masking them does not hide musical content.
FRONT_MATTER_CLASSES = {
    # Clefs
    "clefG", "clefF", "clefCAlto", "clefCTenor",
    "clefUnpitchedPercussion", "clef8", "clef15",
    # Time signatures (full + per-digit)
    "timeSig0", "timeSig1", "timeSig2", "timeSig3", "timeSig4",
    "timeSig5", "timeSig6", "timeSig7", "timeSig8", "timeSig9",
    "timeSigCommon", "timeSigCutCommon",
    # Key signatures + inline accidentals
    "keySharp", "keyFlat", "keyNatural",
    "accidentalSharp", "accidentalFlat", "accidentalNatural",
    "accidentalDoubleSharp", "accidentalDoubleFlat",
    # Numerals on tuplets & time-sig area
    "numeral1", "numeral2", "numeral3", "numeral4", "numeral5",
    "numeral6", "numeral7", "numeral8", "numeral9",
}


# Notehead class names that DO have a stem (filled or open noteheads,
# half/quarter/eighth/sixteenth/etc.). Whole and double-whole noteheads
# do NOT have a stem in standard engraving.
STEMMED_NOTEHEAD_CLASSES = {
    "noteheadBlackOnLine", "noteheadBlackOnLineSmall",
    "noteheadBlackInSpace", "noteheadBlackInSpaceSmall",
    "noteheadHalfOnLine", "noteheadHalfOnLineSmall",
    "noteheadHalfInSpace", "noteheadHalfInSpaceSmall",
}
UNSTEMMED_NOTEHEAD_CLASSES = {
    "noteheadWholeOnLine", "noteheadWholeOnLineSmall",
    "noteheadWholeInSpace", "noteheadWholeInSpaceSmall",
    "noteheadDoubleWholeOnLine", "noteheadDoubleWholeOnLineSmall",
    "noteheadDoubleWholeInSpace", "noteheadDoubleWholeInSpaceSmall",
}
ALL_NOTEHEAD_CLASSES = STEMMED_NOTEHEAD_CLASSES | UNSTEMMED_NOTEHEAD_CLASSES


def mask_front_matter(cell, yolo_dets) -> int:
    """Mutate cell.image (and cell.image_no_staff if present) to set the
    pixels inside each YOLO front-matter bbox to paper-white. Returns the
    number of bboxes masked."""
    if not yolo_dets:
        return 0
    n_masked = 0
    for det in yolo_dets:
        if det.smufl_name not in FRONT_MATTER_CLASSES:
            continue
        x0 = max(0, det.x_canonical)
        y0 = max(0, det.y_canonical)
        x1 = min(cell.image.shape[1], det.x_canonical + det.width_canonical)
        y1 = min(cell.image.shape[0], det.y_canonical + det.height_canonical)
        if x1 <= x0 or y1 <= y0:
            continue
        # Paper is 255 (white). cell.image is BGR or grayscale uint8.
        if cell.image.ndim == 3:
            cell.image[y0:y1, x0:x1, :] = 255
        else:
            cell.image[y0:y1, x0:x1] = 255
        if cell.image_no_staff is not None:
            if cell.image_no_staff.ndim == 3:
                cell.image_no_staff[y0:y1, x0:x1, :] = 255
            else:
                cell.image_no_staff[y0:y1, x0:x1] = 255
        n_masked += 1
    return n_masked


# Module-level YOLO detector, lazy-init on first use (loading the weights
# takes a few seconds).
_yolo_detector: Optional[YoloDetector] = None


def _get_yolo() -> YoloDetector:
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YoloDetector(weights_path=PROD_WEIGHTS, device="auto")
    return _yolo_detector


# ─────────────────────────────────────────────────────────────────────────────
# Structurally-constrained stem detection
# ─────────────────────────────────────────────────────────────────────────────


def _staff_line_spacing(cell) -> float:
    ys = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(ys) >= 2:
        sorted_ys = sorted(ys)
        gaps = [sorted_ys[i+1] - sorted_ys[i] for i in range(len(sorted_ys)-1)]
        return sum(gaps) / len(gaps)
    return 24.0


def _stem_touches_notehead(stem, noteheads, line_spacing) -> Optional[object]:
    """Return the notehead this stem connects to (top OR bottom of stem must
    be within ±0.6 line_spacing of a notehead, AND stem's x-center must be
    within ±0.4 line_spacing of the notehead's left or right edge — stems
    grow from the notehead edge, not the center).
    """
    y_tol = max(3, int(round(line_spacing * 0.6)))
    x_tol = max(2, int(round(line_spacing * 0.4)))
    stem_x_mid = stem.x_canonical + stem.width_canonical // 2
    stem_y_top = stem.y_canonical
    stem_y_bot = stem.y_canonical + stem.height_canonical
    for nh in noteheads:
        if nh.smufl_name not in ALL_NOTEHEAD_CLASSES:
            continue
        nh_x_left = nh.x_canonical
        nh_x_right = nh.x_canonical + nh.width_canonical
        nh_y_top = nh.y_canonical
        nh_y_bot = nh.y_canonical + nh.height_canonical
        # x must align with one of the notehead's edges (where stems grow)
        if not (abs(stem_x_mid - nh_x_left) <= x_tol or abs(stem_x_mid - nh_x_right) <= x_tol):
            continue
        # y: top or bottom of stem must align with the notehead's y-range
        # (allowing some slack because stems thread through the notehead)
        if (nh_y_top - y_tol <= stem_y_top <= nh_y_bot + y_tol or
                nh_y_top - y_tol <= stem_y_bot <= nh_y_bot + y_tol):
            return nh
    return None


def filter_stems_by_noteheads(cv_stems, noteheads, line_spacing) -> tuple[list, set, dict]:
    """Apply notehead-anchored elimination rules to CV stem detections.

    Returns (kept_stems, anchored_notehead_ids, stats_dict) where:
      - kept_stems: stems that connect to a real notehead
      - anchored_notehead_ids: id() of each notehead that has at least
        one anchored stem (so predictive logic can skip those columns)
      - stats_dict: counters for kept / dropped / dropped-whole
    """
    kept = []
    anchored_ids: set = set()
    stats = {"kept_anchored": 0, "dropped_orphan": 0, "dropped_whole_only": 0}
    for s in cv_stems:
        nh = _stem_touches_notehead(s, noteheads, line_spacing)
        if nh is None:
            stats["dropped_orphan"] += 1
            continue
        if nh.smufl_name in UNSTEMMED_NOTEHEAD_CLASSES:
            stats["dropped_whole_only"] += 1
            continue
        kept.append(s)
        anchored_ids.add(id(nh))
        stats["kept_anchored"] += 1
    return kept, anchored_ids, stats


def _group_noteheads_into_columns(noteheads, line_spacing) -> list[list]:
    """Group noteheads whose x-centers cluster within ±0.4 line_spacing
    into chord columns. Each column shares ONE stem (or none, if all whole)."""
    x_tol = max(2, int(round(line_spacing * 0.4)))
    sorted_nh = sorted(
        [n for n in noteheads if n.smufl_name in ALL_NOTEHEAD_CLASSES],
        key=lambda n: n.x_canonical + n.width_canonical / 2,
    )
    columns = []
    for nh in sorted_nh:
        nh_x_mid = nh.x_canonical + nh.width_canonical / 2
        if columns and abs(
            (columns[-1][0].x_canonical + columns[-1][0].width_canonical / 2) - nh_x_mid
        ) <= x_tol:
            columns[-1].append(nh)
        else:
            columns.append([nh])
    return columns


def predict_missing_stems(noteheads, anchored_ids, cell, line_spacing) -> list:
    """For each stemmed-notehead COLUMN (chord) with NO CV-detected stem
    anchored to ANY of its noteheads, scan a narrow vertical strip for ≥30 %
    ink. If found, synthesize ONE predicted stem for the whole column.
    """
    if not noteheads:
        return []

    # Group noteheads into chord columns — one stem per column at most.
    columns = _group_noteheads_into_columns(noteheads, line_spacing)

    binary = cell.image if cell.image.ndim == 2 else cv2.cvtColor(cell.image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(binary, 180, 255, cv2.THRESH_BINARY_INV)
    h, w = binary.shape[:2]

    strip_h = int(round(line_spacing * 3.0))   # ~3 line_spacings tall scan
    strip_w = max(3, int(round(line_spacing * 0.3)))

    predicted = []
    from tools.omr.line_detection import LineDetection

    for column in columns:
        # Skip columns that are entirely whole/double-whole noteheads — no stem expected
        stemmed = [nh for nh in column if nh.smufl_name in STEMMED_NOTEHEAD_CLASSES]
        if not stemmed:
            continue
        # Skip columns where ANY notehead already has a CV-anchored stem
        if any(id(nh) in anchored_ids for nh in stemmed):
            continue
        # Use the highest + lowest notehead to define the column's notehead span
        nh_x_left = min(nh.x_canonical for nh in stemmed)
        nh_x_right = max(nh.x_canonical + nh.width_canonical for nh in stemmed)
        col_top = min(nh.y_canonical for nh in stemmed)
        col_bot = max(nh.y_canonical + nh.height_canonical for nh in stemmed)

        # Two candidate directions: stem-up (right edge, scanning up from col_top)
        # vs stem-down (left edge, scanning down from col_bot). Pick the one
        # with higher ink fill.
        candidates = [
            ("up",   nh_x_right - strip_w // 2, max(0, col_top - strip_h), col_top),
            ("down", nh_x_left,                col_bot, min(h, col_bot + strip_h)),
        ]
        best = None
        for direction, cx, y0, y1 in candidates:
            x0 = max(0, cx - strip_w // 2)
            x1 = min(w, x0 + strip_w)
            if y1 <= y0 or x1 <= x0:
                continue
            roi = binary[y0:y1, x0:x1]
            if roi.size == 0:
                continue
            ink_fill = float((roi > 0).sum()) / roi.size
            if ink_fill >= 0.30 and (best is None or ink_fill > best[0]):
                best = (ink_fill, x0, y0, x1, y1)
        if best is not None:
            _, x0, y0, x1, y1 = best
            predicted.append(LineDetection(
                smufl_name="stem",
                category="stem",
                x_canonical=x0,
                y_canonical=y0,
                width_canonical=x1 - x0,
                height_canonical=y1 - y0,
                confidence=0.5,   # lower than CV-detected; marks as predicted
            ))
    return predicted


# ─────────────────────────────────────────────────────────────────────────────
# Curated cell sample — diverse but small enough to verdict in ~20 min
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CellSample:
    """One cell to benchmark. PDF + 0-indexed page + cell coords."""
    cell_id: str          # human-readable, used in filenames
    pdf_path: Path
    page_1indexed: int
    system_index: int
    staff_index: int      # within the page
    measure_index: int    # within the staff
    source_tag: str       # "wtc-p5" / "beet5-p10" / "catalog-b1m1" — for grouping
    # Optional: if this cell has a paired XML, fill these in for Tier 1 (XML cross-check)
    mxl_path: Optional[Path] = None
    # XML measure number string (after walking the pipeline's measure counter)
    xml_measure_n: Optional[str] = None
    # XML staff index within the measure (0-based)
    xml_staff: Optional[int] = None


# Bach WTC reuses cells from the existing verdict set. PDF path from cells.json.
WTC_PDF = Path(
    "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
    "PDF Scores/IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"
)

# Beethoven 5 — used as the standard spot-check page elsewhere in the repo.
BEET5_PDF = ROOT / "tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/imslp-52624/score.pdf"

# Catalog cells with paired MusicXML (for automatic rhythm precision check).
# Use beethoven-symphony-1 mvt 1 since it had 100% XML match in Phase K/L batches.
B1_PDF = ROOT / "tools/omr/training/data/imslp/beethoven-symphony-1/pdfs/imslp-52848/score.pdf"
B1_MXL = ROOT / "tools/omr/training/data/imslp/beethoven-symphony-1/musicxml/mvt-1.mxl"


CELL_SAMPLES: list[CellSample] = [
    # Bach WTC — sparse keyboard, easy ground truth. Page 5 (0-indexed=4).
    # NOTE: staff_index is GLOBAL within the page, not per-system.
    # WTC p5 layout: 5 systems × 2 staves each (treble+bass).
    CellSample("wtc-p5-sys0-s0-m0",  WTC_PDF, 5, 0, 0, 0, "wtc"),      # sys0 treble m0
    CellSample("wtc-p5-sys0-s1-m1",  WTC_PDF, 5, 0, 1, 1, "wtc"),      # sys0 bass m1
    CellSample("wtc-p5-sys1-s2-m0",  WTC_PDF, 5, 1, 2, 0, "wtc"),      # sys1 treble m0

    # Beethoven 5 page 10 — dense orchestral, hard ground truth.
    # B5 p10 layout: 2 systems × 12 staves each. sys0 = top half, sys1 = bottom.
    CellSample("beet5-p10-sys0-s8-m0",   BEET5_PDF, 10, 0,  8, 0, "beet5"),  # mid-staff string m0
    CellSample("beet5-p10-sys1-s12-m1",  BEET5_PDF, 10, 1, 12, 1, "beet5"),  # sys1 top staff m1
    CellSample("beet5-p10-sys0-s0-m2",   BEET5_PDF, 10, 0,  0, 2, "beet5"),  # flutes m2
    CellSample("beet5-p10-sys0-s4-m3",   BEET5_PDF, 10, 0,  4, 3, "beet5"),  # horns m3

    # Beethoven 1 mvt 1 page 8 — for automated rhythm precision check.
    # B1 p8 layout: 3 systems with sizes 3 / 8 / 11 staves.
    CellSample("b1m1-p8-sys0-s0-m0",   B1_PDF, 8, 0,  0, 0, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=0),
    CellSample("b1m1-p8-sys2-s14-m2",  B1_PDF, 8, 2, 14, 2, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=3),     # sys2 mid staff
    CellSample("b1m1-p8-sys2-s17-m4",  B1_PDF, 8, 2, 17, 4, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=6),     # sys2 mid staff m4
]


# ─────────────────────────────────────────────────────────────────────────────
# Per-cell processing
# ─────────────────────────────────────────────────────────────────────────────


def process_cell(
    sample: CellSample,
    out_dir: Path,
) -> Optional[dict]:
    """Extract the cell from PDF, run CV detection, render overlay,
    return automated stats."""
    pdf_path = sample.pdf_path
    if not pdf_path.exists():
        print(f"  ✗ PDF not found: {pdf_path}")
        return None

    try:
        pi = render_page(pdf_path, sample.page_1indexed - 1, dpi=300)
        pws = detect_staves(pi)
        cells = extract_measures(pws)
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ extract failed: {exc}")
        return None

    # Find the requested cell
    matches = [
        c for c in cells
        if c.system_index == sample.system_index
        and c.staff_index == sample.staff_index
        and c.measure_index == sample.measure_index
    ]
    if not matches:
        avail = sorted({(c.system_index, c.staff_index, c.measure_index) for c in cells})
        print(f"  ✗ cell not found. Want ({sample.system_index},{sample.staff_index},"
              f"{sample.measure_index}); found {len(cells)} cells")
        print(f"     first 5 available: {avail[:5]}")
        return None

    cell = matches[0]

    # Idea 1: run YOLO first to find clefs / keysigs / timesigs / accidentals,
    # then mask their bboxes to paper-white before classical CV. Eliminates
    # false-positive stems on clef strokes, accidental bars, and time-sig digits.
    yolo = _get_yolo()
    yolo_dets = yolo.detect(cell, conf_threshold=0.25, imgsz=1280)
    n_masked = mask_front_matter(cell, yolo_dets)

    # Raw CV detections.
    raw_stems = detect_stems(cell)
    raw_beams = detect_beams(cell)

    # Idea 4: notehead-anchored stem elimination — drop any CV stem that
    # isn't connected to a real (non-whole) notehead.
    line_spacing = _staff_line_spacing(cell)
    noteheads = [d for d in yolo_dets if d.smufl_name in ALL_NOTEHEAD_CLASSES]
    kept_stems, anchored_nh_ids, stem_filter_stats = filter_stems_by_noteheads(
        raw_stems, noteheads, line_spacing
    )

    # Idea 6: predictive gap-fill — for each stemmed-notehead chord column
    # without any anchored stem, scan a vertical strip for ink and predict.
    predicted_stems = predict_missing_stems(noteheads, anchored_nh_ids, cell, line_spacing)
    cv_stems = kept_stems + predicted_stems

    # Beams: detect_beams already does stem-support filtering internally,
    # but it uses the RAW stem set. Re-filter beams against our cleaner
    # notehead-anchored stems for a final structural check.
    from tools.omr.line_detection import _prune_beams_by_stem_support
    cv_beams = _prune_beams_by_stem_support(raw_beams, cv_stems, line_spacing)

    # Auto ink-fill check (Tier 2): % of black pixels in each bbox.
    binary = cell.image if cell.image.ndim == 2 else cv2.cvtColor(cell.image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(binary, 180, 255, cv2.THRESH_BINARY_INV)
    h, w = binary.shape[:2]

    def ink_fill(det) -> float:
        x0 = max(0, det.x_canonical)
        y0 = max(0, det.y_canonical)
        x1 = min(w, det.x_canonical + det.width_canonical)
        y1 = min(h, det.y_canonical + det.height_canonical)
        if x1 <= x0 or y1 <= y0:
            return 0.0
        roi = binary[y0:y1, x0:x1]
        if roi.size == 0:
            return 0.0
        return float((roi > 0).sum()) / roi.size

    stems_info = []
    for i, det in enumerate(cv_stems):
        stems_info.append({
            "idx": i,
            "x_canonical": det.x_canonical,
            "y_canonical": det.y_canonical,
            "width_canonical": det.width_canonical,
            "height_canonical": det.height_canonical,
            "ink_fill_ratio": round(ink_fill(det), 3),
        })
    beams_info = []
    for i, det in enumerate(cv_beams):
        beams_info.append({
            "idx": i,
            "x_canonical": det.x_canonical,
            "y_canonical": det.y_canonical,
            "width_canonical": det.width_canonical,
            "height_canonical": det.height_canonical,
            "ink_fill_ratio": round(ink_fill(det), 3),
        })

    # Render overlay PNG with numbered detections for verdict. Make the
    # labels large + boxed so they're readable when verdicting in a browser.
    overlay = cv2.cvtColor(cell.image, cv2.COLOR_GRAY2BGR) if cell.image.ndim == 2 else cell.image.copy()

    def draw_labeled_box(img, x0, y0, x1, y1, color, label, *, thickness=3, font_scale=1.2):
        cv2.rectangle(img, (x0, y0), (x1, y1), color, thickness)
        # Draw a filled background rectangle for the label, then the label text in white
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        pad = 4
        # Place label above the box; if it'd clip the top, place it below
        ly1 = y0 - pad
        ly0 = ly1 - th - 2 * pad
        if ly0 < 0:
            ly0 = y1 + pad
            ly1 = ly0 + th + 2 * pad
        lx0 = x0
        lx1 = lx0 + tw + 2 * pad
        cv2.rectangle(img, (lx0, ly0), (lx1, ly1), color, -1)
        cv2.putText(img, label, (lx0 + pad, ly1 - pad - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)

    for i, det in enumerate(cv_stems):
        x0 = det.x_canonical; y0 = det.y_canonical
        x1 = x0 + det.width_canonical; y1 = y0 + det.height_canonical
        draw_labeled_box(overlay, x0, y0, x1, y1, (0, 200, 0), f"s{i}")
    for i, det in enumerate(cv_beams):
        x0 = det.x_canonical; y0 = det.y_canonical
        x1 = x0 + det.width_canonical; y1 = y0 + det.height_canonical
        draw_labeled_box(overlay, x0, y0, x1, y1, (255, 0, 0), f"b{i}")

    overlay_path = out_dir / "overlays" / f"{sample.cell_id}.png"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(overlay_path), overlay)

    return {
        "cell_id": sample.cell_id,
        "source_tag": sample.source_tag,
        "pdf_path": str(sample.pdf_path),
        "page": sample.page_1indexed,
        "system_index": sample.system_index,
        "staff_index": sample.staff_index,
        "measure_index": sample.measure_index,
        "cell_canonical_w": cell.width,
        "cell_canonical_h": cell.height,
        "front_matter_masked_count": n_masked,
        "n_noteheads_yolo": len(noteheads),
        "stem_filter_stats": stem_filter_stats,
        "predicted_stems_added": len(predicted_stems),
        "auto": {
            "cv_stem_count": len(cv_stems),
            "cv_beam_count": len(cv_beams),
            "stems": stems_info,
            "beams": beams_info,
            # Tier 2 summary: how many detections have low ink fill (likely FP)?
            "stems_low_ink_count": sum(1 for s in stems_info if s["ink_fill_ratio"] < 0.30),
            "beams_low_ink_count": sum(1 for b in beams_info if b["ink_fill_ratio"] < 0.30),
        },
        "overlay_path": str(overlay_path.relative_to(ROOT)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Verdict template
# ─────────────────────────────────────────────────────────────────────────────


def make_verdict_template(cells: list[dict]) -> dict:
    """Generate a JSON template the user fills in.

    For each cell:
      - stems_verdicts: list of {idx, judgment} for each CV-detected stem
      - stems_missed: count of stems CV missed entirely
      - beams_verdicts: same for beams
      - beams_missed: count
    """
    template = {"cells": []}
    for c in cells:
        template["cells"].append({
            "cell_id": c["cell_id"],
            "overlay_path": c["overlay_path"],
            "stems_count_cv": c["auto"]["cv_stem_count"],
            "stems_verdicts": [
                {"idx": s["idx"], "judgment": "?", "ink_fill_ratio": s["ink_fill_ratio"]}
                for s in c["auto"]["stems"]
            ],
            "stems_missed": "?",
            "beams_count_cv": c["auto"]["cv_beam_count"],
            "beams_verdicts": [
                {"idx": b["idx"], "judgment": "?", "ink_fill_ratio": b["ink_fill_ratio"]}
                for b in c["auto"]["beams"]
            ],
            "beams_missed": "?",
        })
    template["legend"] = {
        "judgment": "Set each to 'correct' (box is on a real stem/beam) or 'wrong' (false positive / hallucination)",
        "missed": "Replace '?' with an integer count of stems/beams that CV missed entirely (real ink that has NO bbox)",
        "workflow": [
            "1. Open each overlay PNG (overlays/<cell_id>.png)",
            "2. For each numbered green box (stems) and blue box (beams), set judgment to 'correct' or 'wrong'",
            "3. Count any real stems/beams that DON'T have a box and put that in stems_missed / beams_missed",
            "4. Save the file (do not change file names)",
            "5. Run: python3 score_verdicts.py path/to/this/verdicts.json",
        ],
    }
    return template


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="benchmarks/omr-stem-precision/run-001",
                    help="Output directory (relative to repo root)")
    args = ap.parse_args(argv[1:])

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output dir: {out_dir}")
    print(f"Cells: {len(CELL_SAMPLES)}")
    print()

    auto_stats = []
    for sample in CELL_SAMPLES:
        print(f"── {sample.cell_id} ({sample.source_tag}) ──")
        result = process_cell(sample, out_dir)
        if result is not None:
            auto_stats.append(result)
            print(f"  stems={result['auto']['cv_stem_count']} "
                  f"(low-ink={result['auto']['stems_low_ink_count']})  "
                  f"beams={result['auto']['cv_beam_count']} "
                  f"(low-ink={result['auto']['beams_low_ink_count']})")

    (out_dir / "auto_stats.json").write_text(json.dumps(auto_stats, indent=2))
    print(f"\nWrote {out_dir / 'auto_stats.json'} ({len(auto_stats)} cells)")

    template = make_verdict_template(auto_stats)
    template_path = out_dir / "verdicts_template.json"
    template_path.write_text(json.dumps(template, indent=2))
    print(f"Wrote {template_path}")
    print()
    print("Next steps for the human:")
    print(f"  1. Inspect overlays in {out_dir / 'overlays'}/")
    print(f"  2. Copy {template_path.name} → verdicts.json and fill in judgments")
    print(f"  3. Run score_verdicts.py verdicts.json")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
