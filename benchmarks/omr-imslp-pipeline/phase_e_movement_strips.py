#!/usr/bin/env python3
"""Phase E — render top-of-page strips for movement-boundary verification.

The v2 OCR segmenter under-detects movement starts on several editions
because top-15% OCR misses italic title text on faded scans (Beethoven 1
imslp-52848 and Beethoven 6 imslp-57857 are the obvious cases). We need
hand-curated movements.yaml for all 7 catalog-ready editions, so this
script gives us a visual contact sheet to spot-check candidate pages.

For one PDF the script does:
  1. Classify each page geometrically — render at 50 DPI, find first staff,
     compute first-staff-y / page-height.
  2. For pages where the ratio exceeds a (loose) threshold, render the
     top 35% of the page at ~600 px wide.
  3. Composite all candidate strips vertically into a single contact-sheet
     PNG, labeled with page number + staff-top ratio.

Then I read each contact sheet and decide where the movement boundaries
actually are.

Output:
  benchmarks/omr-imslp-pipeline/phase-e-output/strips-{work}-{edition}.png
  benchmarks/omr-imslp-pipeline/phase-e-output/candidates-{work}-{edition}.json
"""

from __future__ import annotations

import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
OUT_DIR = (
    REPO_ROOT
    / ".claude/worktrees/interesting-curran-3ca1b7"
    / "benchmarks/omr-imslp-pipeline/phase-e-output"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROBE_DPI = 50
STRIP_DPI = 150
STRIP_TOP_FRAC = 0.45       # capture top 45% of page (movement titles + first 1-2 systems)
STRIP_WIDTH_PX = 1400       # uniform output width — must be legible enough to read tempo titles

# Two thresholds. Pages with staff-top above 0.10 are *candidates*; pages
# above 0.18 are *strong candidates* (very large top margin → very likely
# a movement boundary). Strong candidates always get strips even if the
# first staff detection had low confidence.
LOOSE_THRESHOLD = 0.10
STRONG_THRESHOLD = 0.18


@dataclass
class PageGeometry:
    page_index: int                  # 0-indexed
    is_blank: bool
    first_staff_top_frac: float | None
    staff_count: int


def classify_page(doc: fitz.Document, page_idx: int) -> PageGeometry:
    page = doc[page_idx]
    pix = page.get_pixmap(matrix=fitz.Matrix(PROBE_DPI / 72, PROBE_DPI / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    arr = np.asarray(img)
    ink_frac = float((arr < 128).mean())
    if ink_frac < 0.005:
        return PageGeometry(page_idx, True, None, 0)
    try:
        pi = render_page(doc.name, page_idx, dpi=PROBE_DPI)
        pws = detect_staves(pi)
    except Exception:
        return PageGeometry(page_idx, False, None, 0)
    if not pws.staves:
        return PageGeometry(page_idx, False, None, 0)
    first_y = min(s.top_y for s in pws.staves)
    return PageGeometry(
        page_idx, False, first_y / pi.height, len(pws.staves)
    )


def render_top_strip(doc: fitz.Document, page_idx: int) -> Image.Image:
    """Return top STRIP_TOP_FRAC of the page as a PIL image of width
    STRIP_WIDTH_PX."""
    page = doc[page_idx]
    page_w_pt, page_h_pt = page.rect.width, page.rect.height
    zoom = STRIP_DPI / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    w, h = img.size
    strip = img.crop((0, 0, w, int(h * STRIP_TOP_FRAC)))
    if strip.width != STRIP_WIDTH_PX:
        new_h = int(strip.height * STRIP_WIDTH_PX / strip.width)
        strip = strip.resize((STRIP_WIDTH_PX, new_h), Image.LANCZOS)
    return strip


def annotate_strip(strip: Image.Image, label: str) -> Image.Image:
    """Stamp a label on a strip's left margin."""
    out = Image.new("RGB", (strip.width + 160, strip.height), "white")
    out.paste(strip, (160, 0))
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial.ttf", 24
        )
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((10, 10), label, fill="black", font=font, spacing=4)
    return out


def render_full_page(doc: fitz.Document, page_idx: int, dpi: int = 100) -> Image.Image:
    page = doc[page_idx]
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def build_strips(pdf_path: Path, label_prefix: str = "") -> tuple[Path, list[dict]]:
    doc = fitz.open(str(pdf_path))
    n_pages = len(doc)
    print(f"Classifying {n_pages} pages of {pdf_path.name} at {PROBE_DPI} DPI...")
    geometries = [classify_page(doc, i) for i in range(n_pages)]

    candidates = []
    for g in geometries:
        if g.first_staff_top_frac is None:
            continue
        if g.first_staff_top_frac >= LOOSE_THRESHOLD:
            strength = "strong" if g.first_staff_top_frac >= STRONG_THRESHOLD else "loose"
            candidates.append({
                "page": g.page_index + 1,
                "staff_top_frac": round(g.first_staff_top_frac, 4),
                "staff_count": g.staff_count,
                "strength": strength,
            })

    if not candidates:
        print(f"  no candidate pages (no page had first-staff-top > {LOOSE_THRESHOLD})")
        doc.close()
        return OUT_DIR / f"strips-{label_prefix}.png", candidates

    # Per-edition subdirectory so the per-page PNGs don't pollute the top
    # output dir.
    page_dir = OUT_DIR / f"pages-{label_prefix}"
    page_dir.mkdir(exist_ok=True)

    print(f"  {len(candidates)} candidate pages — rendering full pages at {STRIP_DPI} DPI")
    for cand in candidates:
        page_idx = cand["page"] - 1
        # Top-half of the page is enough to spot movement titles.
        full = render_full_page(doc, page_idx, dpi=STRIP_DPI)
        w, h = full.size
        top = full.crop((0, 0, w, h // 2))
        # Resize to STRIP_WIDTH_PX wide.
        if top.width != STRIP_WIDTH_PX:
            new_h = int(top.height * STRIP_WIDTH_PX / top.width)
            top = top.resize((STRIP_WIDTH_PX, new_h), Image.LANCZOS)
        label = (
            f"p{cand['page']:03d} | top {cand['staff_top_frac']*100:.1f}% | "
            f"{cand['staff_count']} staves | {cand['strength']}"
        )
        annotated = annotate_strip(top, label)
        out_path = page_dir / f"p{cand['page']:03d}.png"
        annotated.save(out_path, "PNG", optimize=True)

    out_json = OUT_DIR / f"candidates-{label_prefix}.json"
    out_json.write_text(json.dumps({
        "pdf": str(pdf_path),
        "total_pages": n_pages,
        "candidates": candidates,
    }, indent=2))
    print(f"  wrote per-page PNGs to {page_dir}")
    doc.close()
    return page_dir, candidates


def main(argv: list[str]) -> int:
    editions = [
        ("beethoven-symphony-1", "imslp-52848"),
        ("beethoven-symphony-2", "imslp-503997"),
        ("beethoven-symphony-2", "imslp-977672"),
        ("beethoven-symphony-4", "imslp-411721"),
        ("beethoven-symphony-6", "imslp-57857"),
        ("beethoven-symphony-8", "imslp-06303"),
        ("beethoven-symphony-8", "imslp-875077"),
    ]
    if len(argv) > 1 and argv[1] != "all":
        # filter to one
        wanted = argv[1]
        editions = [(w, e) for (w, e) in editions if e == wanted or w == wanted]

    for work, ed in editions:
        pdf = DATA_ROOT / work / "pdfs" / ed / "score.pdf"
        if not pdf.exists():
            print(f"{work}/{ed}: MISSING PDF")
            continue
        print(f"\n=== {work} / {ed} ===")
        build_strips(pdf, label_prefix=f"{work}-{ed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
