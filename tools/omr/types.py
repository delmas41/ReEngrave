"""Shared types for the OMR pipeline. Module boundaries pass these around so
each step has a clear input/output contract.

Phase 1 (image foundation):
    PDF path → PageImage[] → PageWithStaves[] → MeasureCell[]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class PageImage:
    """One rendered page from a PDF. Image is a numpy array, dtype uint8.
    `binary` is the Sauvola-binarized image (0=ink, 255=paper)."""

    pdf_path: Path
    page_index: int          # 0-based
    dpi: int
    rgb: np.ndarray          # H×W×3 uint8 — original render
    binary: np.ndarray       # H×W uint8 — binarized (255=paper, 0=ink)
    skew_correction_deg: float = 0.0

    @property
    def height(self) -> int:
        return self.rgb.shape[0]

    @property
    def width(self) -> int:
        return self.rgb.shape[1]


@dataclass
class Staff:
    """One five-line staff on a page, in page-pixel coordinates."""

    page_index: int
    staff_index: int            # 0-based within the page
    line_ys: list[int]          # 5 y-coordinates, top → bottom
    x_start: int                # left edge of staff content (after clef margin)
    x_end: int                  # right edge
    system_index: int = 0       # which system this staff belongs to (group of staves played together)
    group_index: int = 0        # bracket group within the system (winds | brass | strings) — see system_grouping.py
    slot_index: int = -1        # stable part identity across systems/pages, -1 = unassigned — see slots.py

    @property
    def top_y(self) -> int:
        return self.line_ys[0]

    @property
    def bottom_y(self) -> int:
        return self.line_ys[-1]

    @property
    def span_px(self) -> int:
        """Pixel distance from top staff line to bottom staff line."""
        return self.bottom_y - self.top_y

    @property
    def line_spacing_px(self) -> float:
        """Average spacing between adjacent staff lines."""
        if len(self.line_ys) < 2:
            return 0.0
        gaps = [self.line_ys[i + 1] - self.line_ys[i] for i in range(len(self.line_ys) - 1)]
        return sum(gaps) / len(gaps)


@dataclass
class Barline:
    """A vertical line dividing measures on a staff system."""

    page_index: int
    x: int                       # page-pixel x-coordinate
    y_top: int                   # top of barline (usually top staff of system)
    y_bottom: int                # bottom of barline
    system_index: int


@dataclass
class PageWithStaves:
    """A PageImage annotated with detected staves and barlines."""

    page: PageImage
    staves: list[Staff]
    barlines: list[Barline] = field(default_factory=list)

    def staves_in_system(self, system_index: int) -> list[Staff]:
        return [s for s in self.staves if s.system_index == system_index]


@dataclass
class MeasureCell:
    """One (staff × measure) cell extracted from a page, normalized to a
    canonical maximum size for downstream symbol detection.

    The `image` is in CANONICAL coordinates (staff span = ~CANONICAL_STAFF_SPAN_PX),
    not page coordinates. The `bbox` records the original page-pixel location
    so downstream output can be mapped back to the source PDF for visualization.
    """

    page_index: int
    system_index: int
    staff_index: int            # within the page
    measure_index: int          # 0-based within the staff
    image: np.ndarray           # canonical-size cell (BGR or grayscale uint8)
    image_no_staff: np.ndarray | None  # same image with staff lines removed
    bbox_page_px: tuple[int, int, int, int]  # (x0, y0, x1, y1) in original page pixels
    staff_line_ys_canonical: list[int]       # staff line y-coords in CANONICAL image
    upscale_factor: float       # canonical_h / page_h_of_cell

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]
