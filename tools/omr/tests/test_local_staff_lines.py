"""The LOCAL staff-line model (ROADMAP 2.48) — lines read at the SUBJECT's
own x, never a staff-wide or per-cell-flat value (CLAUDE.md §10, 2026-09-30).

`_cell_line_offset` (test_cell_line_localization.py) slides the whole
five-line comb by ONE shift for a cell. On a scan that tilts or stretches
WITHIN a measure — Litolff p3 staff/3/0/0's top line wanders 447-454 px
(~5% spacing change) across one system — that single shift still hands every
reader in the cell the same flat grid. This file tests the finer model:
`measure_extractor._trace_cell_local_lines` (reusing `header_ink.
trace_staff_line`, the same tracer staff-line erasure already runs, column by
column) and `gather._local_cell_grid_at`, which reads it at one x.

Fixtures are synthetic and reused from test_cell_line_localization.py's
pattern: a staff drawn with a known ramp, so the displacement at any x is
known by construction, not by a second measurement.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr import measure_extractor as me
from tools.omr.staged import gather as g
from tools.omr.types import PageImage, PageWithStaves, Staff

PAGE_W = 900
PAGE_H = 400
SPACING = 20
NOMINAL_YS = [100, 120, 140, 160, 180]
X_START, X_END = 50, 850


def _page(binary: np.ndarray) -> PageImage:
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8)
    rgb[binary == 0] = 0
    return PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                      rgb=rgb, binary=binary)


def _draw_staff(ramp_px: float = 0.0, thickness: int = 3) -> np.ndarray:
    """Five printed lines whose y drifts linearly from 0 at X_START to
    `ramp_px` at X_END. 0 = ink."""
    binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
    for x in range(X_START, X_END):
        frac = (x - X_START) / float(X_END - X_START)
        drift = int(round(ramp_px * frac))
        for y in NOMINAL_YS:
            top = y + drift - thickness // 2
            binary[top:top + thickness, x] = 0
    return binary


def _staff() -> Staff:
    return Staff(page_index=0, staff_index=0, line_ys=list(NOMINAL_YS),
                 x_start=X_START, x_end=X_END, system_index=0)


def _pws(binary: np.ndarray) -> PageWithStaves:
    return PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])


# ─── the tracer follows the ramp, not one flat shift ─────────────────────────

class TestTraceFollowsTheRampAtTheSubjectsOwnX:
    def test_two_ends_of_one_cell_read_different_lines(self):
        """A single cell spanning most of a 14px ramp: the LEFT end of the
        cell must read lines near the nominal row, the RIGHT end near the
        full displacement — a single flat grid cannot be both."""
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        paths = me._trace_cell_local_lines(pws, staff, X_START + 10, X_END - 10)
        assert paths is not None, "tracing declined on a plainly printed staff"
        assert len(paths) == 5
        left_top = paths[0][5]     # a few columns into the band
        right_top = paths[0][-5]   # a few columns from its end
        assert abs(left_top - NOMINAL_YS[0]) < 2, left_top
        assert abs(right_top - (NOMINAL_YS[0] + 14)) < 2, right_top
        # And a midpoint reads something in between, not a single shift.
        mid = paths[0][len(paths[0]) // 2]
        assert NOMINAL_YS[0] < mid < NOMINAL_YS[0] + 14

    def test_flat_staff_traces_to_the_nominal_row_everywhere(self):
        """Control: an engraved page is straight, so the local trace must
        agree with the nominal row along the whole band — the case this
        model must be a no-op on."""
        pws = _pws(_draw_staff(ramp_px=0))
        staff = pws.staves[0]
        paths = me._trace_cell_local_lines(pws, staff, X_START + 10, X_END - 10)
        assert paths is not None
        for i, y in enumerate(NOMINAL_YS):
            assert np.max(np.abs(paths[i] - y)) < 1.5, (i, paths[i])

    def test_abstains_with_no_staff_ink_under_the_band(self):
        """A control that can fail (CLAUDE.md §2 rule 7): no printed lines at
        all, so there is nothing to trace and the model must say so rather
        than inventing a row."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        pws = PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])
        got = me._trace_cell_local_lines(pws, pws.staves[0], 200, 400)
        assert got is None, got


# ─── the cell carries the model, and a consumer reads it at its own x ────────

class TestBuildMeasureCellStoresTheLocalModel:
    def test_tilted_staff_cell_carries_a_local_trace(self):
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        cell = me._build_measure_cell(pws, staff, 0, X_START + 10, X_END - 10, 0)
        assert cell is not None
        local = getattr(cell, "local_line_paths_px", None)
        assert local is not None, "a plainly tilted, plainly printed staff must trace"
        x0, paths = local
        assert x0 == X_START + 10
        assert len(paths) == 5 and len(paths[0]) == (X_END - 10) - (X_START + 10)


# ─── gather._local_cell_grid_at: Sean's confirmed D6, with his real numbers ──

class TestLocalCellGridAt:
    def _fake_cell(self, x0, paths, bbox_y0=0.0, scale=1.0):
        return SimpleNamespace(
            local_line_paths_px=(x0, paths),
            bbox_page_px=(x0, bbox_y0, x0 + len(paths[0]), bbox_y0 + 1),
            upscale_factor=scale,
        )

    def test_seans_d6_at_litolff_p3_bar_55(self):
        """Printed lines at x≈902: 450.5/466.5/481.5/497.5/513.5, box centre
        407.8 — Sean's confirmed read is D6, position −5.42 against those
        PRINTED lines (DECISIONS 2026-09-30, 'the green staff lines are not
        lined up with the staff lines'). The pipeline's flat per-bar grid at
        that bar answered −5.56 (E6, wrong); this asserts the local model
        reproduces Sean's own number from his own printed-line measurements."""
        lines_at_902 = [450.5, 466.5, 481.5, 497.5, 513.5]
        paths = [np.array([y]) for y in lines_at_902]
        cell = self._fake_cell(902, paths)
        grid = g._local_cell_grid_at(cell, 902)
        assert grid is not None
        top_y, half_step = grid
        assert top_y == pytest.approx(450.5)
        assert half_step == pytest.approx(7.875)
        pos_float = (407.8 - top_y) / half_step
        assert pos_float == pytest.approx(-5.42, abs=0.01)

    def test_outside_the_traced_band_clamps_rather_than_raising(self):
        paths = [np.array([100.0, 101.0, 102.0]) for _ in range(5)]
        for i, p in enumerate(paths):
            paths[i] = p + i * 20.0  # 5 rows, 20px apart, drifting +1px/col
        cell = self._fake_cell(900, paths)
        got_far = g._local_cell_grid_at(cell, 10_000)
        got_in = g._local_cell_grid_at(cell, 901)
        assert got_far is not None and got_in is not None
        # clamped to the last column, not out of range
        assert got_far[0] == pytest.approx(102.0)

    def test_no_local_trace_returns_none(self):
        cell = SimpleNamespace(bbox_page_px=(0, 0, 10, 10), upscale_factor=1.0)
        assert g._local_cell_grid_at(cell, 5) is None


# ─── gather_notehead_positions prefers local, falls back to the flat grid ────

class _FakeDet:
    def __init__(self, x_center, y_center, smufl_name="noteheadBlack"):
        self.x_center = x_center
        self.y_center = y_center
        self.smufl_name = smufl_name


class TestGatherNoteheadPositionsPrefersLocal:
    def _cell(self, **overrides):
        base = dict(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            staff_line_ys_canonical=[0, 20, 40, 60, 80],  # flat, no drift
            bbox_page_px=(900, 0, 1000, 100),
            upscale_factor=1.0,
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_uses_local_grid_when_present(self):
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q

        # A cell whose flat grid (staff_line_ys_canonical) is WRONG relative
        # to the local trace at the glyph's own x — the exact fault this
        # roadmap item exists to fix.
        cell = self._cell(
            line_grid_localized={"offset_px": 0},  # this cell's own grid IS measured
            local_line_paths_px=(900, [np.array([5.0] * 100),
                                        np.array([25.0] * 100),
                                        np.array([45.0] * 100),
                                        np.array([65.0] * 100),
                                        np.array([85.0] * 100)]),
        )
        det = _FakeDet(x_center=10, y_center=5)  # sits ON the local top line
        log = Log()
        cell_key = R.cell(0, 0, 0, 0).to_key()
        g.gather_notehead_positions(
            log, [cell], {0: (0, 0)}, {cell_key: [det]})
        glyph_sub = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, glyph_sub)
        assert len(rows) == 1
        # On the LOCAL grid the head sits exactly on the top line: pos 0,
        # NOT the flat grid's answer (which would be (5-0)/10 = 0.5).
        assert rows[0].value == pytest.approx(0.0, abs=1e-6)

    def test_falls_back_to_a_measured_flat_grid_when_local_declines(self):
        """No local trace on this cell, but its OWN flat grid came from
        `_cell_line_offset`'s measured shift (`line_grid_localized` set) --
        CLAUDE.md §10 allows this fallback, the one short of staff-wide."""
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q

        cell = self._cell(line_grid_localized={"offset_px": 3})
        det = _FakeDet(x_center=10, y_center=20)  # on the flat grid's 2nd line
        log = Log()
        cell_key = R.cell(0, 0, 0, 0).to_key()
        g.gather_notehead_positions(
            log, [cell], {0: (0, 0)}, {cell_key: [det]})
        glyph_sub = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, glyph_sub)
        assert len(rows) == 1
        assert rows[0].value == pytest.approx(2.0, abs=1e-6)

    def test_abstains_rather_than_the_staff_wide_fallback(self):
        """No local trace AND the cell's own flat grid is NOT this cell's
        measured offset (no `line_grid_localized`) -- i.e. `_cell_grid(c)`
        would answer off the raw staff-wide `Staff.line_ys`. CLAUDE.md §10:
        that must never happen silently, so this abstains instead, counted."""
        from tools.omr.staged import record as R
        from tools.omr.staged.record import ABSTAIN, Log, Q

        cell = self._cell()  # no line_grid_localized, no local_line_paths_px
        det = _FakeDet(x_center=10, y_center=20)
        log = Log()
        cell_key = R.cell(0, 0, 0, 0).to_key()
        g.gather_notehead_positions(
            log, [cell], {0: (0, 0)}, {cell_key: [det]})
        glyph_sub = R.glyph(0, 0, 0, 0, 0)
        assert log.rows(Q.NOTEHEAD_STAFF_POSITION, glyph_sub) == ()
        refusals = log.refusals(Q.NOTEHEAD_STAFF_POSITION, glyph_sub)
        assert len(refusals) == 1
        assert refusals[0].reason == ABSTAIN.GRID_NOT_LOCALIZED
