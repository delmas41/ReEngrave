"""Symbol library — SMuFL glyphs rasterized from Bravura.otf for template
matching against connected components in MeasureCell.image_no_staff.

Public API:

    from tools.omr.symbol_library import SymbolLibrary
    lib = SymbolLibrary.load()
    matches = lib.match(component_image)
"""

from .loader import SymbolLibrary, LibraryEntry, Match

__all__ = ["SymbolLibrary", "LibraryEntry", "Match"]
