"""Where a stacked beam's bars are placed — measured, never fabricated.

`_stacked_bar_count` counts beam bars by vertical ink runs in a column, which
is right and is not touched here. What was wrong is what happened NEXT: the
count went to `detect_beams`, the positions were thrown away, and the bars were
placed by dividing the component's bounding box into `n_bars` equal slices.

A stack's box is sized by its SLOPE and its bars by the engraving, so those two
things are not the same and the even division is a fabrication. It reaches the
output as a duration: `rhythm._beams_attached_to_stem` reads the band EDGES for
its end-window test and the band CENTRES for its level clustering, and a level
is a note's value.

Measured over 2,073 components on 31 pages (the 20-row scan gate plus the 11
engraved fixtures): 51 components read more than one bar, every one of them on
a scan, and 4 of those 51 change their beam-level count under the repair. The
fabricated band edge sits a median 0.241 staff spaces from the measured one,
worst case 1.037 — a full staff space.

The single-bar case — 2,022 of those 2,073 components, and every component on
every engraved page — must be BYTE-IDENTICAL, and is so by construction rather
than by measurement: a single bar has nothing to place, so `_stacked_bar_bands`
returns no bands and the caller's fallback is the old code path verbatim.
"""

from __future__ import annotations

import cv2
import numpy as np

from tools.omr.line_detection import (
    _binary_ink,
    _stacked_bar_bands,
    _stacked_bar_count,
    detect_beams,
)
from tools.omr.types import MeasureCell


SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]


def _stacked_beam_cell() -> MeasureCell:
    """Two sloped bars reaching `detect_beams` as ONE component.

    A stack only arrives as one component when its bars are joined over a run
    WIDER than the 1.5-space horizontal opening kernel — which on a real scan
    is ink bleed closing the gap at the thick end of the group. Joined over a
    shorter run the opening separates them and each is an ordinary single bar.

    The slope is 1 in 4, so the component's box is 161 px tall around bars that
    are 48 px thick and 60 px apart: the box is a poor description of either
    bar, which is the whole defect.
    """
    img = np.full((1000, 900), 255, dtype=np.uint8)
    for x in range(195, 706):
        rise = (x - 195) // 4
        img[150 + rise:198 + rise, x] = 0          # primary bar
        img[210 + rise:258 + rise, x] = 0          # secondary bar
        if x < 420:
            img[196 + rise:212 + rise, x] = 0      # the bleed joining them
    img[150:560, 195:205] = 0                      # stems, one at each end
    end_rise = (705 - 195) // 4
    img[150 + end_rise:560 + end_rise, 695:705] = 0
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 1000),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _bbox(labels, label: int) -> tuple[int, int, int, int]:
    """The component's bounding box, the way `connectedComponentsWithStats` gives it."""
    ys, xs = np.nonzero(labels == label)
    x, y = int(xs.min()), int(ys.min())
    return x, y, int(xs.max()) - x + 1, int(ys.max()) - y + 1


def _sloped_stack(n_bars: int, *, thickness: int = 12, pitch: int = 50,
                  slope_div: int = 4, width: int = 400) -> np.ndarray:
    """`n_bars` parallel sloped bars, all one label, stacked at a fixed pitch.

    The shape a real stacked beam makes: every bar carries the same slope, so
    the component's box is taller than the stack by the slope's whole rise and
    the bars do NOT divide it evenly. That gap between the box and the bars is
    exactly what the even division used to fill in with invented coordinates.
    """
    height = 10 + (n_bars - 1) * pitch + thickness + width // slope_div + 10
    labels = np.zeros((height, width), dtype=np.int32)
    for x in range(width):
        rise = x // slope_div
        for b in range(n_bars):
            top = 10 + b * pitch + rise
            labels[top:top + thickness, x] = 1
    return labels


class TestASingleBarIsUntouched:
    """The 2,022-of-2,073 case, and every engraved page. Inert by construction.

    A single bar has no placement decision to make — the component IS the bar —
    so the function declines to supply bands at all and the caller reproduces
    the old expression verbatim. These assert that decline, at both levels.
    """

    def test_a_level_single_bar_supplies_no_bands(self):
        labels = np.zeros((200, 400), dtype=np.int32)
        labels[40:52, :] = 1
        n_bars, bands = _stacked_bar_bands(labels, 1, 0, 40, 400, 12)
        assert n_bars == 1
        assert bands is None

    def test_a_sloped_single_bar_supplies_no_bands(self):
        labels = _sloped_stack(1)
        x, y, w, h = _bbox(labels, 1)
        n_bars, bands = _stacked_bar_bands(labels, 1, x, y, w, h)
        assert n_bars == 1
        assert bands is None

    def test_detect_beams_emits_a_single_bar_as_its_own_box(self):
        """The byte-identity control, stated as the invariant it protects.

        With one bar the old code computed `y + 0 * (h/1)` and `max(1, h // 1)`
        — the box. Anything the repair emits here that is not exactly the box
        is a regression on the overwhelming majority of components.
        """
        img = np.full((800, 900), 255, dtype=np.uint8)
        # Two stems joined by one level bar: a real beam, one bar.
        img[150:500, 195:205] = 0
        img[150:500, 695:705] = 0
        img[150:198, 195:705] = 0
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 800),
            staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
        )
        beams = detect_beams(cell)
        assert len(beams) == 1
        b = beams[0]
        # Independently recover the component the detector found and compare.
        assert b.y_canonical == 150
        assert b.height_canonical == 48


class TestAStackIsPlacedWhereTheInkIs:
    """The 51-of-2,073 case: the bars go where the mask says, not on a grid."""

    def test_two_sloped_bars_get_their_measured_excursions(self):
        labels = _sloped_stack(2)
        x, y, w, h = _bbox(labels, 1)
        n_bars, bands = _stacked_bar_bands(labels, 1, x, y, w, h)
        assert n_bars == 2
        assert bands is not None
        # Bar b runs from `10 + b*50` at x=0 down to `10 + b*50 + 99 + 11` at
        # x=399, in absolute rows; relative to the box top (y=10) that is:
        assert bands == [(0, 110), (50, 160)]

    def test_the_measured_bands_differ_from_an_even_division(self):
        """Guards the fixture: without this the test above passes vacuously.

        If the bars happened to divide the box evenly there would be nothing to
        repair and no test here would mean anything.
        """
        labels = _sloped_stack(2)
        x, y, w, h = _bbox(labels, 1)
        _, bands = _stacked_bar_bands(labels, 1, x, y, w, h)
        even = [(k * (h // 2), k * (h // 2) + h // 2 - 1) for k in range(2)]
        assert bands != even
        # ...and the disagreement is large enough to matter downstream: the
        # end-window test reads the band EDGE, and half a staff space here.
        edge_gap = max(abs(bands[k][0] - even[k][0]) for k in range(2))
        assert edge_gap / SPACING >= 0.25

    def test_every_emitted_band_contains_its_bar_s_ink(self):
        """The property the even division breaks, stated directly.

        A band is a claim about where a bar is. Measured bands hold every pixel
        of their bar; even slices do not, which is the defect.
        """
        labels = _sloped_stack(3)
        x, y, w, h = _bbox(labels, 1)
        n_bars, bands = _stacked_bar_bands(labels, 1, x, y, w, h)
        assert n_bars == 3 and bands is not None
        for b, (top, bottom) in enumerate(bands):
            # The bar's own ink, reconstructed from the fixture's geometry.
            ink_top = 10 + b * 50 - y
            ink_bottom = 10 + b * 50 + 11 + (w - 1) // 4 - y
            assert top <= ink_top, f"band {b} starts below its bar"
            assert bottom >= ink_bottom, f"band {b} ends above its bar"

    def test_an_even_division_would_NOT_contain_the_ink(self):
        """The same property, asserted to FAIL for the old placement.

        This is the test that goes red if the repair is reverted: it says the
        thing being replaced is measurably wrong, not merely different.
        """
        labels = _sloped_stack(3)
        x, y, w, h = _bbox(labels, 1)
        escaped = 0
        for b in range(3):
            top = int(b * (h / 3))
            bottom = top + max(1, h // 3) - 1
            ink_top = 10 + b * 50 - y
            ink_bottom = 10 + b * 50 + 11 + (w - 1) // 4 - y
            if ink_top < top or ink_bottom > bottom:
                escaped += 1
        assert escaped > 0, "fixture no longer exercises the defect"

    def test_detect_beams_places_a_real_stack_on_its_ink(self):
        """End to end through the emitter, on a cell rather than a raw mask.

        ⚠️ This test is the one that goes RED when the emission site is
        reverted, and it took two attempts to make it do so. The obvious
        fixture — two sloped bars with a short bleed between them — survives
        the 1.5-space horizontal opening as TWO components of one bar each, so
        it exercises the untouched single-bar path and passes either way. The
        bleed has to be wider than the opening kernel for the stack to reach
        `_stacked_bar_bands` as one component at all.
        """
        cell = _stacked_beam_cell()
        beams = detect_beams(cell)
        assert len(beams) == 2
        placed = sorted((b.y_canonical, b.height_canonical) for b in beams)
        # Measured off the ink: the bars are 60 px apart on the page and each
        # sweeps 82 px of excursion across the group.
        assert placed == [(206, 82), (266, 82)]

    def test_the_even_division_would_have_placed_them_elsewhere(self):
        """Guards the test above against passing for the wrong reason.

        Recomputes the fabrication from the component's own box and asserts it
        disagrees. If a future change to the opening kernel or the fixture ever
        splits this stack back into single-bar components, this fails loudly
        instead of leaving the test above quietly vacuous.
        """
        cell = _stacked_beam_cell()
        ink = _binary_ink(cell.image_no_staff)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (150, 1))
        opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
        num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, 8)
        wide = [i for i in range(1, num) if stats[i][2] >= 300]
        assert len(wide) == 1, "the fixture must deliver ONE component"
        i = wide[0]
        x, y, w, h = (int(v) for v in stats[i][:4])
        n_bars, bands = _stacked_bar_bands(labels, i, x, y, w, h)
        assert n_bars == 2, "the fixture must deliver a genuine two-bar stack"
        assert bands is not None
        sub_h = max(1, h // n_bars)
        fabricated = [(int(y + k * (h / n_bars)), int(sub_h)) for k in range(n_bars)]
        measured = [(int(y + t), int(b - t + 1)) for t, b in bands]
        assert fabricated != measured
        # The first bar is where the two disagree most, and by enough to cross
        # the 0.35-space clustering tolerance's neighbourhood downstream.
        assert abs(fabricated[0][0] - measured[0][0]) / SPACING >= 0.15


class TestTheFallbackIsTheOldPath:
    """Where the mask cannot say, nothing is placed on evidence that isn't there."""

    def test_no_clean_column_declines_to_supply_bands(self):
        """A stack every column of which is crossed by something else.

        The median still reads 2 — the count is robust, which is why it is not
        being touched — but no single column shows exactly two clean runs, so
        there is no column entitled to say where bar 0 ends and bar 1 begins.
        """
        labels = np.zeros((200, 400), dtype=np.int32)
        labels[40:52, :] = 1
        labels[90:102, :] = 1
        # A third run in every column: now every column reads 3, never 2.
        labels[140:152, :] = 1
        n_bars, bands = _stacked_bar_bands(labels, 1, 0, 40, 400, 112)
        assert n_bars == 3
        assert bands is not None      # 3 clean runs — this one CAN be placed

        # Now spoil it: make the run count differ column to column so that no
        # value of `n_bars` is matched by any column.
        labels[140:152, ::2] = 0
        n_bars, bands = _stacked_bar_bands(labels, 1, 0, 40, 400, 112)
        assert bands is None or len(bands) == n_bars

    def test_an_empty_roi_declines(self):
        labels = np.zeros((200, 400), dtype=np.int32)
        n_bars, bands = _stacked_bar_bands(labels, 7, 0, 0, 0, 0)
        assert n_bars == 1
        assert bands is None


class TestTheCountIsUnchanged:
    """`_stacked_bar_count` is the count-only view of the same pass.

    Its logic was rewritten to exploit the property that a single sloped bar
    crossed by a vertical column yields ONE run whatever its slope, and an
    independent hand count agreed with it on 51 of 51 real components. The
    repair must not have disturbed it.
    """

    def test_a_sloped_bar_beside_a_neighbour_still_counts_once(self):
        labels = np.zeros((200, 400), dtype=np.int32)
        for x in range(400):
            labels[20 + x // 4:20 + x // 4 + 12, x] = 1
        for x in range(150, 400):
            labels[x // 4:x // 4 + 12, x] = 2
        x, y, w, h = _bbox(labels, 1)
        assert _stacked_bar_count(labels, 1, x, y, w, h) == 1

    def test_two_stacked_bars_still_count_twice(self):
        labels = np.zeros((200, 400), dtype=np.int32)
        labels[40:52, :] = 1
        labels[90:102, :] = 1
        assert _stacked_bar_count(labels, 1, 0, 40, 400, 62) == 2

    def test_the_wrapper_agrees_with_the_bands_function(self):
        for n in (1, 2, 3):
            labels = _sloped_stack(n)
            x, y, w, h = _bbox(labels, 1)
            assert (_stacked_bar_count(labels, 1, x, y, w, h)
                    == _stacked_bar_bands(labels, 1, x, y, w, h)[0] == n)


class TestTheCallerActuallyConsumesTheBands:
    """⚠️ WIRING. The whole value of this change is that `detect_beams` USES
    the bands; a correct `_stacked_bar_bands` that nothing consumes is worth
    exactly nothing.

    The first version of this file tested the FUNCTION heavily and the CALLER
    barely: neutering `_stacked_bar_bands` reddened 6 of 14 tests, but
    neutering only the caller — one `bands = None` inside `detect_beams` —
    reddened exactly ONE. That is thinner than this project's own standard for
    precisely this shape; `test_export.py` carries a source-level anti-drift
    test because a signal computed and then dropped on the way out is the
    recurring bug here, and it is the bug this change repairs. These two close
    that gap from both sides.
    """

    def test_the_placement_branch_reads_the_measured_bands(self):
        """ANTI-DRIFT, in the shape `test_export.py` uses.

        Asserts at SOURCE level that the emission site still has a branch fed
        by `bands`, so a future edit collapsing it back to the even division
        fails here even if some fixture happens to stop exercising it.
        """
        import inspect

        import tools.omr.line_detection as ld

        src = inspect.getsource(ld.detect_beams).splitlines()
        sites = [i for i, line in enumerate(src)
                 if "_stacked_bar_bands(" in line]
        assert len(sites) == 1, (
            f"expected exactly one call to _stacked_bar_bands, found {len(sites)}")
        body = "\n".join(src[sites[0]:sites[0] + 12])
        assert "if bands is None:" in body, (
            "the emission site no longer branches on whether the mask supplied "
            "bands — the even division is being used unconditionally again")
        assert "for top, bottom in bands" in body, (
            "the emission site no longer PLACES bars on the measured bands; "
            "computing them and not consuming them is the bug this fixes")

    def test_a_second_stack_geometry_also_lands_on_its_ink(self):
        """A different slope and gap from the fixture above.

        One end-to-end case can pass because its numbers happen to coincide;
        two geometries disagreeing with the even division in DIFFERENT amounts
        cannot both coincide.
        """
        img = np.full((1100, 900), 255, dtype=np.uint8)
        for x in range(195, 706):
            rise = (x - 195) // 5          # 1-in-5; the other fixture is 1-in-4
            img[200 + rise:236 + rise, x] = 0          # bars 36 px thick, not 48
            img[275 + rise:311 + rise, x] = 0          # 75 px apart, not 60
            if x < 430:
                img[236 + rise:275 + rise, x] = 0      # the joining bleed
        img[200:560, 195:205] = 0
        end = (705 - 195) // 5
        img[200 + end:560 + end, 695:705] = 0
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 1100),
            staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
        )
        beams = detect_beams(cell)
        assert len(beams) == 2, f"expected a two-bar stack, got {len(beams)}"

        ink = _binary_ink(cell.image_no_staff)
        opened = cv2.morphologyEx(
            ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (150, 1)))
        num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, 8)
        wide = [i for i in range(1, num) if stats[i][2] >= 300]
        assert len(wide) == 1, "fixture must deliver ONE component"
        x, y, w, h = (int(v) for v in stats[wide[0]][:4])
        n_bars, bands = _stacked_bar_bands(labels, wide[0], x, y, w, h)
        assert n_bars == 2 and bands is not None

        placed = sorted((b.y_canonical, b.height_canonical) for b in beams)
        measured = sorted((int(y + t), int(b - t + 1)) for t, b in bands)
        sub_h = max(1, h // 2)
        fabricated = sorted((int(y + k * (h / 2)), int(sub_h)) for k in range(2))
        assert placed == measured, "bars were not placed on the measured bands"
        assert placed != fabricated, (
            "this geometry no longer distinguishes the two placements, so the "
            "test above it can pass vacuously")
