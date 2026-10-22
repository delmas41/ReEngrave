"""What the erasure destroys, measured before it happens.

`staff_line_removal` erases along five ideal horizontal rows. The printed
staff is not five ideal rows — the lines carry width, and they wander. Where
the print disagrees with the model the removal misses, and the pipeline had no
way to tell the two cases apart, because `line_ys` looks identical either way.

`measure_staff_line` / `measure_line_geometry` are that missing measurement.
These tests pin down what they must get right: the thickness of a line that
IS thick, the straightness of a line that is straight, and — the part that
took two attempts — not confusing the music sitting on a line for the line
moving.

Synthetic throughout, so thicknesses can be known exactly rather than argued
about. The repo's own PDFs are all modern engravings at roughly 0.10 staff
spaces; the thick-line case these functions exist for is covered here rather
than measured on a real scan.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.header_ink import measure_staff_line
from tools.omr.staff_detector import measure_line_geometry
from tools.omr.types import Staff


WIDTH = 1200
HEIGHT = 400
SPACING = 40.0


def _line(mask: np.ndarray, y: float, thickness: int, x0: int = 0, x1: int = WIDTH) -> None:
    """Draw one horizontal line `thickness` px tall, centred on `y`."""
    top = int(round(y - (thickness - 1) / 2.0))
    mask[top:top + thickness, x0:x1] = 255


def _blank(h: int = HEIGHT, w: int = WIDTH) -> np.ndarray:
    return np.zeros((h, w), np.uint8)


class TestThickness:
    """A line's thickness is how much ink removal has to take."""

    @pytest.mark.parametrize("thickness", [2, 3, 5, 8, 12])
    def test_reads_the_thickness_it_was_drawn_with(self, thickness):
        mask = _blank()
        _line(mask, 200, thickness)
        measured, _ = measure_staff_line(mask, 200.0, SPACING)
        assert measured == pytest.approx(thickness, abs=1.0)

    def test_thick_line_is_not_mistaken_for_a_thin_one(self):
        # The case this exists for: 0.30 staff spaces vs 0.08. A removal band
        # sized for the thin line leaves most of the thick one behind.
        mask_thin = _blank(); _line(mask_thin, 200, 3)
        mask_thick = _blank(); _line(mask_thick, 200, 12)
        t_thin, _ = measure_staff_line(mask_thin, 200.0, SPACING)
        t_thick, _ = measure_staff_line(mask_thick, 200.0, SPACING)
        assert t_thin / SPACING == pytest.approx(0.075, abs=0.03)
        assert t_thick / SPACING == pytest.approx(0.300, abs=0.03)
        assert t_thick > t_thin * 3


class TestWander:
    """How far the line departs from the single row it is modelled as."""

    def test_a_straight_line_reports_no_wander(self):
        mask = _blank()
        _line(mask, 200, 4)
        _, wander = measure_staff_line(mask, 200.0, SPACING)
        assert wander <= 1.0

    @pytest.mark.parametrize("bow", [3, 6, 10])
    def test_a_bowed_line_reports_its_bow(self, bow):
        # A line that genuinely bends bends across many columns, so the
        # quantile sees it — that is what separates real wander from an
        # isolated artifact.
        mask = _blank()
        xs = np.arange(WIDTH)
        centre = 200 + bow * np.sin(np.pi * xs / WIDTH)
        for x in xs:
            _line(mask, centre[x], 4, x, x + 1)
        _, wander = measure_staff_line(mask, 200.0, SPACING)
        assert wander == pytest.approx(bow, abs=1.5)

    def test_notes_on_the_line_are_not_read_as_the_line_moving(self):
        # The bug this test exists for. `_run_extent` clips a tall glyph run at
        # the search window, so some arrive at a plausible-looking height while
        # their centre is nowhere near the line. Taking a MAXIMUM over the
        # columns of a staff is then guaranteed to find one: on a real page
        # straight to within half a pixel it reported 13.5 px of wander.
        clean = _blank()
        _line(clean, 200, 4)
        _, wander_clean = measure_staff_line(clean, 200.0, SPACING)

        noisy = clean.copy()
        for cx in range(120, WIDTH, 150):          # noteheads sitting on the line
            noisy[186:214, cx:cx + 46] = 255
        for cx in range(60, WIDTH, 150):           # stems crossing it
            noisy[150:250, cx:cx + 6] = 255
        thickness, wander_noisy = measure_staff_line(noisy, 200.0, SPACING)

        assert wander_noisy == pytest.approx(wander_clean, abs=1.0)
        assert thickness == pytest.approx(4, abs=1.0)  # thickness survives too


class TestAbstention:
    def test_blank_image_is_not_traced(self):
        assert measure_staff_line(_blank(), 200.0, SPACING) is None

    def test_too_few_ink_columns_is_not_traced(self):
        mask = _blank()
        _line(mask, 200, 4, 0, WIDTH // 40)   # a stub, well under the 10% floor
        assert measure_staff_line(mask, 200.0, SPACING) is None


class TestMeasureLineGeometry:
    """The page-level entry point Phase 1 calls, on Phase 1's polarity
    (binary is 0=ink, 255=paper — the inverse of the masks above)."""

    @staticmethod
    def _page(thickness: int = 5, wander: float = 0.0):
        ys = [100, 140, 180, 220, 260]
        mask = _blank(HEIGHT, WIDTH)
        xs = np.arange(WIDTH)
        for y in ys:
            centre = y + wander * np.sin(np.pi * xs / WIDTH)
            for x in xs:
                _line(mask, centre[x], thickness, x, x + 1)
        binary = np.where(mask > 0, 0, 255).astype(np.uint8)   # Phase 1 polarity
        return binary, ys

    def test_measures_every_line(self):
        binary, ys = self._page(thickness=6)
        thicknesses, wander = measure_line_geometry(binary, ys, 0, WIDTH - 1)
        assert len(thicknesses) == 5
        assert all(t == pytest.approx(6, abs=1.0) for t in thicknesses)
        assert wander <= 1.0

    def test_reports_the_worst_line_wander(self):
        binary, ys = self._page(thickness=4, wander=5.0)
        _, wander = measure_line_geometry(binary, ys, 0, WIDTH - 1)
        assert wander == pytest.approx(5.0, abs=1.5)

    def test_blank_page_abstains(self):
        binary = np.full((HEIGHT, WIDTH), 255, np.uint8)
        assert measure_line_geometry(binary, [100, 140, 180, 220, 260], 0, WIDTH - 1) is None

    def test_degenerate_extent_abstains(self):
        binary, ys = self._page()
        assert measure_line_geometry(binary, ys, 500, 400) is None
        assert measure_line_geometry(binary, [100], 0, WIDTH - 1) is None

    def test_partial_read_abstains_rather_than_reporting_four_lines(self):
        # All five or nothing: a thicknesses list shorter than the staff would
        # be silently mis-indexed by anything zipping it against line_ys.
        binary, ys = self._page()
        binary[218:224, :] = 255      # erase the fourth line entirely
        assert measure_line_geometry(binary, ys, 0, WIDTH - 1) is None


class TestStaffProperty:
    def test_median_thickness(self):
        st = Staff(page_index=0, staff_index=0, line_ys=[100, 140, 180, 220, 260],
                   x_start=0, x_end=999, line_thickness_px=[4.0, 5.0, 4.0, 6.0, 5.0])
        assert st.median_line_thickness_px == 5.0

    def test_none_when_never_traced(self):
        st = Staff(page_index=0, staff_index=0, line_ys=[100, 140, 180, 220, 260],
                   x_start=0, x_end=999)
        assert st.line_thickness_px is None
        assert st.line_wander_px is None
        assert st.median_line_thickness_px is None
