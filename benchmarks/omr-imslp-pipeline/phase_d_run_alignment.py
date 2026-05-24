#!/usr/bin/env python3
"""Phase D — run alignment across the IMSLP catalog.

For each (work, edition) pair under tools/omr/training/data/imslp/, run
cell-level alignment of the WHOLE PDF against the work's concatenated
XML (all movement .mxl files summed). Aggregates a per-edition delta
stat (PDF measure count vs. expected XML total) and writes a catalog
summary.

This bypasses the per-movement segmentation problem (which has noisy
auto-detection) and gives a catalog-level signal of how well the
alignment pipeline scales. Per-movement alignment can be re-attempted
once segmentation accuracy improves.

Resumable: writes per-PDF result JSONs as it goes. Re-running skips
PDFs that already have results.

Run from anywhere:
    python3 benchmarks/omr-imslp-pipeline/phase_d_run_alignment.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _import_cell_align():
    """Load phase_c_cell_align.py as a module, bypassing the hyphenated
    package path. Registers in sys.modules first to satisfy dataclass
    introspection in Python 3.9 (where _get_field looks up cls.__module__
    via sys.modules)."""
    name = "phase_c_cell_align"
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parent / "phase_c_cell_align.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _xml_total_measures(mxl_path: Path, cell_align) -> tuple[int, int, str]:
    """Return (xml_measure_count, repeat_count, repeat_style) for an .mxl."""
    measures, _ = cell_align.parse_xml_measures(mxl_path)
    info = cell_align.classify_xml_repeat_style(measures)
    return len(measures), info["repeat_count"], info["style"]


REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
OUT_DIR = REPO_ROOT / ".claude/worktrees/interesting-curran-3ca1b7/benchmarks/omr-imslp-pipeline/phase-d-output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Lower DPI for catalog-scale speed. 150 DPI is enough for measure-count
# alignment (staff detection is robust at this resolution); production
# pipeline uses 300-600.
CATALOG_DPI = 150


def run_one(work_dir: Path, edition_dir: Path, cell_align) -> dict | None:
    pdf = edition_dir / "score.pdf"
    if not pdf.exists():
        return None

    mxl_dir = work_dir / "musicxml"
    mxl_files = sorted(mxl_dir.glob("mvt-*.mxl"))
    if not mxl_files:
        return None

    # XML totals (cheap to compute)
    xml_total = 0
    xml_repeats_total = 0
    mvt_breakdown = []
    for mxl in mxl_files:
        n, repeats, style = _xml_total_measures(mxl, cell_align)
        xml_total += n
        xml_repeats_total += repeats
        mvt_breakdown.append({"mvt": mxl.stem, "measures": n, "repeats": repeats, "style": style})

    # PDF alignment over the WHOLE pdf (skip front matter via dropping zero-
    # cell pages later, but extract_cells_for_range handles non-music pages
    # gracefully — they just return 0 cells).
    import fitz
    doc = fitz.open(str(pdf))
    total_pages = len(doc)
    doc.close()

    print(f"  → PDF {pdf.name}: {total_pages} pages × XML {xml_total} measures")
    t0 = time.time()
    # Stream pages one at a time and accumulate only the measure counts.
    # Holding all per-page cell data in memory OOM-killed the script on
    # large facsimile PDFs (197+ pages × heavy bitmaps).
    pdf_detected = 0
    n_pages_processed = 0
    n_pages_errored = 0
    from tools.omr.preprocessing import render_page  # local import for memory locality
    from tools.omr.staff_detector import detect_staves
    from tools.omr.measure_extractor import extract_measures
    import gc
    for page_idx in range(total_pages):
        try:
            pi = render_page(pdf, page_idx, dpi=CATALOG_DPI)
            pws = detect_staves(pi)
            cells = extract_measures(pws)
        except Exception as e:
            n_pages_errored += 1
            continue
        # Accumulate the per-system measure counts (matches align_pair's
        # build_alignment math: sum of measures_in_each_system across
        # all systems on this page).
        sys_measures: dict[int, int] = {}
        for c in cells:
            sys_measures[c.system_index] = max(sys_measures.get(c.system_index, -1), c.measure_index)
        pdf_detected += sum(v + 1 for v in sys_measures.values())
        n_pages_processed += 1
        # Release memory before next page
        del pi, pws, cells
        if page_idx % 20 == 0:
            gc.collect()
    elapsed = time.time() - t0
    delta = pdf_detected - xml_total
    delta_pct = 100.0 * delta / max(xml_total, 1)
    return {
        "work": work_dir.name,
        "edition": edition_dir.name,
        "pdf_path": str(pdf),
        "total_pages": total_pages,
        "xml_total_measures": xml_total,
        "xml_movements": len(mxl_files),
        "xml_movement_breakdown": mvt_breakdown,
        "pdf_detected_measures": pdf_detected,
        "delta": delta,
        "delta_pct": delta_pct,
        "elapsed_seconds": elapsed,
        "dpi": CATALOG_DPI,
    }


def main() -> int:
    cell_align = _import_cell_align()

    results: list[dict] = []
    skipped = 0
    failures = 0

    for work_dir in sorted(DATA_ROOT.iterdir()):
        if not work_dir.is_dir() or not work_dir.name.startswith(("beethoven-", "brahms-")):
            continue
        pdfs_dir = work_dir / "pdfs"
        if not pdfs_dir.exists():
            continue
        for edition_dir in sorted(pdfs_dir.iterdir()):
            result_file = OUT_DIR / f"{work_dir.name}__{edition_dir.name}.json"
            if result_file.exists():
                try:
                    results.append(json.loads(result_file.read_text()))
                    skipped += 1
                    continue
                except Exception:
                    pass

            print(f"\n{work_dir.name} / {edition_dir.name}")
            try:
                r = run_one(work_dir, edition_dir, cell_align)
            except Exception as exc:
                print(f"  ! FAILED: {exc}")
                failures += 1
                continue
            if r is None:
                print("  (no PDF or no XMLs)")
                continue
            result_file.write_text(json.dumps(r, indent=2, default=str))
            results.append(r)
            print(f"  done in {r['elapsed_seconds']:.0f}s: "
                  f"XML {r['xml_total_measures']} vs PDF {r['pdf_detected_measures']} "
                  f"= delta {r['delta']:+d} ({r['delta_pct']:+.1f}%)")

    # Aggregate
    print(f"\n=== CATALOG SUMMARY ===")
    print(f"Processed: {len(results)}   (skipped existing: {skipped}, failed: {failures})")
    if results:
        deltas = [r["delta_pct"] for r in results]
        print(f"Delta %  mean: {sum(deltas)/len(deltas):+.1f}%")
        print(f"Delta %  min:  {min(deltas):+.1f}%")
        print(f"Delta %  max:  {max(deltas):+.1f}%")
        within_10 = sum(1 for d in deltas if abs(d) <= 10)
        within_20 = sum(1 for d in deltas if abs(d) <= 20)
        print(f"Editions within  ±10%: {within_10}/{len(results)}")
        print(f"Editions within  ±20%: {within_20}/{len(results)}")

    summary_file = OUT_DIR / "_catalog_summary.json"
    summary_file.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nFull results: {summary_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
