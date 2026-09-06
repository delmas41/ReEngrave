"""Ground truth: where each movement of a volume actually starts.

A movement opening is engraved differently from a continuation page — the
lineup is named in FULL in the left margin, and the first system is dropped
down the page to make room for a movement title and tempo. Both are visible
without OCR, and each is measured here so the two can corroborate rather than
one being trusted alone:

  margin_ink   dark fraction of the left `frac` of the page
  top_gap      how far down the page the first ink starts, in page heights

The caller reads the ranked rows against the print. This writes nothing and
decides nothing — it is here so the boundary rule below has something to be
scored against.
"""
from __future__ import annotations

import json
import sys

import fitz


def profile(pdf_path: str, frac: float = 0.085):
    doc = fitz.open(pdf_path)
    rows = []
    for pi in range(doc.page_count):
        page = doc[pi]
        r = page.rect
        margin = page.get_pixmap(
            dpi=72, clip=fitz.Rect(r.x0, r.y0, r.x0 + r.width * frac, r.y1),
            colorspace=fitz.csGRAY)
        ink = sum(1 for b in margin.samples if b < 160) / max(
            1, len(margin.samples))

        full = page.get_pixmap(dpi=36, colorspace=fitz.csGRAY)
        w, h = full.width, full.height
        buf = full.samples
        top_gap = 1.0
        for y in range(h):
            row = buf[y * w:(y + 1) * w]
            if sum(1 for b in row if b < 140) > w * 0.02:
                top_gap = y / h
                break
        rows.append({"page": pi, "margin_ink": round(ink, 5),
                     "top_gap": round(top_gap, 4)})
    return rows


def main():
    pdf = sys.argv[1]
    rows = profile(pdf)
    mean = sum(r["margin_ink"] for r in rows) / len(rows)
    print(f"pages={len(rows)}  margin-ink mean={mean:.5f}")
    print("\nranked by margin ink x top gap (a movement opening scores on both):")
    ranked = sorted(rows, key=lambda r: -(r["margin_ink"] / mean) * (
        1 + r["top_gap"]))
    for r in ranked[:12]:
        print(f"  page {r['page']:4d}  ink {r['margin_ink']:.5f}"
              f"  (x{r['margin_ink']/mean:4.2f})  top_gap {r['top_gap']:.3f}")
    if len(sys.argv) > 2:
        json.dump(rows, open(sys.argv[2], "w"), indent=1)
        print(f"\nwrote {sys.argv[2]}")


if __name__ == "__main__":
    main()
