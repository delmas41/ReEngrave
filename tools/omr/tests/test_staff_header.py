"""Unit tests for the header-window measurement
(`tools/omr/staff_header.py`).

The case that matters is a staff whose printed lines are BROKEN. That is what
pushes `Staff.x_start` past the clef on real 19th-century prints, and it is why
reading the header out of the staff-start measure cell loses it entirely.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tools.omr.staff_header import (
    HEADER_MEASURE_INDEX,
    HeaderWindowConfig,
    extract_header_cell,
    header_cells_for_page,
    measure_header_window,
    system_left_edge,
)
from tools.omr.types import Barline, PageImage, PageWithStaves, Staff

SPACING = 20
PAGE_W, PAGE_H = 900, 600
STAFF_LEFT = 100          # where the staff lines really begin
BRACKET_X = 92            # the system's initial vertical rule, just left of it
BARLINE_X = 400


def _staff_lines(top: int) -> list[int]:
    return [top + i * SPACING for i in range(5)]


def _page(
    staff_tops: list[int],
    *,
    breaks: dict[int, list[tuple[int, int]]] | None = None,
    instrument_text: bool = True,
) -> np.ndarray:
    """A page with staves, a bracket, a barline, and optional gaps in the lines.

    `breaks` maps a staff's index to x-ranges to erase from its lines, which is
    how a faded or heavily-inked print actually behaves.
    """
    img = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
    for idx, top in enumerate(staff_tops):
        lines = _staff_lines(top)
        for y in lines:
            cv2.line(img, (STAFF_LEFT, y), (PAGE_W - 60, y), 0, 2)
        for x0, x1 in (breaks or {}).get(idx, []):
            img[top - 2 : top + 4 * SPACING + 3, x0:x1] = 255
        # The bracket / initial rule, spanning this staff.
        cv2.rectangle(img, (BRACKET_X, lines[0]), (BRACKET_X + 3, lines[-1]), 0, -1)
        cv2.rectangle(img, (BARLINE_X, lines[0]), (BARLINE_X + 3, lines[-1]), 0, -1)
        if instrument_text:
            # "Fl." printed clear of the staff — the thing a too-generous walk
            # would wrongly swallow.
            cv2.putText(img, "Fl.", (30, lines[2] + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    return img


def _pws(img: np.ndarray, staff_tops: list[int], x_starts: list[int]) -> PageWithStaves:
    page = PageImage(
        pdf_path=None, page_index=0, dpi=300,
        rgb=cv2.cvtColor(img, cv2.COLOR_GRAY2RGB), binary=img,
    )
    staves = [
        Staff(page_index=0, staff_index=i, line_ys=_staff_lines(top),
              x_start=x_starts[i], x_end=PAGE_W - 60, system_index=0)
        for i, top in enumerate(staff_tops)
    ]
    barlines = [
        Barline(page_index=0, x=BARLINE_X, y_top=staves[0].top_y,
                y_bottom=staves[-1].bottom_y, system_index=0)
    ]
    return PageWithStaves(page=page, staves=staves, barlines=barlines)


# ─── the left edge ──────────────────────────────────────────────────────────

class TestSystemLeftEdge:
    def test_clean_staff(self):
        tops = [100, 250]
        pws = _pws(_page(tops), tops, [STAFF_LEFT, STAFF_LEFT])
        assert system_left_edge(pws, 0) == pytest.approx(STAFF_LEFT, abs=SPACING // 2)

    def test_broken_lines_do_not_push_the_edge_right(self):
        # THE regression: staff 0's lines are broken just past the header, so
        # its own x_start lands deep in the music. The system's other staff is
        # sound, and the minimum rule is what rescues staff 0.
        tops = [100, 250]
        img = _page(tops, breaks={0: [(150, 210), (260, 300)]})
        pws = _pws(img, tops, [310, STAFF_LEFT])   # x_start for staff 0 is past the header
        assert system_left_edge(pws, 0) == pytest.approx(STAFF_LEFT, abs=SPACING // 2)

    def test_walk_stops_at_the_bracket_not_the_instrument_name(self):
        # Erring a little left is safe; reaching the text is not, because the
        # text would then become the header's left edge.
        tops = [100]
        pws = _pws(_page(tops), tops, [STAFF_LEFT])
        assert system_left_edge(pws, 0) >= BRACKET_X - 1

    def test_blank_page_abstains(self):
        tops = [100]
        img = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        pws = _pws(img, tops, [STAFF_LEFT])
        assert system_left_edge(pws, 0) is None


# ─── the window ─────────────────────────────────────────────────────────────

class TestHeaderWindow:
    def test_right_edge_is_the_first_barline(self):
        tops = [100]
        pws = _pws(_page(tops), tops, [STAFF_LEFT])
        window = measure_header_window(pws, pws.staves[0])
        assert window.right_from == "barline"
        assert window.x1 == BARLINE_X

    def test_window_covers_the_header_even_when_x_start_does_not(self):
        tops = [100, 250]
        img = _page(tops, breaks={0: [(150, 210)]})
        pws = _pws(img, tops, [310, STAFF_LEFT])
        window = measure_header_window(pws, pws.staves[0])
        # The clef would sit within a few spaces of the staff's left edge; the
        # window has to start at or before it, not at x_start.
        assert window.x0 <= STAFF_LEFT
        assert window.x0 < 310

    def test_width_cap_applies_when_no_barline_is_near(self):
        tops = [100]
        img = _page(tops)
        pws = _pws(img, tops, [STAFF_LEFT])
        pws.barlines.clear()
        window = measure_header_window(pws, pws.staves[0], HeaderWindowConfig(max_width_spaces=8.0))
        assert window.right_from == "width_cap"
        assert window.width == pytest.approx(8 * SPACING, abs=2)

    def test_a_barline_too_close_is_the_initial_rule_and_is_skipped(self):
        tops = [100]
        img = _page(tops)
        pws = _pws(img, tops, [STAFF_LEFT])
        pws.barlines.insert(
            0, Barline(page_index=0, x=STAFF_LEFT + 4, y_top=100, y_bottom=180, system_index=0)
        )
        window = measure_header_window(pws, pws.staves[0])
        assert window.x1 == BARLINE_X


# ─── cells ──────────────────────────────────────────────────────────────────

class TestHeaderCells:
    def test_cell_is_marked_as_not_a_measure(self):
        tops = [100]
        pws = _pws(_page(tops), tops, [STAFF_LEFT])
        cell = extract_header_cell(pws, pws.staves[0])
        assert cell.measure_index == HEADER_MEASURE_INDEX
        assert cell.measure_index < 0

    def test_cell_carries_canonical_staff_lines_and_a_no_staff_variant(self):
        tops = [100]
        pws = _pws(_page(tops), tops, [STAFF_LEFT])
        cell = extract_header_cell(pws, pws.staves[0])
        assert len(cell.staff_line_ys_canonical) == 5
        assert cell.image_no_staff is not None

    def test_one_cell_per_staff(self):
        tops = [100, 250, 400]
        pws = _pws(_page(tops), tops, [STAFF_LEFT] * 3)
        cells = header_cells_for_page(pws)
        assert sorted(cells) == [0, 1, 2]

    def test_staves_share_one_measured_edge(self):
        # Every staff in a system gets the same left edge, so a staff whose own
        # lines are broken is carried by its neighbours.
        tops = [100, 250]
        img = _page(tops, breaks={0: [(150, 240)]})
        pws = _pws(img, tops, [320, STAFF_LEFT])
        cells = header_cells_for_page(pws)
        assert cells[0].bbox_page_px[0] == cells[1].bbox_page_px[0]
