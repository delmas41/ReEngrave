"""Unit tests for the shared header-ink primitives
(`tools/omr/header_ink.py`) — staff-line tracing and glyph clustering.

These exist for a specific failure: on 19th-century prints the staff lines are
thick (0.15–0.31 staff spaces, against ~0.08 for a modern engraving) and they
wander, so generic morphology either leaves them or shreds the glyphs with
them. The fixtures below reproduce both properties deliberately.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tools.omr.header_ink import (
    MAX_HEADER_LINE_SHIFT_SPACES,
    cluster_components,
    cluster_components_2d,
    erase_staff_lines,
    refine_staff_lines_in_cell,
    trace_staff_line,
)

SPACING = 40.0
LINE_YS = [40, 80, 120, 160, 200]
H, W = 280, 400


def _mask(thickness: int = 10, wobble: int = 0) -> np.ndarray:
    """A mask (255 = ink) with thick, optionally wandering staff lines."""
    m = np.zeros((H, W), dtype=np.uint8)
    for y in LINE_YS:
        for x in range(W):
            dy = int(round(wobble * np.sin(x / 60.0)))
            top = y + dy - thickness // 2
            m[top : top + thickness, x] = 255
    return m


def _add_glyph(m: np.ndarray, x: int, y: int, w: int = 24, h: int = 70) -> None:
    """A blob standing in for an accidental, crossing at least one line."""
    m[y : y + h, x : x + w] = 255


# ─── tracing ────────────────────────────────────────────────────────────────

class TestTrace:
    def test_measures_a_thick_line(self):
        path, thickness = trace_staff_line(_mask(thickness=12), 120, SPACING)
        assert thickness == pytest.approx(12, abs=2)
        assert np.allclose(path, 120, atol=2)

    def test_follows_a_wandering_line(self):
        # The property a straight-band erase cannot handle.
        path, _ = trace_staff_line(_mask(thickness=8, wobble=6), 120, SPACING)
        assert path.max() - path.min() >= 6

    def test_a_glyph_on_the_line_does_not_inflate_thickness(self):
        m = _mask(thickness=8)
        _add_glyph(m, 100, 90)          # sits across the middle line
        _, thickness = trace_staff_line(m, 120, SPACING)
        assert thickness == pytest.approx(8, abs=3)

    def test_blank_region_abstains(self):
        assert trace_staff_line(np.zeros((H, W), np.uint8), 120, SPACING) is None


# ─── erasing ────────────────────────────────────────────────────────────────

class TestErase:
    def test_lines_are_removed(self):
        out = erase_staff_lines(_mask(thickness=10), LINE_YS, SPACING)
        # Ink left along the line rows should be negligible.
        assert (out[115:125] > 0).mean() < 0.05

    def test_wandering_lines_are_removed(self):
        out = erase_staff_lines(_mask(thickness=8, wobble=6), LINE_YS, SPACING)
        assert (out > 0).mean() < 0.05

    def test_a_glyph_crossing_a_line_survives_in_one_piece(self):
        m = _mask(thickness=8)
        _add_glyph(m, 100, 90, w=24, h=70)
        out = erase_staff_lines(m, LINE_YS, SPACING)
        n, _labels, stats, _c = cv2.connectedComponentsWithStats(out, connectivity=8)
        big = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 200]
        assert len(big) == 1, "the glyph should be bridged back together, not cut in two"
        assert stats[big[0], cv2.CC_STAT_HEIGHT] >= 60

    def test_the_line_itself_is_not_bridged_back(self):
        # The bridging rule keys on how FAR the "something continues" condition
        # holds: narrow for a glyph, the whole width for a line.
        out = erase_staff_lines(_mask(thickness=14), LINE_YS, SPACING)
        assert (out[110:130] > 0).mean() < 0.10


# ─── clustering ─────────────────────────────────────────────────────────────

class TestClusterComponents:
    """The clef clusterer: near in x AND near in y."""

    STAFF = (100, 155)   # the staff's own top and bottom line, in pixels

    def test_a_heading_above_the_staff_does_not_join_the_clef(self):
        # What cost the clef locator most of its coverage. A movement heading
        # printed above the staff sits in the same narrow column as the clef,
        # so grouping on the x-gap alone produced one cluster six or more
        # staff spaces tall, which was then thrown away as far too big to be
        # a clef.
        clef = (40, 100, 30, 55, 900)
        heading = (44, 20, 34, 30, 700)
        merged = cluster_components([clef, heading], max_gap=12, max_y_gap=6,
                                    on_staff=self.STAFF)
        assert len(merged) == 2

    def test_two_pieces_that_both_touch_the_staff_always_join(self):
        # The safety rule: a glyph printed on the staff arrives in pieces, and
        # they must stay together however far apart the morphology left them,
        # because half a treble clef is the size and shape of a C clef.
        body = (40, 96, 30, 40, 900)
        tail = (46, 150, 12, 40, 400)     # 14px below the body, well over the gap
        merged = cluster_components([body, tail], max_gap=12, max_y_gap=6,
                                    on_staff=self.STAFF)
        assert len(merged) == 1

    def test_without_on_staff_the_gap_applies_to_everything(self):
        body = (40, 96, 30, 40, 900)
        tail = (46, 150, 12, 40, 400)
        assert len(cluster_components([body, tail], max_gap=12, max_y_gap=6)) == 2

    def test_pieces_of_one_glyph_still_join_across_an_erased_line(self):
        # Stripping the staff lines severs a glyph's vertical strokes, so its
        # pieces arrive a line-thickness apart and MUST rejoin: a piece of a
        # treble clef on its own is the size and shape of a C clef.
        upper = (40, 100, 30, 24, 500)
        lower = (40, 129, 30, 26, 520)
        assert len(cluster_components([upper, lower], max_gap=12, max_y_gap=6)) == 1

    def test_a_fragment_can_bridge_two_others_it_sits_between(self):
        # Why this is union-find and not a left-to-right chain: the middle
        # fragment is what connects the outer two, and it is not the one
        # immediately preceding either of them in x order.
        left = (40, 100, 10, 20, 180)
        right = (70, 100, 10, 20, 180)
        middle = (52, 104, 16, 12, 150)
        merged = cluster_components([left, right, middle], max_gap=12, max_y_gap=6)
        assert len(merged) == 1

    def test_without_a_y_limit_it_groups_on_x_alone(self):
        clef = (40, 100, 30, 55, 900)
        heading = (44, 20, 34, 30, 700)
        assert len(cluster_components([clef, heading], max_gap=12)) == 1

    def test_horizontally_distant_boxes_do_not_merge(self):
        boxes = [(10, 100, 20, 40, 800), (200, 100, 20, 40, 800)]
        assert len(cluster_components(boxes, max_gap=20, max_y_gap=6)) == 2

    def test_empty_input(self):
        assert cluster_components([], max_gap=20, max_y_gap=6) == []

    def test_output_is_left_to_right(self):
        boxes = [(200, 100, 20, 40, 800), (10, 100, 20, 40, 800),
                 (100, 100, 20, 40, 800)]
        merged = cluster_components(boxes, max_gap=5, max_y_gap=6)
        assert [m[0] for m in merged] == sorted(m[0] for m in merged)


class TestCluster2D:
    def test_vertically_disjoint_neighbours_do_not_merge(self):
        # The bug this function fixes: an accidental merging with the stem
        # above it into a cluster four spaces tall, which then fails the
        # accidental size gate and is discarded.
        boxes = [(10, 100, 20, 40, 800), (12, 10, 8, 60, 480)]
        merged = cluster_components_2d(boxes, max_gap=20)
        assert len(merged) == 2

    def test_side_by_side_parts_of_one_glyph_merge(self):
        # A flat's ascender and bowl: adjacent in x, overlapping in y.
        boxes = [(10, 100, 8, 44, 350), (20, 120, 22, 24, 500)]
        merged = cluster_components_2d(boxes, max_gap=20)
        assert len(merged) == 1
        assert merged[0][2] >= 30

    def test_stacked_fragments_are_left_to_the_bridging_step(self):
        # Two halves of a glyph cut apart by an erased line band do NOT overlap
        # in y, so clustering cannot rejoin them — and must not, or it would
        # rejoin a glyph to the unrelated ink above it just as readily.
        # Reconnecting those is `erase_staff_lines`' bridging, which does it in
        # the mask before components are ever labelled.
        boxes = [(10, 100, 20, 18, 360), (10, 122, 20, 18, 360)]
        assert len(cluster_components_2d(boxes, max_gap=20)) == 2

    def test_horizontally_distant_boxes_do_not_merge(self):
        boxes = [(10, 100, 20, 40, 800), (200, 100, 20, 40, 800)]
        assert len(cluster_components_2d(boxes, max_gap=20)) == 2

    def test_empty_input(self):
        assert cluster_components_2d([], max_gap=20) == []

    def test_output_is_left_to_right(self):
        boxes = [(200, 100, 20, 40, 800), (10, 100, 20, 40, 800), (100, 100, 20, 40, 800)]
        merged = cluster_components_2d(boxes, max_gap=5)
        assert [m[0] for m in merged] == sorted(m[0] for m in merged)


class TestRefineStaffLinesInCell:
    """A header cell's staff lines must sit where the print has them.

    `Staff.line_ys` is a model of the WHOLE staff: five ideal rows fitted across
    its full width. The print wanders — `Staff.line_wander_px` exists because it
    does — and the header sits at the extreme left end, furthest from where a
    page-wide average is accurate. Measured on Beethoven 5 p.15 at 600 DPI, the
    header cells are off by 0.12 staff spaces on average and 0.47 at worst,
    and every staff whose key signature the pipeline managed to read is off by
    less than 0.08. Key-signature slots are half a space apart.
    """

    @staticmethod
    def _cell_with_lines_at(rows, declared):
        import numpy as np
        from tools.omr.types import MeasureCell

        img = np.full((340, 420), 255, np.uint8)
        for y in rows:
            cv2.line(img, (0, y), (419, y), 0, 2)
        return MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=-1,
            image=img, image_no_staff=None, bbox_page_px=(0, 0, 420, 340),
            staff_line_ys_canonical=list(declared), upscale_factor=1.0,
        )

    def test_a_displaced_staff_is_found(self):
        printed = [110, 130, 150, 170, 190]
        declared = [100, 120, 140, 160, 180]      # 10px = half a staff space out
        cell = self._cell_with_lines_at(printed, declared)
        shift = refine_staff_lines_in_cell(cell)
        assert shift == 10
        assert cell.staff_line_ys_canonical == printed

    def test_a_staff_already_right_is_left_alone(self):
        printed = [100, 120, 140, 160, 180]
        cell = self._cell_with_lines_at(printed, printed)
        assert refine_staff_lines_in_cell(cell) == 0.0
        assert cell.staff_line_ys_canonical == printed

    def test_it_will_not_wander_further_than_a_staff_could(self):
        """Beyond `MAX_HEADER_LINE_SHIFT_SPACES` the cell is not a displaced
        staff, it is the wrong staff — so nothing moves that far."""
        printed = [100, 120, 140, 160, 180]
        declared = [180, 200, 220, 240, 260]   # four spaces out: another staff
        cell = self._cell_with_lines_at(printed, declared)
        shift = refine_staff_lines_in_cell(cell)
        assert abs(shift) <= MAX_HEADER_LINE_SHIFT_SPACES * 20
