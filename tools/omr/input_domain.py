"""Classify a PDF's pages as SCANNED or ENGRAVED, before any model loads.

The two domains have different best-measured weights (see
``benchmarks/omr-weight-routing-2026-09/FINDINGS.md``): the hollow fine-tune
wins on scans (half-notes 8 -> 27 on beet5-p1) and the prior production
weights win on engraved input (11-work OMR-NED 0.1399 vs 0.1421). The weight
router asks this module which domain a run belongs to.

The discriminator is WHERE THE INK COMES FROM, not what it looks like:

- a scanned page's ink arrives as a full-page raster image (total raster
  coverage 0.95-1.0+ over every scan measured, including a Durand scan tiled
  into eight strips of 0.143 each — which is why the signal is TOTAL
  coverage, never max);
- an engraved page's ink arrives as vector drawings — staff lines, stems and
  barlines are path operations in every typesetter measured (LilyPond and two
  non-LilyPond digital typesets), 428-2058 paths per music page against 0-4
  on scans, with the gap in between empty over all 147 probed pages.

Text is deliberately NOT a signal: scans carry OCR text layers (IMSLP 575951)
and stamped text (Mozart K319, 175 chars on a 0.96-coverage page), so a page
with neither raster nor drawings — blank pages, text-only title pages —
ABSTAINS rather than guesses.

Both constants are read off measured gaps, not tuned; the populations either
side are in FINDINGS.md. Re-measure there before moving them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

# Nearest measured populations: 0.000 (engraved) / 0.95 (sparsest scan page).
SCAN_TOTAL_RASTER_COVERAGE = 0.5
# Nearest measured populations: 4 (busiest scan page) / 428 (lightest
# engraved music page).
ENGRAVED_MIN_DRAWINGS = 50
# Verdict pages examined when the caller does not name pages. Any-scan-wins
# means extra pages only ever flip the verdict TOWARD scanned, and 12 covers
# every cover-sheet/blank-page prefix seen in the library.
DEFAULT_CLASSIFY_PAGES = 12

SCANNED = "scanned"
ENGRAVED = "engraved"
UNKNOWN = "unknown"


@dataclass
class PageDomain:
    page_index: int
    verdict: str
    total_raster_coverage: float
    n_images: int
    n_drawings: int
    raster_filters: str

    def to_dict(self) -> dict:
        return {
            "page_index": self.page_index,
            "verdict": self.verdict,
            "total_raster_coverage": round(self.total_raster_coverage, 3),
            "n_images": self.n_images,
            "n_drawings": self.n_drawings,
            "raster_filters": self.raster_filters,
        }


@dataclass
class DomainClassification:
    verdict: str
    pages: list = field(default_factory=list)
    ms: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "ms": round(self.ms, 1),
            **({"reason": self.reason} if self.reason else {}),
            "pages": [p.to_dict() for p in self.pages],
        }


def _classify_page(doc, page_index: int) -> PageDomain:
    page = doc[page_index]
    area = abs(page.rect) or 1.0

    total_cov = 0.0
    infos = page.get_image_info()
    for info in infos:
        import fitz  # local: keep module importable without PyMuPDF

        total_cov += abs(fitz.Rect(info["bbox"])) / area

    filters: set[str] = set()
    if infos:
        for img in page.get_images(full=True):
            filt = doc.xref_get_key(img[0], "Filter")
            if filt and filt[0] != "null":
                filters.add(filt[1].strip("[]/ ").replace("/", "+"))

    if total_cov >= SCAN_TOTAL_RASTER_COVERAGE:
        # Raster-dominant. Checked FIRST so OCR text layers and stamped text
        # on scans can never outvote the image the ink actually lives in.
        return PageDomain(page_index, SCANNED, total_cov, len(infos), -1,
                          "+".join(sorted(filters)) or "-")

    try:
        n_drawings = len(page.get_cdrawings())
    except Exception:  # noqa: BLE001 — a parse failure is not evidence
        n_drawings = -1
    verdict = ENGRAVED if n_drawings >= ENGRAVED_MIN_DRAWINGS else UNKNOWN
    return PageDomain(page_index, verdict, total_cov, len(infos), n_drawings,
                      "+".join(sorted(filters)) or "-")


def classify_pdf_domain(
    pdf_path: Path,
    page_indices: Optional[Sequence[int]] = None,
) -> DomainClassification:
    """Classify the document over the pages a transcription will process.

    Never raises: a PDF this cannot open or parse abstains with verdict
    ``unknown`` (the pipeline's own preprocessing will report the real error),
    so routing can only ever fall back to the default weights, not fail a run.

    Document verdict, in order — the asymmetry matches the measured costs of
    misrouting (engraved-to-scan-weights costs +0.0022 pooled; scanned-to-
    engraved-weights forfeits the half-note gains):

    1. any page ``scanned``  -> ``scanned``   (an IMSLP scan behind a
       digitally generated cover page is a scan);
    2. else any ``engraved`` -> ``engraved``  (blank pages don't block);
    3. else                  -> ``unknown``.
    """
    t0 = time.perf_counter()
    try:
        import fitz
    except Exception as exc:  # noqa: BLE001
        return DomainClassification(UNKNOWN, [], 0.0,
                                    f"PyMuPDF unavailable: {exc}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        return DomainClassification(
            UNKNOWN, [], (time.perf_counter() - t0) * 1000.0,
            f"could not open PDF: {exc}")

    try:
        if page_indices is None:
            indices = range(min(doc.page_count, DEFAULT_CLASSIFY_PAGES))
        else:
            indices = [i for i in page_indices if 0 <= i < doc.page_count]

        pages: list[PageDomain] = []
        for i in indices:
            try:
                pages.append(_classify_page(doc, i))
            except Exception:  # noqa: BLE001 — abstain on the broken page
                pages.append(PageDomain(i, UNKNOWN, 0.0, 0, -1, "-"))
    finally:
        doc.close()

    if any(p.verdict == SCANNED for p in pages):
        verdict = SCANNED
    elif any(p.verdict == ENGRAVED for p in pages):
        verdict = ENGRAVED
    else:
        verdict = UNKNOWN
    return DomainClassification(verdict, pages,
                                (time.perf_counter() - t0) * 1000.0)
