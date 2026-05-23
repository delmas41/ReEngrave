"""Run the full Phase 1 pipeline on a PDF and report metrics + write
overlays for visual verification.

Usage:
    python3 -m tools.omr.run_pipeline <pdf> --pages 0,4,9 --out-dir benchmarks/omr-phase1/<slug>
    python3 -m tools.omr.run_pipeline <pdf> --pages 0-4 --out-dir <...>
    python3 -m tools.omr.run_pipeline <pdf>   # default: page 0 only
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import detect_barlines, extract_measures
from .staff_line_removal import remove_staff_lines
from .visualize import write_overlay


def parse_pages(spec: str, n_pages: int) -> list[int]:
    if not spec:
        return [0]
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 0 <= p < n_pages]


def main():
    ap = argparse.ArgumentParser(description="Phase 1 end-to-end OMR pipeline")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="", help="Comma-separated or range, e.g. '0,4,9' or '0-4'")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--write-cells", action="store_true", help="Also write each cell as PNG")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get page count
    import fitz
    doc = fitz.open(pdf)
    n_pages = doc.page_count
    doc.close()

    pages = parse_pages(args.pages, n_pages) or [0]
    print(f"\n{pdf.name}: {n_pages} pages, processing {pages}")
    print(f"out_dir: {out_dir}")

    summary = {
        "pdf": str(pdf),
        "n_pages_in_doc": n_pages,
        "dpi": args.dpi,
        "pages_processed": [],
    }

    total_t = 0.0
    for p in pages:
        t0 = time.perf_counter()
        page = render_page(pdf, p, dpi=args.dpi)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        t = time.perf_counter() - t0
        total_t += t

        n_systems = 1 + max((s.system_index for s in pws.staves), default=-1) if pws.staves else 0
        meas_per_sys: dict[int, list[int]] = {}
        for c in cells:
            meas_per_sys.setdefault(c.system_index, []).append(c.measure_index)
        meas_count_per_sys = {sys: 1 + max(m_idxs, default=-1) for sys, m_idxs in meas_per_sys.items()}

        page_summary = {
            "page": p,
            "render_size": [page.width, page.height],
            "skew_corrected_deg": page.skew_correction_deg,
            "staves": len(pws.staves),
            "systems": n_systems,
            "barlines": len(pws.barlines),
            "cells": len(cells),
            "measures_per_system": meas_count_per_sys,
            "runtime_s": round(t, 3),
        }
        if cells:
            sample = cells[0]
            page_summary["sample_cell"] = {
                "width": sample.width,
                "height": sample.height,
                "upscale_factor": round(sample.upscale_factor, 3),
                "staff_line_ys_canonical": sample.staff_line_ys_canonical,
            }
        summary["pages_processed"].append(page_summary)

        # Write overlay
        overlay_path = out_dir / f"page{p:03d}-overlay.png"
        write_overlay(pws, overlay_path, cells=cells)

        # Optional: write per-cell PNGs
        if args.write_cells:
            cell_dir = out_dir / f"page{p:03d}-cells"
            cell_dir.mkdir(parents=True, exist_ok=True)
            import cv2
            for c in cells:
                name = f"sys{c.system_index}_s{c.staff_index}_m{c.measure_index}.png"
                img = c.image
                if img.ndim == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(cell_dir / name), img)
                if c.image_no_staff is not None:
                    cv2.imwrite(str(cell_dir / name.replace('.png', '_nostaff.png')), c.image_no_staff)

        print(f"  page {p}: {len(pws.staves)} staves, {n_systems} systems, "
              f"{len(pws.barlines)} barlines, {len(cells)} cells, {t:.2f}s")
        if pws.staves:
            print(f"           measures/system: {meas_count_per_sys}")

    summary["total_runtime_s"] = round(total_t, 3)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote summary: {summary_path}")
    print(f"total time: {total_t:.2f}s for {len(pages)} pages")


if __name__ == "__main__":
    main()
