"""How separable are scanned pages from born-digital engravings, before OCR?

Candidate signals, cheapest first — all read from the PDF itself, no rendering:
  drawings   vector path operations. An engraver emits thousands; a scan zero.
  images     a scan is ONE raster covering the page.
  cover      that image's area as a fraction of the page.
  fonts      embedded fonts. An engraving embeds its music font.
And one that needs a render:
  greys      fraction of pixels that are neither near-black nor near-white.
             Paper and print noise live there; a vector render does not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz
import numpy as np

ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")


def probe(pdf: Path, page_index: int = 0, render: bool = True) -> dict:
    with fitz.open(pdf) as doc:
        if page_index >= doc.page_count:
            page_index = 0
        page = doc[page_index]
        area = abs(page.rect.width * page.rect.height) or 1.0
        images = page.get_images(full=True)
        cover = 0.0
        for img in images:
            for r in page.get_image_rects(img[0]) or []:
                cover = max(cover, abs(r.width * r.height) / area)
        out = {
            "drawings": len(page.get_drawings()),
            "images": len(images),
            "cover": cover,
            "fonts": len(page.get_fonts(full=True)),
            "greys": float("nan"),
        }
        if render:
            pix = page.get_pixmap(dpi=100, colorspace=fitz.csGRAY)
            a = np.frombuffer(pix.samples, dtype=np.uint8)
            out["greys"] = float(((a > 40) & (a < 215)).mean())
    return out


CASES = [
    ("ENGRAVED  brahms fixture", ROOT / "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf", 0),
    ("ENGRAVED  beethoven fixture", ROOT / "benchmarks/omr-orchestral-e2e/fixtures/beethoven-sym5-mvt1.pdf", 0),
    ("ENGRAVED  mahler fixture", ROOT / "benchmarks/omr-orchestral-e2e/fixtures/mahler-sym5-mvt1.pdf", 0),
]
scans = sorted((ROOT / "library/editions").rglob("*.pdf"))
step = max(1, len(scans) // 14)
for pdf in scans[::step][:14]:
    CASES.append((f"library   {pdf.parent.parent.name}/{pdf.parent.name}"[:44], pdf, 12))

print(f"{'case':46s} {'draw':>7s} {'imgs':>5s} {'cover':>6s} {'fonts':>6s} {'greys':>7s}")
for label, pdf, pg in CASES:
    if not pdf.is_file():
        continue
    try:
        r = probe(pdf, pg)
    except Exception as exc:                                  # noqa: BLE001
        print(f"{label:46s} FAILED {type(exc).__name__}: {exc}")
        continue
    print(f"{label:46s} {r['drawings']:>7d} {r['images']:>5d} {r['cover']:>6.2f} "
          f"{r['fonts']:>6d} {r['greys']:>7.3f}")
