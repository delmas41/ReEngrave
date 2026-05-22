"""End-to-end OMR transcription: PDF → structured symbol detections.

This is the **simplest entry point** for running the ReEngrave OMR pipeline
on a music PDF. Combines Phase 1 (staff + measure detection) with Phase 3.3
(YOLOv8l symbol detection at 98.8% F1 on the Bach WTC verdict set) into a
single command that writes a structured JSON report.

CLI:

    python3 -m tools.omr.transcribe path/to/score.pdf --out out.json

    # Specific pages, with overlays
    python3 -m tools.omr.transcribe score.pdf --pages 0-4 --out out.json \\
        --overlays-dir overlays/

    # Specify a different weights file
    python3 -m tools.omr.transcribe score.pdf \\
        --weights tools/omr/training/data/weights/<other>.pt \\
        --out out.json

Output schema (JSON):

    {
      "source_pdf": "score.pdf",
      "weights":    "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt",
      "conf_threshold": 0.25,
      "n_pages_processed": 3,
      "n_systems_total": 6,
      "n_staves_total": 30,
      "n_measures_total": 84,
      "n_detections_total": 1923,
      "runtime": {"phase1_s": 8.2, "yolo_s": 4.1, "total_s": 12.3},
      "pages": [
        {
          "page_index": 0,        # 0-based, matches pdf2image/fitz numbering
          "page_size_px": [w, h], # at the source render DPI (default 600)
          "n_systems": 2,
          "systems": [
            {
              "system_index": 0,
              "n_staves": 5,
              "staves": [
                {
                  "staff_index": 0,
                  "clef": "treble",         # heuristic from staff_index in piano-style
                  "n_measures": 4,
                  "measures": [
                    {
                      "measure_index": 0,
                      "bbox_page_px": [x0, y0, x1, y1],
                      "n_detections": 12,
                      "detections": [
                        {
                          "class":      "noteheadBlack",
                          "category":   "notehead",
                          "bbox":       [x, y, w, h],  # in cell-local (canonical) coords
                          "bbox_page":  [x, y, w, h],  # in page-pixel coords
                          "confidence": 0.87,
                          "pitch":      "C4"            # if the wrapper inferred it
                        },
                        ...
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }

The "simplest transcription" path for a future agent / user:

    1. Render the PDF, find staves + measures (the OMR scaffolding).
    2. For each measure-cell, run YOLOv8l to detect notation symbols.
    3. Group detections by (system, staff, measure) and emit a JSON file.
    4. Optionally render overlay PNGs for visual inspection.

For richer downstream output (MusicXML, MIDI, LilyPond), this JSON is the
intermediate representation that other tools can consume.

Defaults are tuned for clean engraved PDFs (typeset music). Quality
degrades on handwritten or low-quality scanned scores; the model was
trained on the synthetic DeepScoresV2 corpus + ~60 hand-labeled real
orchestral cells. See benchmarks/omr-phase3.3/comparison-trained-v3.md
for the F1 numbers.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import detect_barlines, extract_measures
from .staff_line_removal import remove_staff_lines
from .types import MeasureCell


# Default weights — Phase 3.3, F1 98.8% on the 25 verdict cells.
# Keep this in sync with the latest "production" weights.
DEFAULT_WEIGHTS = (
    "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
)


def parse_pages(spec: str, n_pages: int) -> list[int]:
    """Accept '0,4,9' or '0-4' or '' (default all)."""
    if not spec:
        return list(range(n_pages))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 0 <= p < n_pages]


def _detections_for_cell(
    detector,  # YoloDetector — passed in to avoid import at module import time
    cell: MeasureCell,
    *,
    conf_threshold: float,
    imgsz: int,
    iou_threshold: float,
    agnostic_nms: bool,
) -> list[dict[str, Any]]:
    """Run YOLO on a single cell and return cleaned-up detection dicts."""
    dets = detector.detect(
        cell,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )
    out: list[dict[str, Any]] = []
    # Convert cell-local bbox → page-pixel bbox using the cell's offset + upscale.
    # cell.bbox_page_px gives the cell's origin on the source page (at source DPI).
    cell_x0, cell_y0, cell_x1, cell_y1 = cell.bbox_page_px
    cell_page_w = cell_x1 - cell_x0
    cell_page_h = cell_y1 - cell_y0
    canonical_w = max(1, cell.width)
    canonical_h = max(1, cell.height)
    for d in dets:
        # Cell-local bbox (canonical coords). SymbolDetection uses the
        # *_canonical names from template_matcher.SymbolDetection.
        cx = d.x_canonical
        cy = d.y_canonical
        cw = d.width_canonical
        ch = d.height_canonical
        # Scale into page pixels — proportionally map (cx, cy) from canonical
        # cell coords to (page_x0 + cx*page_w/canon_w) etc.
        page_x = cell_x0 + int(round(cx * cell_page_w / canonical_w))
        page_y = cell_y0 + int(round(cy * cell_page_h / canonical_h))
        page_w = max(1, int(round(cw * cell_page_w / canonical_w)))
        page_h = max(1, int(round(ch * cell_page_h / canonical_h)))
        out.append({
            "class": d.smufl_name,
            "category": d.category,
            "bbox": [cx, cy, cw, ch],
            "bbox_page": [page_x, page_y, page_w, page_h],
            "confidence": round(float(d.confidence), 3),
            "pitch": getattr(d, "pitch", None),
        })
    return out


def transcribe(
    *,
    pdf_path: Path,
    pages: list[int],
    weights: str,
    conf_threshold: float = 0.25,
    imgsz: int = 640,
    iou_threshold: float = 0.5,
    agnostic_nms: bool = True,
    dpi: int = 600,
    overlays_dir: Path | None = None,
    progress: bool = True,
) -> dict[str, Any]:
    """Run the full transcribe pipeline. Returns the structured dict.

    The defaults match what the Phase 3.3 evaluation used (conf=0.25,
    agnostic_nms=True). Lower conf_threshold (e.g. 0.10) for higher recall
    at the cost of more false positives.
    """
    # Lazy-import the YOLO wrapper so this module imports cheaply when the
    # caller doesn't actually need OMR (e.g. when listing pages).
    from .yolo_detector import YoloDetector

    detector = YoloDetector(weights, device="auto")

    out: dict[str, Any] = {
        "source_pdf": str(pdf_path),
        "weights": weights,
        "conf_threshold": conf_threshold,
        "iou_threshold": iou_threshold,
        "agnostic_nms": agnostic_nms,
        "imgsz": imgsz,
        "dpi": dpi,
        "n_pages_processed": 0,
        "n_systems_total": 0,
        "n_staves_total": 0,
        "n_measures_total": 0,
        "n_detections_total": 0,
        "runtime": {"phase1_s": 0.0, "yolo_s": 0.0, "total_s": 0.0},
        "pages": [],
    }

    t_total = time.perf_counter()
    for p in pages:
        t_phase1 = time.perf_counter()
        page = render_page(pdf_path, p, dpi=dpi)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        out["runtime"]["phase1_s"] += time.perf_counter() - t_phase1

        # Group cells by (system, staff). Keep them in measure_index order
        # within each group.
        systems: dict[int, dict[int, list[MeasureCell]]] = {}
        for c in cells:
            systems.setdefault(c.system_index, {}).setdefault(c.staff_index, []).append(c)
        for sys_idx in systems:
            for staff_idx in systems[sys_idx]:
                systems[sys_idx][staff_idx].sort(key=lambda c: c.measure_index)

        # Run YOLO on each cell + build the nested structure.
        page_dict: dict[str, Any] = {
            "page_index": p,
            "page_size_px": [page.width, page.height],
            "skew_corrected_deg": page.skew_correction_deg,
            "n_systems": len(systems),
            "systems": [],
        }

        t_yolo = time.perf_counter()
        for sys_idx in sorted(systems.keys()):
            sys_dict: dict[str, Any] = {
                "system_index": sys_idx,
                "n_staves": len(systems[sys_idx]),
                "staves": [],
            }
            for staff_idx in sorted(systems[sys_idx].keys()):
                staff_cells = systems[sys_idx][staff_idx]
                staff_dict: dict[str, Any] = {
                    "staff_index": staff_idx,
                    "n_measures": len(staff_cells),
                    "measures": [],
                }
                for cell in staff_cells:
                    detections = _detections_for_cell(
                        detector,
                        cell,
                        conf_threshold=conf_threshold,
                        imgsz=imgsz,
                        iou_threshold=iou_threshold,
                        agnostic_nms=agnostic_nms,
                    )
                    staff_dict["measures"].append({
                        "measure_index": cell.measure_index,
                        "bbox_page_px": list(cell.bbox_page_px),
                        "n_detections": len(detections),
                        "detections": detections,
                    })
                    out["n_detections_total"] += len(detections)
                    out["n_measures_total"] += 1
                sys_dict["staves"].append(staff_dict)
                out["n_staves_total"] += 1
            page_dict["systems"].append(sys_dict)
            out["n_systems_total"] += 1
        out["runtime"]["yolo_s"] += time.perf_counter() - t_yolo

        out["pages"].append(page_dict)
        out["n_pages_processed"] += 1

        if progress:
            n_dets = sum(
                m["n_detections"]
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
            )
            print(
                f"  page {p}: {len(systems)} systems, "
                f"{sum(len(staves) for staves in systems.values())} staves, "
                f"{sum(len(c) for staves in systems.values() for c in staves.values())} measures, "
                f"{n_dets} detections",
                flush=True,
            )

        # Overlay rendering (optional)
        if overlays_dir is not None:
            from .visualize import write_overlay
            overlays_dir.mkdir(parents=True, exist_ok=True)
            write_overlay(pws, overlays_dir / f"page{p:03d}-overlay.png", cells=cells)

    out["runtime"]["total_s"] = round(time.perf_counter() - t_total, 2)
    out["runtime"]["phase1_s"] = round(out["runtime"]["phase1_s"], 2)
    out["runtime"]["yolo_s"] = round(out["runtime"]["yolo_s"], 2)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="End-to-end OMR transcription: PDF → JSON detections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "    python3 -m tools.omr.transcribe score.pdf --out result.json\n"
            "    python3 -m tools.omr.transcribe score.pdf --pages 0-4 \\\n"
            "        --overlays-dir overlays/ --out result.json\n"
        ),
    )
    ap.add_argument("pdf", type=Path, help="Source PDF path")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output JSON file (default: stdout)")
    ap.add_argument("--pages", default="",
                    help="Pages to process: e.g. '0,4,9' or '0-4' (default: all)")
    ap.add_argument("--weights", default=DEFAULT_WEIGHTS,
                    help=f"YOLO weights path (default: {DEFAULT_WEIGHTS})")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection confidence threshold (default: 0.25)")
    ap.add_argument("--imgsz", type=int, default=640,
                    help="YOLO inference image size (default: 640)")
    ap.add_argument("--iou", type=float, default=0.5,
                    help="NMS IoU threshold (default: 0.5)")
    ap.add_argument("--no-agnostic-nms", action="store_true",
                    help="Disable agnostic NMS (default: enabled, collapses "
                         "overlapping boxes across classes)")
    ap.add_argument("--dpi", type=int, default=600,
                    help="Source-page render DPI (default: 600)")
    ap.add_argument("--overlays-dir", type=Path, default=None,
                    help="If set, write per-page overlay PNGs here")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress per-page progress logs")
    args = ap.parse_args(argv)

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        return 2

    if not Path(args.weights).exists():
        print(f"ERROR: weights file not found: {args.weights}")
        return 2

    # Count pages
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(args.pdf)
        n_pages = doc.page_count
        doc.close()
    except ImportError:
        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(args.pdf))
        n_pages = int(info.get("Pages", 0))

    pages = parse_pages(args.pages, n_pages)
    if not pages:
        print(f"ERROR: no valid pages selected from {args.pages!r} (doc has {n_pages})")
        return 2

    if not args.quiet:
        print(f"transcribe: {args.pdf.name} ({n_pages} pages, processing {len(pages)})")
        print(f"  weights:  {args.weights}")
        print(f"  conf:     {args.conf}, iou: {args.iou}, "
              f"agnostic_nms: {not args.no_agnostic_nms}, imgsz: {args.imgsz}")

    result = transcribe(
        pdf_path=args.pdf,
        pages=pages,
        weights=args.weights,
        conf_threshold=args.conf,
        imgsz=args.imgsz,
        iou_threshold=args.iou,
        agnostic_nms=not args.no_agnostic_nms,
        dpi=args.dpi,
        overlays_dir=args.overlays_dir,
        progress=not args.quiet,
    )

    if args.out is None:
        print(json.dumps(result, indent=2))
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        if not args.quiet:
            print(f"\nwrote {args.out}")
            print(f"  pages={result['n_pages_processed']}  "
                  f"systems={result['n_systems_total']}  "
                  f"staves={result['n_staves_total']}  "
                  f"measures={result['n_measures_total']}  "
                  f"detections={result['n_detections_total']}")
            print(f"  runtime: phase1={result['runtime']['phase1_s']}s  "
                  f"yolo={result['runtime']['yolo_s']}s  "
                  f"total={result['runtime']['total_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
