#!/usr/bin/env python3
"""Phase E — full-PDF contact-sheet renderer for movement-boundary
identification.

The geometric heuristic in phase_e_movement_strips.py fails on dense
orchestral pages — the staff detector misses early staves, making the
"first-staff-y" metric meaningless for movement-start detection.

So instead, render every page of a PDF at thumbnail resolution into a
single tiled contact-sheet PNG (or a few of them for long PDFs). At
~250 px per thumbnail, movement-start pages stand out visually:
  - Large top margin
  - Title text ("II. Andante con moto", etc.)
  - First-system instrument labels in full (vs. abbreviations on
    continuation pages)

Output:
  phase-e-output/contact-{work}-{edition}.png
  phase-e-output/contact-{work}-{edition}-page-coords.json
"""

from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
OUT_DIR = (
    REPO_ROOT
    / ".claude/worktrees/interesting-curran-3ca1b7"
    / "benchmarks/omr-imslp-pipeline/phase-e-output"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

THUMB_DPI = 80
THUMB_WIDTH = 360
THUMB_LABEL_HEIGHT = 28
COLS = 5             # 5 thumbs per row → wide enough to read tempo text in each
PAGES_PER_SHEET = 30  # 6 rows × 5 cols per sheet; long PDFs span multiple sheets


def render_thumb(doc: fitz.Document, page_idx: int) -> Image.Image:
    page = doc[page_idx]
    zoom = THUMB_DPI / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    # Scale to uniform width
    if img.width != THUMB_WIDTH:
        new_h = int(img.height * THUMB_WIDTH / img.width)
        img = img.resize((THUMB_WIDTH, new_h), Image.LANCZOS)
    return img


def add_label(thumb: Image.Image, label: str) -> Image.Image:
    out = Image.new(
        "RGB", (thumb.width, thumb.height + THUMB_LABEL_HEIGHT), "white"
    )
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial.ttf", 18
        )
    except OSError:
        font = ImageFont.load_default()
    draw.text((4, 4), label, fill="black", font=font)
    out.paste(thumb, (0, THUMB_LABEL_HEIGHT))
    return out


def build_contact_sheet(pdf_path: Path, label_prefix: str) -> list[Path]:
    doc = fitz.open(str(pdf_path))
    n_pages = len(doc)
    print(f"Rendering {n_pages} thumbnails at {THUMB_DPI} DPI...")

    thumbs = []
    for i in range(n_pages):
        t = render_thumb(doc, i)
        thumbs.append(add_label(t, f"p{i+1:03d}"))

    # Common height — pad shorter thumbs to match the tallest.
    max_h = max(t.height for t in thumbs)
    padded = []
    for t in thumbs:
        if t.height < max_h:
            p = Image.new("RGB", (t.width, max_h), "white")
            p.paste(t, (0, 0))
            padded.append(p)
        else:
            padded.append(t)

    n_sheets = math.ceil(n_pages / PAGES_PER_SHEET)
    sheet_paths = []
    for sheet_idx in range(n_sheets):
        start = sheet_idx * PAGES_PER_SHEET
        end = min(start + PAGES_PER_SHEET, n_pages)
        sheet_thumbs = padded[start:end]
        rows = math.ceil(len(sheet_thumbs) / COLS)
        sheet_w = COLS * THUMB_WIDTH
        sheet_h = rows * max_h
        sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
        for j, t in enumerate(sheet_thumbs):
            r, c = divmod(j, COLS)
            sheet.paste(t, (c * THUMB_WIDTH, r * max_h))
        suffix = "" if n_sheets == 1 else f"-{sheet_idx + 1:02d}"
        out_path = OUT_DIR / f"contact-{label_prefix}{suffix}.png"
        sheet.save(out_path, "PNG", optimize=True)
        print(f"  wrote {out_path} (pages {start+1}-{end})")
        sheet_paths.append(out_path)

    doc.close()
    return sheet_paths


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
        wanted = argv[1]
        editions = [(w, e) for (w, e) in editions if e == wanted or w == wanted]

    for work, ed in editions:
        pdf = DATA_ROOT / work / "pdfs" / ed / "score.pdf"
        if not pdf.exists():
            print(f"{work}/{ed}: MISSING PDF")
            continue
        print(f"\n=== {work} / {ed} ===")
        build_contact_sheet(pdf, label_prefix=f"{work}-{ed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
