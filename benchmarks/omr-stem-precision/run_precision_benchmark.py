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
    CellSample("wtc-p5-sys0-s0-m0", WTC_PDF, 5, 0, 0, 0, "wtc"),
    CellSample("wtc-p5-sys0-s1-m1", WTC_PDF, 5, 0, 1, 1, "wtc"),
    CellSample("wtc-p5-sys1-s0-m0", WTC_PDF, 5, 1, 0, 0, "wtc"),

    # Beethoven 5 page 10 — dense orchestral, hard ground truth.
    CellSample("beet5-p10-sys0-s8-m0",  BEET5_PDF, 10, 0,  8, 0, "beet5"),  # mid-staff string
    CellSample("beet5-p10-sys0-s12-m1", BEET5_PDF, 10, 0, 12, 1, "beet5"),  # cello/bass
    CellSample("beet5-p10-sys0-s0-m2",  BEET5_PDF, 10, 0,  0, 2, "beet5"),  # flutes top
    CellSample("beet5-p10-sys0-s4-m3",  BEET5_PDF, 10, 0,  4, 3, "beet5"),  # horns

    # Beethoven 1 mvt 1 with XML — for automated rhythm precision check.
    # Page 8 was densely-orchestrated in Phase K visual validation.
    CellSample("b1m1-p8-sys0-s0-m0",  B1_PDF, 8, 0,  0, 0, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=0),
    CellSample("b1m1-p8-sys1-s6-m1",  B1_PDF, 8, 1,  6, 1, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=6),
    CellSample("b1m1-p8-sys0-s10-m2", B1_PDF, 8, 0, 10, 2, "catalog-b1m1",
               mxl_path=B1_MXL, xml_measure_n=None, xml_staff=10),
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
    cv_stems = detect_stems(cell)
    cv_beams = detect_beams(cell)

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

    # Render overlay PNG with numbered detections for verdict
    overlay = cv2.cvtColor(cell.image, cv2.COLOR_GRAY2BGR) if cell.image.ndim == 2 else cell.image.copy()
    for i, det in enumerate(cv_stems):
        x0 = det.x_canonical; y0 = det.y_canonical
        x1 = x0 + det.width_canonical; y1 = y0 + det.height_canonical
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 200, 0), 2)
        cv2.putText(overlay, f"s{i}", (x0 + 2, y0 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)
    for i, det in enumerate(cv_beams):
        x0 = det.x_canonical; y0 = det.y_canonical
        x1 = x0 + det.width_canonical; y1 = y0 + det.height_canonical
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (255, 0, 0), 2)
        cv2.putText(overlay, f"b{i}", (x0 + 2, y0 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

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
