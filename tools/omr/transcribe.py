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
      "n_noteheads_total": 412,             # all detections with category=="notehead"
      "n_noteheads_pitched_total": 405,     # those for which pitch resolution succeeded
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
                  "clef": "treble",         # starting clef for this staff (detected
                                            # from the first clef detection, or
                                            # heuristic default for piano top/bottom)
                  "clef_final": "bass",     # OPTIONAL — only present if a clef change
                                            # happened mid-staff (rare)
                  "n_measures": 4,
                  "measures": [
                    {
                      "measure_index": 0,
                      "bbox_page_px": [x0, y0, x1, y1],
                      "clef": "treble",     # active clef AT this measure
                      "n_detections": 12,
                      "detections": [
                        {
                          "class":      "noteheadBlack",
                          "category":   "notehead",
                          "bbox":       [x, y, w, h],  # in cell-local (canonical) coords
                          "bbox_page":  [x, y, w, h],  # in page-pixel coords
                          "confidence": 0.87,
                          "pitch":      "C4"            # null for non-noteheads and
                                                        # unpitched clefs (percussion);
                                                        # diatonic only — no key
                                                        # signature or accidentals yet
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
from .pitch_resolver import pitch_for_notehead


# Default weights — Phase 3.3, F1 98.8% on the 25 verdict cells.
# Keep this in sync with the latest "production" weights.
DEFAULT_WEIGHTS = (
    "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
)


# ---------------------------------------------------------------------------
# Clef inference helpers (Phase 4a — pitch resolution)
# ---------------------------------------------------------------------------
#
# Each notehead's pitch depends on the active clef of its staff. The detector
# emits clef detections (clefG → treble, clefF → bass, clefCAlto → alto, etc.)
# and we maintain an `active_clef` per staff that updates whenever a new clef
# detection appears. Default per-position heuristics handle the case where the
# first cell of a staff has no detected clef (rare on engraved music, but
# possible on a continuation page where the courtesy clef wasn't picked up).


def _clef_name_from_class(smufl: str) -> str | None:
    """Map a DSv2 clef class name to a pitch_resolver clef key.

    Returns None for unpitched / octave-marker clefs (we don't resolve pitches
    on those — leaves the noteheads' pitch field as null).
    """
    if not smufl:
        return None
    s = smufl.lower()
    if "calto" in s:
        return "alto"
    if "ctenor" in s:
        return "tenor"
    if s.startswith("clefg") or s == "gclef":
        return "treble"
    if s.startswith("cleff") or s == "fclef":
        return "bass"
    if "percussion" in s or s in ("clef8", "clef15"):
        return None
    if s.startswith("clefc") or s == "cclef":  # generic C-clef → alto fallback
        return "alto"
    return None


def _default_clef_for_position(position_in_system: int, system_size: int) -> str:
    """Best-guess clef before we see any clef detection.

    Piano-style (2 staves per system): top = treble, bottom = bass.
    Single-staff or anything-else default = treble. The first detected clef
    in the staff overrides this, so the default only matters when the
    detector misses the courtesy clef at the start of the staff.
    """
    if system_size == 2 and position_in_system == 1:
        return "bass"
    return "treble"


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
    active_clef: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Run YOLO on a single cell, attach pitches to noteheads, and emit
    cleaned-up detection dicts.

    Two things happen here beyond a raw YOLO call:

    1. **Clef tracking.** If this cell contains a clef detection, the active
       clef is updated to whatever the highest-confidence clef class maps to.
       The updated clef is returned so the caller can persist it for
       subsequent measures on the same staff.
    2. **Pitch resolution.** Each notehead detection's `pitch` field is
       resolved via `pitch_for_notehead(d, clef=active_clef)`. Falls back to
       `None` if there's no clef context yet, the clef is unpitched
       (percussion / octave-marker), or the resolver can't compute (cell has
       no staff lines).

    Returns `(detection_dicts, new_active_clef)`.
    """
    dets = detector.detect(
        cell,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )

    # ── Clef pass: update active_clef from the highest-confidence clef
    #    detection in this cell, if any. ──────────────────────────────────────
    best_clef_name: str | None = None
    best_clef_conf = -1.0
    for d in dets:
        if d.category != "clef":
            continue
        mapped = _clef_name_from_class(d.smufl_name)
        if mapped is None:
            continue
        if d.confidence > best_clef_conf:
            best_clef_name = mapped
            best_clef_conf = d.confidence
    if best_clef_name is not None:
        active_clef = best_clef_name

    # ── Build output dicts. Convert cell-local bbox → page-pixel bbox using
    #    the cell's offset + upscale. ───────────────────────────────────────
    out: list[dict[str, Any]] = []
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

        # Pitch resolution — only for noteheads, and only if we have a
        # current pitched clef. The resolver also returns None when the
        # cell lacks staff_line_ys_canonical (rare).
        pitch: str | None = None
        if d.category == "notehead" and active_clef is not None:
            pitch = pitch_for_notehead(d, clef=active_clef)

        out.append({
            "class": d.smufl_name,
            "category": d.category,
            "bbox": [cx, cy, cw, ch],
            "bbox_page": [page_x, page_y, page_w, page_h],
            "confidence": round(float(d.confidence), 3),
            "pitch": pitch,
        })
    return out, active_clef


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
        "n_noteheads_total": 0,
        "n_noteheads_pitched_total": 0,
        "runtime": {"phase1_s": 0.0, "yolo_s": 0.0, "total_s": 0.0},
        "pages": [],
    }

    # Active clef per (page_idx, system_idx, staff_idx). Survives across
    # cells within a staff so a clef stays in effect through a whole line
    # (until a clef-change detection updates it). NOT carried across pages —
    # the courtesy clef at the start of a new page should re-establish it,
    # and if the detector misses it the default heuristic kicks in.
    active_clef_by_staff: dict[tuple[int, int, int], str | None] = {}

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
            staff_keys = sorted(systems[sys_idx].keys())
            sys_dict: dict[str, Any] = {
                "system_index": sys_idx,
                "n_staves": len(systems[sys_idx]),
                "staves": [],
            }
            for position_in_system, staff_idx in enumerate(staff_keys):
                staff_cells = systems[sys_idx][staff_idx]
                # Pick a default clef for this staff. Will be overridden the
                # moment a clef detection appears (which on engraved music is
                # typically inside the very first cell).
                active_clef = active_clef_by_staff.get(
                    (p, sys_idx, staff_idx),
                    _default_clef_for_position(position_in_system, len(staff_keys)),
                )
                starting_clef = active_clef
                staff_dict: dict[str, Any] = {
                    "staff_index": staff_idx,
                    "clef": starting_clef,
                    "n_measures": len(staff_cells),
                    "measures": [],
                }
                for cell in staff_cells:
                    detections, active_clef = _detections_for_cell(
                        detector,
                        cell,
                        conf_threshold=conf_threshold,
                        imgsz=imgsz,
                        iou_threshold=iou_threshold,
                        agnostic_nms=agnostic_nms,
                        active_clef=active_clef,
                    )
                    staff_dict["measures"].append({
                        "measure_index": cell.measure_index,
                        "bbox_page_px": list(cell.bbox_page_px),
                        "clef": active_clef,
                        "n_detections": len(detections),
                        "detections": detections,
                    })
                    out["n_detections_total"] += len(detections)
                    out["n_measures_total"] += 1
                # Record the staff's first-cell clef on the staff dict, but
                # also record the *final* clef so a clef change mid-staff
                # surfaces somewhere obvious.
                if active_clef != starting_clef:
                    staff_dict["clef_final"] = active_clef
                active_clef_by_staff[(p, sys_idx, staff_idx)] = active_clef
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
            page_noteheads = sum(
                1
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
                for d in m["detections"]
                if d["category"] == "notehead"
            )
            page_pitched = sum(
                1
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
                for d in m["detections"]
                if d["category"] == "notehead" and d["pitch"] is not None
            )
            print(
                f"  page {p}: {len(systems)} systems, "
                f"{sum(len(staves) for staves in systems.values())} staves, "
                f"{sum(len(c) for staves in systems.values() for c in staves.values())} measures, "
                f"{n_dets} detections "
                f"({page_pitched}/{page_noteheads} noteheads pitched)",
                flush=True,
            )

        # Overlay rendering (optional)
        if overlays_dir is not None:
            from .visualize import write_overlay
            overlays_dir.mkdir(parents=True, exist_ok=True)
            write_overlay(pws, overlays_dir / f"page{p:03d}-overlay.png", cells=cells)

    # Final pass: count noteheads + pitch-resolved noteheads. Cheap (linear
    # over the already-built output) and saves consumers from doing it.
    n_noteheads = 0
    n_pitched = 0
    for page_d in out["pages"]:
        for sys_d in page_d["systems"]:
            for st_d in sys_d["staves"]:
                for m_d in st_d["measures"]:
                    for det in m_d["detections"]:
                        if det["category"] == "notehead":
                            n_noteheads += 1
                            if det["pitch"] is not None:
                                n_pitched += 1
    out["n_noteheads_total"] = n_noteheads
    out["n_noteheads_pitched_total"] = n_pitched

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
            print(f"  noteheads={result['n_noteheads_total']}  "
                  f"pitched={result['n_noteheads_pitched_total']}  "
                  f"({100 * result['n_noteheads_pitched_total'] // max(1, result['n_noteheads_total'])}% pitch coverage)")
            print(f"  runtime: phase1={result['runtime']['phase1_s']}s  "
                  f"yolo={result['runtime']['yolo_s']}s  "
                  f"total={result['runtime']['total_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
