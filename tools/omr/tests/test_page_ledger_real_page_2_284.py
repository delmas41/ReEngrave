"""ROADMAP 2.284 -- the cell -> page stroke link on a REAL page (Brahms p0, the master cell map). Slow: it reads the library PDF and cuts the cells.

The control that can fail: the same link with every cell's page rectangle shifted by two staff spaces must lose most of its links."""
from __future__ import annotations

import pathlib

import pytest

pytestmark = pytest.mark.slow

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"


def _linked_share(shift_px: float = 0.0):
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import gather as G
    from tools.omr.staged import page_ledger as PL
    from tools.omr.staged import page_strokes as PS
    from tools.omr.staged import stroke_map as SM
    (pws, cells), = CM.load_prepared(PDF, [0], root=LIB / "_shared-records" / "cell-maps")
    local = G._system_local(pws.staves)
    pm = PS.map_page(pws, cells, local, {})
    labels = PL.PageLabels(pm, pws.page.binary.shape)
    tot = linked = 0
    for c in cells:
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None or local.get(c.staff_index) is None:
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None))
        if not res or not res.strokes:
            continue
        rect = list(c.bbox_page_px)
        rect[1] += shift_px
        for (m, _x, _y), ln in zip(res.masks, PL.link_cell_strokes(res, rect, float(c.upscale_factor), labels)):
            n = int(m.sum())
            tot += n
            if ln is not None and ln[1] >= PL.LINK_SHARE_MIN:
                linked += n
    return linked / float(max(1, tot)), float(pm.sp)


@pytest.mark.skipif(not PDF.exists(), reason="library PDF not on this machine")
def test_most_cell_stroke_ink_links_to_one_page_stroke_and_a_shift_breaks_it():
    share, sp = _linked_share()
    assert share >= 0.8, share
    shifted, _ = _linked_share(shift_px=2.0 * sp)
    assert shifted < 0.5 * share, (share, shifted)
