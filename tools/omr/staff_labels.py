"""Read instrument labels from a PDF's text layer and join them to staves.

Many scanned scores carry an OCR text layer. The music glyphs come through as
garbage, but the **margin labels are clean** — measured across the IMSLP corpus
in `tools/omr/training/data/imslp`, 18 of 65 score PDFs (28%) yield extractable
text, and the sampled pages returned `Fl. / Ob. / Cl. / Fag. / Cor. / Tr. /
Timp. / Vl. / Vla. / Vc. / Cb.`, with one page giving a full instrumentation
list (`2 Flauti / 2 Oboi / 2 Clarinetti in C / ...`).

That makes this the cheapest possible route to instrument identity: no OCR
dependency, no model, no API call. It is the first half of contextual-analysis
item #2 (NOTES.md); scans with no text layer still need a reader.

## The coordinate problem

`preprocessing.render_page` rasterizes at `dpi` **and then deskews**, so text
coordinates from PyMuPDF do not land on the page pixels a `Staff` is measured
in. Mapping needs both steps:

    1. PDF points -> pixels:  (pt - page.rect.origin) * dpi/72
    2. the same rotation deskew applied, about the image centre, by
       `PageImage.skew_correction_deg`

Both are replicated in `_pdf_to_pixel_transform`. Skipping step 2 is a real
error, not a rounding one: at 1 degree of skew a label 1000 px left of centre
shifts ~17 px vertically, and staves are only ~150 px apart.

## Matching rule

Everything left of the staves is a candidate label. Spans are grouped by the
staff whose vertical band they fall in (or nearest, within half an inter-staff
distance), then **joined per staff before lookup** — a label's key is often
engraved on its own line below the name (`Cor.` over `(Es)`), and only the
joined string resolves to "horn in E-flat".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from .instruments import Instrument, lookup
from .types import PageWithStaves, Staff

# Labels sit left of the staves. Allow a little overlap into the staff for
# scores that print the name tight against the bracket.
LABEL_RIGHT_MARGIN_PX = 40

# A span must land within this fraction of the inter-staff distance of a
# staff's centre to be claimed by it.
MAX_STAFF_DISTANCE_FRAC = 0.5

# Spans shorter than this are page numbers / stray OCR marks.
MIN_LABEL_CHARS = 1


@dataclass(frozen=True)
class StaffLabel:
    """What the text layer says about one staff."""

    staff_index: int
    text: str                       # joined raw text of every span claimed
    instrument: Instrument | None   # None when nothing in the lexicon matched
    fifths_offset: int              # written key = concert key + this
    y_center_px: float
    confidence: str = "none"        # high | medium | low | none — see instruments.Match
    alias: str = ""                 # the alias that fired, for auditing a bad read

    @property
    def matched(self) -> bool:
        return self.instrument is not None


def _pdf_to_pixel_transform(page: fitz.Page, dpi: int, skew_deg: float,
                            width: int, height: int):
    """Return f(x_pt, y_pt) -> (x_px, y_px) in deskewed page-pixel space."""
    zoom = dpi / 72.0
    x0, y0 = page.rect.x0, page.rect.y0
    # cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0) rotates COUNTER-clockwise
    # for a positive angle, about the image centre.
    theta = math.radians(skew_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    cx, cy = width / 2.0, height / 2.0

    def transform(x_pt: float, y_pt: float) -> tuple[float, float]:
        x = (x_pt - x0) * zoom
        y = (y_pt - y0) * zoom
        dx, dy = x - cx, y - cy
        return (cx + cos_t * dx + sin_t * dy,
                cy - sin_t * dx + cos_t * dy)

    return transform


def has_text_layer(pdf_path: str | Path, page_index: int, min_chars: int = 40) -> bool:
    """Whether this page carries enough extractable text to be worth reading."""
    doc = fitz.open(Path(pdf_path))
    try:
        if page_index < 0 or page_index >= doc.page_count:
            return False
        return len(doc[page_index].get_text().strip()) >= min_chars
    finally:
        doc.close()


def _margin_spans(pdf_path: Path, page_index: int, dpi: int, skew_deg: float,
                  width: int, height: int, x_limit: float):
    """Text spans left of `x_limit`, in deskewed page pixels."""
    doc = fitz.open(pdf_path)
    try:
        if page_index < 0 or page_index >= doc.page_count:
            return []
        page = doc[page_index]
        to_px = _pdf_to_pixel_transform(page, dpi, skew_deg, width, height)
        spans = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if len(text) < MIN_LABEL_CHARS:
                        continue
                    bx0, by0, bx1, by1 = span["bbox"]
                    px0, py0 = to_px(bx0, by0)
                    px1, py1 = to_px(bx1, by1)
                    if max(px0, px1) > x_limit:
                        continue
                    spans.append((text, (py0 + py1) / 2.0, min(px0, px1)))
        return spans
    finally:
        doc.close()


def _reading_order(items: list[tuple[float, float, str]], staff_span: float) -> list[str]:
    """Sort spans into reading order: lines top-to-bottom, spans left-to-right
    within a line.

    Sorting on raw `(y, x)` is wrong — OCR gives two spans of the SAME printed
    line slightly different y, so "Timp." came back as "p. Tim". Spans within
    a band of the staff height count as one line.
    """
    if not items:
        return []
    tol = max(4.0, staff_span * 0.5)
    lines: list[list[tuple[float, float, str]]] = []
    for item in sorted(items, key=lambda t: t[0]):
        if lines and abs(item[0] - lines[-1][0][0]) <= tol:
            lines[-1].append(item)
        else:
            lines.append([item])
    ordered: list[str] = []
    for line in lines:
        ordered.extend(t[2] for t in sorted(line, key=lambda t: t[1]))
    return ordered


def read_staff_labels(pws: PageWithStaves, *, dpi: int | None = None) -> list[StaffLabel]:
    """Instrument labels for the staves of `pws`, read from the PDF text layer.

    Returns one `StaffLabel` per staff that claimed at least one text span —
    staves with no label (strings are routinely unlabelled below the first
    system) are simply absent. Returns `[]` when the page has no text layer.
    """
    staves: list[Staff] = sorted(pws.staves, key=lambda s: s.top_y)
    if not staves:
        return []
    page_img = pws.page
    dpi = dpi if dpi is not None else page_img.dpi

    x_limit = min(s.x_start for s in staves) + LABEL_RIGHT_MARGIN_PX
    spans = _margin_spans(
        Path(page_img.pdf_path), page_img.page_index, dpi,
        page_img.skew_correction_deg, page_img.width, page_img.height, x_limit,
    )
    if not spans:
        return []

    centers = [(s.top_y + s.bottom_y) / 2.0 for s in staves]
    if len(centers) > 1:
        pitch = min(b - a for a, b in zip(centers, centers[1:]))
    else:
        pitch = float(staves[0].span_px * 3)
    tolerance = pitch * MAX_STAFF_DISTANCE_FRAC

    claimed: dict[int, list[tuple[float, float, str]]] = {}
    for text, y, x in spans:
        best = min(range(len(staves)), key=lambda i: abs(centers[i] - y))
        inside = staves[best].top_y <= y <= staves[best].bottom_y
        if not inside and abs(centers[best] - y) > tolerance:
            continue
        claimed.setdefault(best, []).append((y, x, text))

    out: list[StaffLabel] = []
    for idx, items in sorted(claimed.items()):
        text = " ".join(_reading_order(items, staves[idx].span_px)).strip()
        hit = lookup(text)
        out.append(StaffLabel(
            staff_index=staves[idx].staff_index,
            text=text,
            instrument=hit.instrument if hit else None,
            fifths_offset=hit.fifths_offset if hit else 0,
            y_center_px=centers[idx],
            confidence=hit.confidence if hit else "none",
            alias=hit.alias if hit else "",
        ))
    return out
