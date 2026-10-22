"""OMR pipeline — Phase 1 (image foundation).

See plans/i-have-tried-several-unified-sphinx.md for the design.

Pipeline:
    PDF → render_page() → PageImage
    PageImage → detect_staves() → PageWithStaves
    PageWithStaves → extract_measures() → list[MeasureCell]
"""

from .types import PageImage, Staff, Barline, PageWithStaves, MeasureCell

__all__ = ["PageImage", "Staff", "Barline", "PageWithStaves", "MeasureCell"]
