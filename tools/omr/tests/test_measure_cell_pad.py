"""A measure cell records the pad it was cut with — its OWN, not the module's.

⚠️ The whole point of this file is the discriminator, so it is worth stating
what it is. `_build_measure_cell` starts from `PAD_ABOVE_STAFF_LINES` /
`PAD_BELOW_STAFF_LINES` and GROWS to `PAD_MAX_STAFF_LINES` on whichever side
the neighbouring staff is further than the ceiling away. On the page drawn
below the staves sit ~5 staff spaces apart, so an interior staff grows on
NEITHER side, while the top staff has no neighbour above and grows there and
only there. That page therefore produces cells whose pad differs BETWEEN THE
TWO SIDES OF THE SAME CELL and between cells of the same page — which a field
populated from the module constant could not reproduce, and which a page of
well-spaced staves (where every side grows to 6) could not detect.

The fixture is synthesized rather than taken from the score library, which is
machine-local and gitignored, so this runs anywhere the pipeline's own
dependencies are installed — same reasoning as test_recut_cells_e2e.py, whose
crowding note this fixture is copied from.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("skimage", reason="pipeline needs scikit-image")
pytest.importorskip("pymupdf", reason="fixture needs PyMuPDF to draw a page")

from tools.omr import measure_extractor as me  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402


DPI = 300
STAFF_TOPS = (200, 254, 308, 362)   # ~5 staff spaces apart — see the module note


def _draw_page(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)

    def staff(y0: float) -> None:
        for i in range(5):
            y = y0 + i * 6
            page.draw_line(pymupdf.Point(60, y), pymupdf.Point(550, y), width=0.6)
        for bx in (60, 220, 380, 550):
            page.draw_line(pymupdf.Point(bx, y0), pymupdf.Point(bx, y0 + 24), width=0.9)
        for nx in (120, 180, 280, 340, 440):
            page.draw_circle(pymupdf.Point(nx, y0 + 12), 2.6, fill=(0, 0, 0))

    for y in STAFF_TOPS:
        staff(y)
    doc.save(str(path))
    doc.close()


@pytest.fixture(scope="module")
def page_pdf(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("padsynth") / "page.pdf"
    _draw_page(p)
    return p


def _cut(pdf: Path):
    """Phase 1 on the page, returning (pws, cells)."""
    img = render_page(pdf, 0, dpi=DPI)
    pws = detect_staves(img)
    pws = me.detect_barlines(pws)
    cells = me.extract_measures(pws)
    assert cells, "fixture produced no cells — the page is not being read"
    return pws, cells


def _by_staff(cells) -> dict[int, list]:
    out: dict[int, list] = {}
    for c in cells:
        out.setdefault(c.staff_index, []).append(c)
    return out


def test_the_fixture_crowds_its_staves(page_pdf):
    """The discriminator only exists if growth fires on some sides and not
    others. Assert that before asserting anything about the field, so a
    fixture that drifts apart fails HERE rather than making the real tests
    pass vacuously."""
    pws, _ = _cut(page_pdf)
    assert len(pws.staves) >= 3, f"want several staves, got {len(pws.staves)}"
    top = pws.staves[0]
    spacing = max(1.0, top.line_spacing_px)
    ceiling = me.PAD_MAX_STAFF_LINES * spacing
    clearance = me.CELL_NEIGHBOUR_CLEARANCE_SPACES * spacing
    room_above, room_below = me._neighbour_room(pws, top)
    assert room_above - clearance >= ceiling, "top staff should have room above"
    assert room_below - clearance < ceiling, (
        f"staves are too far apart ({room_below / spacing:.1f} spaces) — both "
        "sides would grow to the ceiling and the module-constant bug would be "
        "invisible"
    )


def test_the_pad_differs_between_the_two_sides_of_one_cell(page_pdf):
    """The top staff has open paper above and a crowded neighbour below.

    ⚠️ THIS IS THE ANTI-VACUITY TEST. A field populated from
    `PAD_ABOVE_STAFF_LINES` would report 4.0 above, where the cut actually
    took PAD_MAX_STAFF_LINES.
    """
    _, cells = _cut(page_pdf)
    top = _by_staff(cells)[0]
    assert top, "no cells on the top staff"
    for c in top:
        assert c.pad_above_staff_lines == float(me.PAD_MAX_STAFF_LINES), (
            f"top staff cut at {c.pad_above_staff_lines} above, want the grown "
            f"{float(me.PAD_MAX_STAFF_LINES)} — this is the module-constant bug"
        )
        assert c.pad_below_staff_lines == float(me.PAD_BELOW_STAFF_LINES)
        assert c.pad_above_staff_lines != c.pad_below_staff_lines


def test_an_interior_cell_grows_on_neither_side(page_pdf):
    """A staff crowded above AND below keeps the default on both sides — so
    the two tests together pin both branches of `grown()`."""
    _, cells = _cut(page_pdf)
    by_staff = _by_staff(cells)
    interior = sorted(by_staff)[1:-1]
    assert interior, "fixture should have an interior staff"
    for idx in interior:
        for c in by_staff[idx]:
            assert c.pad_above_staff_lines == float(me.PAD_ABOVE_STAFF_LINES)
            assert c.pad_below_staff_lines == float(me.PAD_BELOW_STAFF_LINES)


def test_the_recorded_pad_is_the_crop_that_was_actually_taken(page_pdf):
    """Spaces × spacing (truncated) is the distance from the staff's own top
    line to the cell's top edge. Without this the field could be an
    independently-computed number that merely looks right."""
    pws, cells = _cut(page_pdf)
    staves = {s.staff_index: s for s in pws.staves}
    checked = 0
    for c in cells:
        staff = staves[c.staff_index]
        spacing = max(1.0, staff.line_spacing_px)
        x0, y0, x1, y1 = c.bbox_page_px
        if y0 == 0 or y1 == pws.page.rgb.shape[0]:
            continue        # clamped to the paper edge — see MeasureCell
        assert staff.top_y - y0 == int(c.pad_above_staff_lines * spacing)
        assert y1 - staff.bottom_y == int(c.pad_below_staff_lines * spacing)
        checked += 1
    assert checked, "every cell was edge-clamped — this test proved nothing"


def test_the_labeling_cutters_pad_is_recorded_as_its_own_value(page_pdf):
    """`annotate/select_cells_orchestral` monkey-patches the module constants
    to 5.0 and does NOT patch the ceiling. So under that mode the interior
    staves must record 5.0 and the top staff must still record 6.0 above —
    which is the fact `recut_cells` currently derives by re-cutting.

    ⚠️ Reads `recut_cells.padding_mode` as the definition of the labeling
    mode rather than restating 5.0 here, so the two cannot drift apart.
    """
    from tools.omr.annotate import recut_cells as rc

    with rc.padding_mode("orchestral"):
        _, cells = _cut(page_pdf)
        want = float(rc.ORCH_PAD_STAFF_LINES)
        by_staff = _by_staff(cells)
        for c in by_staff[0]:
            assert c.pad_above_staff_lines == float(me.PAD_MAX_STAFF_LINES)
            assert c.pad_below_staff_lines == want
        for idx in sorted(by_staff)[1:-1]:
            for c in by_staff[idx]:
                assert c.pad_above_staff_lines == want
                assert c.pad_below_staff_lines == want

    # And the patch is undone, so a later test in the same process is not
    # silently measuring the labeling mode.
    assert me.PAD_ABOVE_STAFF_LINES == 4
