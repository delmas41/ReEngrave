#!/usr/bin/env python3
"""Phase K — emit YOLO labels for STRUCTURAL classes using CV-detected
positions for stems/beams, validated against XML counts.

Phase J relied on Verovio SVG positions warped via a homography that has
~5-20 px error — fatal for thin-line stems/beams. Phase K replaces the
stem/beam labels with classical-CV detections from tools.omr.line_detection,
which find the ACTUAL printed pixel positions. The XML is used only for
*validation*: per-cell, the CV-detected count must match the Verovio SVG
count within ±25% (stems) or ±50% (beams — see note below) — otherwise the
cell is dropped as likely noise.

Why looser tolerance on beams: the SVG count is one polygon per beam
*segment* between adjacent stems, but the CV detector counts horizontal
ink strokes (with stacked-beam splitting). On a 4-eighth-note group,
Verovio might emit one polygon while CV finds one stroke = match.
On a 4-sixteenth-note group, Verovio emits multiple polygons per level
while CV emits one stroke per level (after split). The counts can differ
by 2x cleanly without either being wrong.

Barlines remain identical to Phase J — synthesized at cell right edges
from the classical-CV detection inside extract_measures(). They're
already accurate.

Reuses:
  * phase_e.VerovioCache, build_pdf_xml_staff_map, PDF_DPI
  * phase_j.parse_measure_structural (only for COUNTS — positions discarded)
  * tools.omr.line_detection.detect_stems / detect_beams
  * tools.omr.preprocessing.render_page
  * tools.omr.staff_detector.detect_staves
  * tools.omr.measure_extractor.extract_measures

CLI:
  python3 benchmarks/omr-imslp-pipeline/phase_k_emit_labels.py \\
      --work beethoven-symphony-1 --edition imslp-52848 --mvt 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-imslp-pipeline"))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.line_detection import detect_stems, detect_beams  # noqa: E402

import phase_e_emit_labels as pe  # noqa: E402
import phase_j_emit_labels as pj  # noqa: E402


# Prod-208 class IDs (must match phase_j_emit_labels.py)
CLASS_STEM = 41
CLASS_BEAM = 121
CLASS_BARLINE = 207   # repurposed "staff" slot

DATA_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")
OUT_BASE = ROOT / "benchmarks/omr-imslp-pipeline/phase-k-labels"

# Validation tolerances — see module docstring for rationale.
STEM_COUNT_TOLERANCE = 0.25   # ±25%
BEAM_COUNT_TOLERANCE = 0.50   # ±50% (Verovio polygon-vs-CV-stroke counting is fuzzy)
# Minimum SVG count we'll trust as a non-zero signal — below this, the
# count-match check loses statistical meaning.
MIN_NONZERO_FOR_RATIO = 2


def _count_match(detected: int, expected: int, tolerance: float) -> bool:
    """Validate that detected count is within ±tolerance of expected.

    Edge cases:
      - If expected == 0: only accept if detected == 0 (no expected, no emission).
      - If expected < MIN_NONZERO_FOR_RATIO (i.e. 1): allow detected in
        {0, 1, 2} — ratio math is too noisy on a single expected item.
      - Else: |det - exp| / exp <= tolerance.
    """
    if expected == 0:
        return detected == 0
    if expected < MIN_NONZERO_FOR_RATIO:
        return detected <= expected + 1
    diff = abs(detected - expected)
    return (diff / expected) <= tolerance


def _canonical_det_to_page_bbox(
    det,
    cell,
) -> tuple[float, float, float, float]:
    """Convert a LineDetection (canonical coords) to page-pixel (cx, cy, w, h).

    Uses cell.bbox_page_px (page origin) and cell.upscale_factor
    (canonical_h / page_h_of_cell, so canonical / scale = page).
    """
    cx_canon = det.x_canonical + det.width_canonical / 2.0
    cy_canon = det.y_canonical + det.height_canonical / 2.0
    scale = cell.upscale_factor
    x0_page, y0_page = cell.bbox_page_px[0], cell.bbox_page_px[1]
    page_cx = x0_page + cx_canon / scale
    page_cy = y0_page + cy_canon / scale
    page_w = max(2.0, det.width_canonical / scale)
    page_h = max(2.0, det.height_canonical / scale)
    return float(page_cx), float(page_cy), float(page_w), float(page_h)


def to_yolo_norm(
    boxes: list[tuple[int, float, float, float, float]],
    image_w: int,
    image_h: int,
) -> list[tuple[int, float, float, float, float]]:
    out = []
    for cls, cx, cy, w, h in boxes:
        ncx = max(0.0, min(1.0, cx / image_w))
        ncy = max(0.0, min(1.0, cy / image_h))
        nw = max(0.0, min(1.0, w / image_w))
        nh = max(0.0, min(1.0, h / image_h))
        if nw <= 0 or nh <= 0:
            continue
        out.append((cls, ncx, ncy, nw, nh))
    return out


def process_movement(
    pdf_path: Path,
    mxl_path: Path,
    pdf_pages_1indexed: tuple[int, int],
    xml_staff_map: dict[int, int],
    out_dir: Path,
    debug_overlays: bool = True,
    max_pages: Optional[int] = None,
) -> dict:
    print(f"Loading Verovio cache for {mxl_path.name}...")
    cache = pe.VerovioCache(mxl_path)
    print(f"  indexed {len(cache._measure_index)} measures across "
          f"{cache.n_pages} Verovio pages")

    out_dir.mkdir(parents=True, exist_ok=True)
    labels_dir = out_dir / "labels"
    labels_dir.mkdir(exist_ok=True)
    overlays_dir = out_dir / "overlays"
    if debug_overlays:
        overlays_dir.mkdir(exist_ok=True)

    p_start, p_end = pdf_pages_1indexed
    running_measure = 0
    summary = {
        "movement_pages": [p_start, p_end],
        "pages_processed": 0,
        "cells_total": 0,
        "cells_with_xml_match": 0,
        "cells_stems_emitted": 0,
        "cells_stems_skipped_count_mismatch": 0,
        "cells_beams_emitted": 0,
        "cells_beams_skipped_count_mismatch": 0,
        "barlines_emitted": 0,
        "stems_emitted": 0,
        "beams_emitted": 0,
        "labels_total": 0,
    }

    pages_iter = range(p_start, p_end + 1)
    if max_pages is not None:
        pages_iter = list(pages_iter)[:max_pages]

    for pdf_page in pages_iter:
        print(f"\n── PDF page {pdf_page} ──")
        try:
            pi = render_page(pdf_path, pdf_page - 1, dpi=pe.PDF_DPI)
        except Exception as exc:
            print(f"  ! render_page failed: {exc}")
            continue
        try:
            pws = detect_staves(pi)
            cells = extract_measures(pws)
        except Exception as exc:
            print(f"  ! staff/measure extraction failed: {exc}")
            continue

        print(f"  page {pi.width}×{pi.height}, "
              f"{len(pws.staves)} staves, {len(cells)} cells")
        if not cells:
            continue

        cells_by_system_staff: dict[tuple[int, int], list] = {}
        for c in cells:
            cells_by_system_staff.setdefault(
                (c.system_index, c.staff_index), []
            ).append(c)
        for k in cells_by_system_staff:
            cells_by_system_staff[k].sort(key=lambda c: c.measure_index)

        page_labels: list[tuple[int, float, float, float, float]] = []
        page_overlay: list[tuple[str, float, float, float, float]] = []

        systems = sorted({c.system_index for c in cells})
        for sys_idx in systems:
            sys_cells = [c for c in cells if c.system_index == sys_idx]
            if not sys_cells:
                continue
            n_measures = max(c.measure_index for c in sys_cells) + 1
            staves_on_sys = sorted({c.staff_index for c in sys_cells})

            for staff_idx_within_page in staves_on_sys:
                staff_cells = cells_by_system_staff.get(
                    (sys_idx, staff_idx_within_page), []
                )
                if not staff_cells:
                    continue

                staff_idx_within_system = staves_on_sys.index(staff_idx_within_page)
                xml_staff = xml_staff_map.get(staff_idx_within_system)
                if xml_staff is None:
                    continue

                pdf_staff = next(
                    (s for s in pws.staves if s.staff_index == staff_idx_within_page),
                    None,
                )
                if pdf_staff is None:
                    continue

                for cell in staff_cells:
                    summary["cells_total"] += 1
                    xml_n = str(running_measure + cell.measure_index + 1)
                    hit = cache.find_measure(xml_n)
                    if hit is None:
                        continue
                    summary["cells_with_xml_match"] += 1
                    vpage, mid = hit
                    svg = cache.svg(vpage)
                    staves_data = pj.parse_measure_structural(svg, mid)
                    if xml_staff >= len(staves_data):
                        continue
                    sd = staves_data[xml_staff]

                    expected_stems = len(sd.stems)
                    expected_beams = len(sd.beams)

                    cv_stems = detect_stems(cell)
                    cv_beams = detect_beams(cell)

                    # ─── Stems ─────────────────────────────────────────────
                    if _count_match(len(cv_stems), expected_stems, STEM_COUNT_TOLERANCE):
                        if cv_stems:
                            summary["cells_stems_emitted"] += 1
                            for det in cv_stems:
                                page_cx, page_cy, page_w, page_h = (
                                    _canonical_det_to_page_bbox(det, cell)
                                )
                                page_labels.append((
                                    CLASS_STEM, page_cx, page_cy, page_w, page_h,
                                ))
                                page_overlay.append((
                                    "stem", page_cx, page_cy, page_w, page_h,
                                ))
                                summary["stems_emitted"] += 1
                    else:
                        summary["cells_stems_skipped_count_mismatch"] += 1

                    # ─── Beams ─────────────────────────────────────────────
                    if _count_match(len(cv_beams), expected_beams, BEAM_COUNT_TOLERANCE):
                        if cv_beams:
                            summary["cells_beams_emitted"] += 1
                            for det in cv_beams:
                                page_cx, page_cy, page_w, page_h = (
                                    _canonical_det_to_page_bbox(det, cell)
                                )
                                page_labels.append((
                                    CLASS_BEAM, page_cx, page_cy, page_w, page_h,
                                ))
                                page_overlay.append((
                                    "beam", page_cx, page_cy, page_w, page_h,
                                ))
                                summary["beams_emitted"] += 1
                    else:
                        summary["cells_beams_skipped_count_mismatch"] += 1

                    # ─── Barline (synthesized at cell right edge) ──────────
                    cx0, cy0, cx1, cy1 = cell.bbox_page_px
                    barline_top = float(pdf_staff.top_y) - 3
                    barline_bot = float(pdf_staff.bottom_y) + 3
                    barline_cy = (barline_top + barline_bot) / 2
                    barline_h = barline_bot - barline_top
                    barline_w = max(4.0, barline_h * 0.025)
                    page_labels.append((
                        CLASS_BARLINE,
                        float(cx1), barline_cy,
                        barline_w, barline_h,
                    ))
                    page_overlay.append((
                        "barline", float(cx1), barline_cy,
                        barline_w, barline_h,
                    ))
                    summary["barlines_emitted"] += 1

            running_measure += n_measures

        yolo = to_yolo_norm(page_labels, pi.width, pi.height)
        summary["labels_total"] += len(yolo)
        label_path = labels_dir / f"p{pdf_page:03d}.txt"
        with label_path.open("w") as f:
            for cls, cx, cy, w, h in yolo:
                f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        if debug_overlays:
            overlay = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR).copy()
            colors = {
                "stem":    (0, 200, 0),     # green
                "beam":    (255, 0, 0),     # blue
                "barline": (0, 0, 255),     # red
            }
            for kind, cx, cy, w, h in page_overlay:
                col = colors.get(kind, (128, 128, 128))
                x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
                x1 = int(round(cx + w / 2)); y1 = int(round(cy + h / 2))
                cv2.rectangle(overlay, (x0, y0), (x1, y1), col, 2)
            cv2.imwrite(str(overlays_dir / f"p{pdf_page:03d}.png"), overlay)

        summary["pages_processed"] += 1
        print(f"  wrote {len(yolo)} labels "
              f"(stems={summary['stems_emitted']} beams={summary['beams_emitted']} "
              f"barlines={summary['barlines_emitted']}) → {label_path.name}")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nSummary: {summary}")
    return summary


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="beethoven-symphony-1")
    parser.add_argument("--edition", default="imslp-52848")
    parser.add_argument("--mvt", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--no-overlays", action="store_true")
    args = parser.parse_args(argv[1:])

    pdf = DATA_ROOT / args.work / "pdfs" / args.edition / "score.pdf"
    mxl = DATA_ROOT / args.work / "musicxml" / f"mvt-{args.mvt}.mxl"
    yml = DATA_ROOT / args.work / "pdfs" / args.edition / "movements.yaml"
    for p in (pdf, mxl, yml):
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            return 1

    movements = yaml.safe_load(yml.read_text())
    mvt_key = f"mvt_{args.mvt}"
    if mvt_key not in movements["movements"]:
        print(f"{mvt_key} not in {yml}", file=sys.stderr)
        return 1
    pages = movements["movements"][mvt_key]["pages"]
    p_start, p_end = pages

    out_dir = OUT_BASE / f"{args.work}-{args.edition}-mvt{args.mvt}"
    print(f"Working on {args.work}/{args.edition} mvt {args.mvt}, "
          f"pages {p_start}-{p_end}")
    print(f"Out: {out_dir}")

    xml_staff_map = pe.build_pdf_xml_staff_map(mxl)
    print(f"PDF→XML staff map: {xml_staff_map}")

    process_movement(
        pdf_path=pdf,
        mxl_path=mxl,
        pdf_pages_1indexed=(p_start, p_end),
        xml_staff_map=xml_staff_map,
        out_dir=out_dir,
        debug_overlays=not args.no_overlays,
        max_pages=args.max_pages,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
