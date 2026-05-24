#!/usr/bin/env python3
"""Phase D — auto-detect movement page boundaries across the IMSLP catalog.

For each PDF in tools/omr/training/data/imslp/{work}/pdfs/{edition}/, find:
  - front-matter pages (blank + title pages before any music)
  - movement-start pages (first staff top-y is below 18% of page height,
    indicating room for a tempo-marking title above the first system)
  - end of file

Writes a movements.yaml per edition.

Known limitations:
  - Attacca transitions (Beethoven 5 mvt 3 → mvt 4) don't have title-space
    breaks and won't be detected. The output marks `needs_manual_review: true`
    when detected_count < expected_count.
  - For pages with unusually compressed top-margin (some Eulenburg pocket
    scores, some 20th-century Japanese editions), the heuristic threshold
    may need per-edition tuning.

Run from anywhere:
    python3 benchmarks/omr-imslp-pipeline/phase_d_segment_movements.py
"""

from __future__ import annotations

import io
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402


REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"

# Detection thresholds, validated against imslp-52624 (1862 Breitkopf
# Beethoven 5) where mvts 1 and 2 yielded staff-top-frac = 0.34 and 0.25
# respectively, while continuation pages clustered at 0.05-0.10.
BLANK_DENSITY_MAX = 0.005
STAFF_TOP_FRAC_MVT_START_MIN = 0.18
PROBE_DPI = 150           # cheap enough; the staff y is robust to DPI

# Expected movement counts per work (from XML — could parse but hardcode is
# simpler and these are stable):
EXPECTED_MVTS = {
    "beethoven-symphony-1": 4,
    "beethoven-symphony-2": 4,
    "beethoven-symphony-3": 4,
    "beethoven-symphony-4": 4,
    "beethoven-symphony-5": 4,
    "beethoven-symphony-6": 5,   # Pastoral
    "beethoven-symphony-7": 4,
    "beethoven-symphony-8": 4,
    "beethoven-symphony-9": 4,
    "brahms-symphony-1": 4,
    "brahms-symphony-2": 4,
    "brahms-symphony-3": 4,
    "brahms-symphony-4": 4,
}


def classify_page(doc: fitz.Document, page_idx: int) -> tuple[float, Optional[float]]:
    """Return (full_ink_density, staff_top_frac). staff_top_frac is None if
    no staves could be detected (e.g., blank page)."""
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=fitz.Matrix(50/72, 50/72))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    arr = np.asarray(img)
    full = float((arr < 128).mean())

    if full < BLANK_DENSITY_MAX:
        return full, None

    # Run staff detection at slightly higher DPI for usable y values
    try:
        pi = render_page(doc.name, page_idx, dpi=PROBE_DPI)
        pws = detect_staves(pi)
    except Exception:
        return full, None

    if not pws.staves:
        return full, None
    first_y = min(s.top_y for s in pws.staves)
    return full, first_y / pi.height


def segment_pdf(pdf_path: Path) -> dict:
    """Return a dict describing the movement boundaries in this PDF."""
    doc = fitz.open(str(pdf_path))
    n_pages = len(doc)
    classifications = []
    for i in range(n_pages):
        full, top_frac = classify_page(doc, i)
        classifications.append((full, top_frac))
    doc.close()

    front_matter: list[int] = []
    mvt_starts: list[int] = []

    # Front matter = leading run of blank or title pages with no music staves.
    in_front = True
    for i, (full, top_frac) in enumerate(classifications):
        if in_front:
            # A page counts as front-matter if it's blank OR has very low
            # density (a title page typically has dense centered text but
            # low overall density — but that overlaps with sparse music).
            if top_frac is None or full < 0.04:
                front_matter.append(i + 1)
                continue
            # Found the first real music page — mvt 1 starts here.
            in_front = False
            mvt_starts.append(i + 1)
            continue
        # Within music: look for movement-start signals.
        if top_frac is None:
            # Blank page — usually a separator before a new mvt. Don't mark
            # it as a mvt start; the NEXT music page is the mvt start.
            continue
        if top_frac >= STAFF_TOP_FRAC_MVT_START_MIN:
            # Reject double-counting: must be at least 3 pages after the
            # previous mvt start.
            if not mvt_starts or i + 1 - mvt_starts[-1] >= 3:
                mvt_starts.append(i + 1)

    # Compose page-ranges per detected movement
    movements: list[dict] = []
    for j, start in enumerate(mvt_starts):
        end = (mvt_starts[j + 1] - 1) if j + 1 < len(mvt_starts) else n_pages
        movements.append({"mvt": j + 1, "pages": [start, end]})

    work_name = pdf_path.parent.parent.parent.name  # beethoven-symphony-N
    expected = EXPECTED_MVTS.get(work_name, 4)
    needs_review = len(movements) != expected

    return {
        "pdf_path": str(pdf_path),
        "total_pages": n_pages,
        "front_matter": front_matter,
        "detected_movements": movements,
        "detected_count": len(movements),
        "expected_count": expected,
        "needs_manual_review": needs_review,
        "review_reason": (
            f"detected {len(movements)} but expected {expected}; "
            f"likely attacca transitions or unusual layout"
        ) if needs_review else "",
    }


def write_yaml(out_path: Path, data: dict, work_name: str) -> None:
    lines = [
        "# Auto-generated by phase_d_segment_movements.py",
        f"# Source PDF: {data['pdf_path']}",
        f"# Generated:  {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"total_pdf_pages: {data['total_pages']}",
        f"front_matter: {data['front_matter']}",
        f"detected_count: {data['detected_count']}",
        f"expected_count: {data['expected_count']}",
        f"needs_manual_review: {str(data['needs_manual_review']).lower()}",
    ]
    if data["needs_manual_review"]:
        lines.append(f'review_reason: "{data["review_reason"]}"')
    lines.append("movements:")
    for m in data["detected_movements"]:
        start, end = m["pages"]
        lines.append(f"  mvt_{m['mvt']}: {{ pages: [{start}, {end}] }}")
    out_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    overall = []
    for work_dir in sorted(DATA_ROOT.iterdir()):
        if not work_dir.is_dir() or not work_dir.name.startswith(("beethoven-", "brahms-")):
            continue
        pdfs_dir = work_dir / "pdfs"
        if not pdfs_dir.exists():
            continue
        for edition_dir in sorted(pdfs_dir.iterdir()):
            pdf = edition_dir / "score.pdf"
            if not pdf.exists():
                continue
            print(f"\n{work_dir.name} / {edition_dir.name}")
            try:
                data = segment_pdf(pdf)
            except Exception as exc:
                print(f"  ! failed: {exc}")
                traceback.print_exc()
                continue
            write_yaml(edition_dir / "movements.yaml", data, work_dir.name)
            status = "OK" if not data["needs_manual_review"] else "REVIEW"
            print(f"  {status}: {data['total_pages']} pages, "
                  f"front_matter={data['front_matter']}, "
                  f"{data['detected_count']}/{data['expected_count']} mvts")
            for m in data["detected_movements"]:
                print(f"    mvt {m['mvt']}: pages {m['pages']}")
            overall.append({
                "work": work_dir.name,
                "edition": edition_dir.name,
                **data,
            })

    print("\n=== SUMMARY ===")
    total = len(overall)
    ok = sum(1 for o in overall if not o["needs_manual_review"])
    print(f"PDFs processed: {total}")
    print(f"Fully auto-detected: {ok}")
    print(f"Needs manual review: {total - ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
