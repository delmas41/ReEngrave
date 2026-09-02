"""Ink the cell crop cut in half is not a notehead.

A measure cell is the staff plus four staff spaces of air, and on a conductor's
page that air holds whatever the neighbouring staff printed. The crop slices it,
and a wide flat sliver is exactly the shape of a hollow notehead — which is how
the engraved Brahms 1 benchmark page, whose truth contains no whole note at all,
came to report seven `noteheadWholeInSpace`. Reading the pixels back: two are
the bowl of the "g" in the word "legato", one is the lower bowl of the "8" of a
6/8 above, and four are noteheads belonging to the staff above or below.

The discriminator is the one dimension a notehead cannot vary in: it is a staff
space tall. See `transcribe._drop_clipped_notehead_fragments`.
"""
from __future__ import annotations

import numpy as np

from tools.omr.transcribe import _drop_clipped_notehead_fragments
from tools.omr.types import MeasureCell

#: Canonical staff spacing used throughout: five lines 24px apart.
SPACING = 24
CELL_H = 400


def _cell(line_ys=None):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=np.zeros((CELL_H, 800, 3), np.uint8), image_no_staff=None,
        bbox_page_px=(0, 0, 800, CELL_H),
        staff_line_ys_canonical=(
            [150, 174, 198, 222, 246] if line_ys is None else line_ys
        ),
        upscale_factor=1.0,
    )


class _Det:
    def __init__(self, category, y, height, x=100, width=26):
        self.category = category
        self.smufl_name = "noteheadWholeInSpace"
        self.x_canonical = x
        self.y_canonical = y
        self.width_canonical = width
        self.height_canonical = height


def _drop(dets, cell=None):
    kept, n = _drop_clipped_notehead_fragments(dets, cell or _cell())
    return kept, n


def test_sliver_at_the_top_edge_is_dropped():
    # The measured fragments run 0.29-0.56 spaces; 0.3 spaces at the very first
    # row of the crop is the Brahms "legato" case.
    kept, n = _drop([_Det("notehead", y=0, height=int(0.3 * SPACING))])
    assert (kept, n) == ([], 1)


def test_sliver_at_the_bottom_edge_is_dropped():
    h = int(0.3 * SPACING)
    kept, n = _drop([_Det("notehead", y=CELL_H - h, height=h)])
    assert (kept, n) == ([], 1)


def test_a_notehead_the_crop_only_grazes_is_kept():
    # Flute 1's F6 and Violin 1's F6 touch the edge at 0.93-0.99 spaces: a note
    # the crop barely reaches is still all there, and is a real note.
    det = _Det("notehead", y=0, height=int(0.95 * SPACING))
    assert _drop([det]) == ([det], 0)


def test_a_short_notehead_in_the_interior_is_kept():
    # The rule is about the crop boundary. A short notehead in the middle of a
    # cell is some other problem and this must not have an opinion on it.
    det = _Det("notehead", y=CELL_H // 2, height=int(0.3 * SPACING))
    assert _drop([det]) == ([det], 0)


def test_other_categories_at_the_edge_are_kept():
    # Slurs, ties and clefs touch cell edges constantly and are not measured
    # against a notehead's height.
    det = _Det("slur", y=0, height=int(0.3 * SPACING))
    assert _drop([det]) == ([det], 0)


def test_abstains_without_staff_geometry():
    # No lines means no staff space to measure against — return everything
    # rather than guess a scale.
    det = _Det("notehead", y=0, height=2)
    assert _drop([det], cell=_cell(line_ys=[])) == ([det], 0)


def test_threshold_is_relative_to_the_cell_s_own_spacing():
    # A cell scaled by width rather than by staff span has a smaller staff, and
    # the same pixel height then IS a notehead. Half-spacing lines: 12px apart.
    tight = _cell(line_ys=[150, 162, 174, 186, 198])
    det = _Det("notehead", y=0, height=11)  # 0.92 spaces here, 0.46 canonically
    assert _drop([det], cell=tight) == ([det], 0)
