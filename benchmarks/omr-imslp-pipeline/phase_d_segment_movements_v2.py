#!/usr/bin/env python3
"""Phase D — improved movement segmentation using OCR confirmation.

v1 (phase_d_segment_movements.py) used a pure geometric heuristic — pages
whose first detected staff sits below 18% of the page height are flagged
as movement starts. That gave too many false positives on editions with
running page headers (which push the first staff down without indicating
a movement break).

v2 uses a two-stage approach:
  1. Geometric prefilter: any page whose first-staff-y is below 12% of
     the page height is a CANDIDATE.
  2. OCR confirmation: render the top 15% of the candidate page and OCR
     it. Reject the candidate unless the recognized text contains a
     movement marker — a Roman numeral followed by a period (I. II. III.
     IV. V.), or a known tempo word (Allegro, Andante, Adagio, Presto,
     Largo, Vivace, Scherzo, Finale, etc.). Real movement-start pages
     have these as centered title text above the first system.

Output: same movements.yaml format as v1.

Run from anywhere:
    python3 benchmarks/omr-imslp-pipeline/phase_d_segment_movements_v2.py
"""

from __future__ import annotations

import io
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

import pytesseract  # noqa: E402

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"

BLANK_DENSITY_MAX = 0.005
STAFF_TOP_FRAC_CANDIDATE_MIN = 0.12   # cheap pre-filter; OCR refines
PROBE_DPI = 150
OCR_DPI = 200                          # higher for OCR readability

# Tempo / movement markers we recognize. Case-insensitive contains.
TEMPO_WORDS = [
    "allegro", "andante", "adagio", "presto", "largo", "lento",
    "vivace", "moderato", "grave", "scherzo", "menuett", "minuetto",
    "finale", "rondo", "rondeau", "intermezzo", "marcia", "menuetto",
    "molto", "assai", "ma non troppo", "con brio", "con moto",
    "con fuoco", "con grazia", "tempo di", "andantino",
]
ROMAN_NUMERAL_RE = re.compile(r"\b(I|II|III|IV|V|VI|VII|VIII)\.\s", re.IGNORECASE)

EXPECTED_MVTS = {
    "beethoven-symphony-1": 4,
    "beethoven-symphony-2": 4,
    "beethoven-symphony-3": 4,
    "beethoven-symphony-4": 4,
    "beethoven-symphony-5": 4,
    "beethoven-symphony-6": 5,
    "beethoven-symphony-7": 4,
    "beethoven-symphony-8": 4,
    "beethoven-symphony-9": 4,
    "brahms-symphony-1": 4,
    "brahms-symphony-2": 4,
    "brahms-symphony-3": 4,
    "brahms-symphony-4": 4,
}


def ocr_top_strip(doc: fitz.Document, page_idx: int) -> str:
    """Render the top 15% of a page at OCR_DPI and OCR it. Returns the
    recognized text (lowercased) or an empty string on failure."""
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    w, h = img.size
    top = img.crop((0, 0, w, int(h * 0.15)))
    try:
        text = pytesseract.image_to_string(top)
        return text.lower()
    except Exception:
        return ""


def looks_like_movement_start(text: str) -> tuple[bool, str]:
    """Check the OCR text for movement-marker indicators. Returns
    (is_match, reason_label)."""
    if not text.strip():
        return False, ""
    # Roman numeral followed by a period (e.g. "II. Andante con moto")
    rn = ROMAN_NUMERAL_RE.search(text)
    if rn:
        return True, f"roman={rn.group(0).strip()}"
    # Tempo word
    for word in TEMPO_WORDS:
        if word in text:
            return True, f"tempo={word}"
    return False, ""


def classify_page(doc: fitz.Document, page_idx: int) -> tuple[float, Optional[float]]:
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=fitz.Matrix(50/72, 50/72))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    arr = np.asarray(img)
    full = float((arr < 128).mean())
    if full < BLANK_DENSITY_MAX:
        return full, None
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
    doc = fitz.open(str(pdf_path))
    n_pages = len(doc)

    geometry = [classify_page(doc, i) for i in range(n_pages)]

    front_matter: list[int] = []
    mvt_starts: list[tuple[int, str]] = []  # (page_1indexed, reason)
    in_front = True

    for i, (full, top_frac) in enumerate(geometry):
        if in_front:
            if top_frac is None or full < 0.04:
                front_matter.append(i + 1)
                continue
            in_front = False
            # First music page = mvt 1 start (always accept the first one)
            mvt_starts.append((i + 1, "first-music-page"))
            continue
        if top_frac is None:
            continue
        if top_frac < STAFF_TOP_FRAC_CANDIDATE_MIN:
            continue
        # Geometric candidate — confirm with OCR
        ocr_text = ocr_top_strip(doc, i)
        is_match, reason = looks_like_movement_start(ocr_text)
        if is_match:
            # Reject if too close to last mvt start (< 3 pages)
            if mvt_starts and i + 1 - mvt_starts[-1][0] < 3:
                continue
            mvt_starts.append((i + 1, reason))

    doc.close()

    movements = []
    for j, (start, reason) in enumerate(mvt_starts):
        end = (mvt_starts[j + 1][0] - 1) if j + 1 < len(mvt_starts) else n_pages
        movements.append({"mvt": j + 1, "pages": [start, end], "detection": reason})

    work_name = pdf_path.parent.parent.parent.name
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
            f"detected {len(movements)} but expected {expected}"
        ) if needs_review else "",
    }


def write_yaml(out_path: Path, data: dict) -> None:
    lines = [
        "# Auto-generated by phase_d_segment_movements_v2.py (OCR-confirmed)",
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
        lines.append(f"  mvt_{m['mvt']}: {{ pages: [{start}, {end}], detection: \"{m['detection']}\" }}")
    out_path.write_text("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    # Allow a single PDF path argument for testing
    if len(argv) > 1:
        pdf = Path(argv[1])
        print(f"Testing single PDF: {pdf}")
        data = segment_pdf(pdf)
        write_yaml(pdf.parent / "movements_v2.yaml", data)
        for m in data["detected_movements"]:
            print(f"  mvt {m['mvt']}: pages {m['pages']} ({m['detection']})")
        return 0

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
            write_yaml(edition_dir / "movements_v2.yaml", data)
            status = "OK" if not data["needs_manual_review"] else "REVIEW"
            print(f"  {status}: {data['detected_count']}/{data['expected_count']} mvts")
            for m in data["detected_movements"]:
                print(f"    mvt {m['mvt']}: pages {m['pages']} ({m['detection']})")
            overall.append(data)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
