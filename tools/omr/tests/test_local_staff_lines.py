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
        """A single cell spanning most of a small ramp (well under the
        total-drift bound, `CELL_LINE_WALK_MAX_TOTAL_SPACES` * SPACING =
        6px here): the LEFT end of the cell must read lines near the
        nominal row, the RIGHT end near the full displacement — a single
        flat grid cannot be both."""
        pws = _pws(_draw_staff(ramp_px=5))
        staff = pws.staves[0]
        paths = me._trace_cell_local_lines(pws, staff, X_START + 10, X_END - 10)
        assert paths is not None, "tracing declined on a plainly printed staff"
        assert len(paths) == 5
        left_top = paths[0][5]     # a few columns into the band
        right_top = paths[0][-5]   # a few columns from its end
        assert abs(left_top - NOMINAL_YS[0]) < 2, left_top
        assert abs(right_top - (NOMINAL_YS[0] + 5)) < 2, right_top
        # And a midpoint reads something in between, not a single shift.
        mid = paths[0][len(paths[0]) // 2]
        assert NOMINAL_YS[0] < mid < NOMINAL_YS[0] + 5

    def test_a_ramp_past_the_total_drift_bound_is_capped(self):
        """A 14px/0.7-space ramp (`CELL_LINE_WALK_MAX_TOTAL_SPACES` = 0.3,
        i.e. 6px here) exceeds what the comb may walk from the staff's own
        rigid course -- added 2026-10-01 after 55 of 84 right-to-wrong
        regressions on the real re-gather traced to the comb aliasing onto
        a NEIGHBOURING line through a long dense passage (up to 11px, past
        a full line on some staves). The bound must hold the comb at (or
        under) it, never follow the ramp past it."""
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        shift = me._walk_comb_shift(pws.page.binary, [float(y) for y in NOMINAL_YS],
                                    X_START + 10, X_END - 10, float(SPACING))
        assert shift is not None
        assert np.max(np.abs(shift)) <= 0.3 * SPACING + 0.5, shift.max()

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

    def test_no_ink_anywhere_holds_at_the_nominal_comb(self):
        """Sean's design: the comb only moves where ink CONFIRMS it; with no
        ink at all, every step holds, so the walk never updates away from
        the nominal (unshifted) rigid comb it started at -- not an
        abstention, because nothing here CONTRADICTS the starting comb
        either (compare test_abstains_when_the_band_is_too_narrow_to_walk,
        a control that CAN fail)."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        pws = PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])
        paths = me._trace_cell_local_lines(pws, pws.staves[0], 200, 400)
        assert paths is not None
        for i, y in enumerate(NOMINAL_YS):
            assert np.all(paths[i] == y), (i, paths[i])

    def test_abstains_when_the_band_is_too_narrow_to_walk(self):
        """A control that CAN fail: a band narrower than a single step has
        no column to take even one step over, so the walk must say so
        rather than inventing a one-point course."""
        pws = _pws(_draw_staff(ramp_px=0))
        got = me._trace_cell_local_lines(pws, pws.staves[0], 200, 200)
        assert got is None, got


class TestCombMovesAsOneShape:
    """Sean's design, proved directly against `_walk_comb_shift`: the comb
    moves only where >=3 of 5 lines agree within ~1px, a single outlier
    line never drags it, and a stretch with too little ink simply HOLDS the
    comb's last course."""

    def test_an_outlier_line_never_moves_the_comb(self):
        """Four lines straight, ONE line's own ink displaced by 6px (a
        beam, a slur, a stray mark sitting where that line should be) --
        the comb must follow the FOUR, not average in the fifth."""
        binary = _draw_staff(ramp_px=0)
        # Displace line index 2 (y=140) by +6px over the whole band.
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        for x in range(X_START, X_END):
            for i, y in enumerate(NOMINAL_YS):
                yy = y + (6 if i == 2 else 0)
                binary[yy - 1:yy + 2, x] = 0
        pws = PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])
        shift = me._walk_comb_shift(binary, [float(y) for y in NOMINAL_YS],
                                    X_START + 5, X_END - 5, float(SPACING))
        assert shift is not None
        # The outlier's own +6px never pulls the comb more than a tiny
        # fraction of the way there.
        assert np.max(np.abs(shift)) < 1.0, shift

    def test_a_blob_covering_most_lines_holds_the_comb(self):
        """A dense blob (a chord, several ledger lines) covers 4 of 5
        lines' own narrow search windows over one stretch -- fewer than 3
        can still find clean ink there, so the comb must HOLD exactly the
        course it already had, not drift toward the blob's own ink."""
        binary = _draw_staff(ramp_px=0)
        blob_x0, blob_x1 = 300, 340
        binary[90:170, blob_x0:blob_x1] = 0   # solid ink over 4 of 5 lines
        shift = me._walk_comb_shift(binary, [float(y) for y in NOMINAL_YS],
                                    X_START + 5, X_END - 5, float(SPACING))
        assert shift is not None
        all_cols = np.arange(X_START + 5, X_END - 5)
        in_blob = (all_cols >= blob_x0) & (all_cols < blob_x1)
        before = shift[np.where(all_cols < blob_x0)[0][-1]]
        # Inside the blob's own columns, the comb holds -- it does not jump.
        assert np.allclose(shift[in_blob], before, atol=0.5), shift[in_blob]


class TestCentreNotEdge:
    """Sean, on the first comb-walk's own crops: 'the green line is on the
    ink but towards the TOP of the ink' -- `_measure_line_run_mid` must
    answer the run's MIDPOINT even when the search window is NOT already
    centred on it (the exact situation a correction exists for)."""

    def test_midpoint_survives_an_off_centre_window(self):
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        # A 5px-thick line centred at y=150 (148..152 inclusive).
        binary[148:153, 200:260] = 0
        # A window that fully CONTAINS the run but whose own centre (151)
        # sits near the line's bottom edge, not its middle -- the exact
        # shape a slightly-off running prediction produces. The withdrawn
        # ink-weighted-centroid design would read this window off-centre
        # too (less ink visible above the window's own middle than below);
        # the midpoint of the run's own top/bottom must not care.
        found = me._measure_line_run_mid(binary, 200, 260, 146.0, 156.0,
                                         max_thickness_px=10.0)
        assert found is not None
        mid, thickness = found
        assert mid == pytest.approx(150.0, abs=0.5), (mid, thickness)
        assert thickness == pytest.approx(5.0, abs=0.5)

    def test_a_thick_run_is_declined_not_measured(self):
        """A run much taller than a bare line (a stem, a barline, a
        notehead) must be declined, never averaged into an answer."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        binary[100:160, 200:210] = 0  # a 60px-tall run -- not a staff line
        found = me._measure_line_run_mid(binary, 200, 210, 120.0, 140.0,
                                         max_thickness_px=10.0)
        assert found is None, found


class TestBarlinesAndConsistencyRun:
    def test_a_barline_column_excludes_its_neighbours(self):
        binary = _draw_staff(ramp_px=0)
        bx = 400
        margin = me.CELL_LINE_WALK_BARLINE_MARGIN_PX
        top_y, bottom_y = float(NOMINAL_YS[0]), float(NOMINAL_YS[-1])
        assert me._is_barline_column(binary, bx, top_y, bottom_y) is False
        binary[int(top_y):int(bottom_y) + 1, bx - margin:bx + margin + 1] = 0
        assert me._is_barline_column(binary, bx, top_y, bottom_y) is True

    def test_a_single_accepted_step_cannot_move_the_comb(self):
        """A ramp drawn for only ONE step's width (everywhere else flat) --
        even a perfectly clean, agreeing single step must not commit a
        move; `CELL_LINE_WALK_MIN_CONSISTENT_RUN` consecutive steps are
        required."""
        binary = _draw_staff(ramp_px=0)
        step_px = max(1, int(round(me.CELL_LINE_WALK_STEP_SPACES * SPACING)))
        one_step_x0 = 400
        for x in range(one_step_x0, one_step_x0 + step_px):
            for y in NOMINAL_YS:
                binary[y + 4:y + 7, x] = 0   # this one step's lines read +5px
        shift = me._walk_comb_shift(binary, [float(y) for y in NOMINAL_YS],
                                    X_START + 5, X_END - 5, float(SPACING))
        assert shift is not None
        assert np.max(np.abs(shift)) < 0.5, shift.max()


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

    def test_a_cell_with_no_page_geometry_at_all_falls_back_unchanged(self):
        """A cell never built by `_build_measure_cell` (no `bbox_page_px`/
        `upscale_factor` -- e.g. a test double standing in for an
        already-known-correct grid, same shape as `test_staged_pipeline.
        FakeCell`) never had the means to ATTEMPT a local trace. That is not
        the same as a real cell DECLINING one, and must not abstain -- this
        is the regression this lane's own first cut of the fallback caused
        and the manager's review caught via test_staged_pipeline.py."""
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q

        cell = SimpleNamespace(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            staff_line_ys_canonical=[0, 20, 40, 60, 80],
            # no bbox_page_px, no upscale_factor, no line_grid_localized
        )
        det = _FakeDet(x_center=10, y_center=20)
        log = Log()
        cell_key = R.cell(0, 0, 0, 0).to_key()
        g.gather_notehead_positions(
            log, [cell], {0: (0, 0)}, {cell_key: [det]})
        glyph_sub = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, glyph_sub)
        assert len(rows) == 1
        assert rows[0].value == pytest.approx(2.0, abs=1e-6)


# ─── 2026-10-01: the comb is SEEDED from today's per-bar grid ("orange") ─────
#
# DECISIONS 2026-10-01 (Sean): "let's use the current process to start where
# the comb starts -- so the green line should take a cue from the orange
# lines so it can't get lost and then it should tilt with the ink as it
# does." The one-head trace (FINDINGS.md, same date) found the UNSEEDED
# comb silently answering the raw, unshifted lines (shift 0) on a busy cell
# (Litolff p3 bar 49) where `_cell_line_offset` ("orange") had already found
# a real +6px shift -- "could not tell" was being read as "zero" (rule 8).

class TestCombSeededFromOrange:
    def test_a_cell_that_never_commits_holds_the_seed_not_zero(self):
        """RED on the unseeded comb (`benchmarks/omr-local-staff-2026-09/
        FINDINGS.md`, 2026-10-01 one-head trace): a cell solid with ink top
        to bottom (six stems and a beam, in the real bar) never finds a
        single CLEAN run anywhere, so it never commits a move and holds its
        starting value for the whole band. Unseeded, that start is 0 -- the
        raw, un-localized lines, wrong whenever orange had already measured
        a real shift. Seeded with orange's own +6px, the held value is +6,
        not 0."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        top = min(NOMINAL_YS) - 5
        bottom = max(NOMINAL_YS) + 6 + 5
        binary[top:bottom, X_START:X_END] = 0  # solid ink: no clean line anywhere

        shift_unseeded = me._walk_comb_shift(
            binary, [float(y) for y in NOMINAL_YS],
            X_START + 5, X_END - 5, float(SPACING))
        assert shift_unseeded is not None
        assert np.allclose(shift_unseeded, 0.0), shift_unseeded  # today's bug

        shift_seeded = me._walk_comb_shift(
            binary, [float(y) for y in NOMINAL_YS],
            X_START + 5, X_END - 5, float(SPACING), seed_shift_px=6.0)
        assert shift_seeded is not None
        assert np.allclose(shift_seeded, 6.0), shift_seeded

    def test_tilted_clean_staff_still_bends_with_the_ink_from_the_seed(self):
        """A clean, printed tilt (0px drift at the left end, 4px at the
        right -- well under the 6px/0.3-space total bound FROM THE SEED)
        with a seed of 2px (an orange answer that is neither end's true
        value): the comb must still find and follow the REAL ink at each
        end, not freeze at the seed -- seeding must not turn off bending."""
        pws = _pws(_draw_staff(ramp_px=4))
        staff = pws.staves[0]
        shift = me._walk_comb_shift(
            pws.page.binary, [float(y) for y in NOMINAL_YS],
            X_START + 10, X_END - 10, float(SPACING), seed_shift_px=2.0)
        assert shift is not None
        left = shift[5]
        right = shift[-5]
        assert abs(left - 0.0) <= 2.0, left
        assert abs(right - 4.0) <= 2.0, right

    def test_build_measure_cell_seeds_from_its_own_orange_shift(self):
        """`_build_measure_cell` must pass THIS cell's own `_cell_line_offset`
        shift into the comb as its seed, not call it unseeded -- the wiring
        this lane adds. A busy cell (solid ink) that never commits must
        store a local grid at orange's own shift, matching the stored flat
        grid (`line_grid_localized`) exactly, never at the raw unlocalized
        lines."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        thickness = 3
        for x in range(X_START, X_END):
            for y in NOMINAL_YS:
                top_y = y + 6 - thickness // 2
                binary[top_y:top_y + thickness, x] = 0
        # A dense busy patch covering most of the cell's own width so the
        # comb (searching a narrow window right around the seed) finds
        # clean ink only in a thin margin -- not enough to ever commit a
        # move of its own, but orange (which scores the WHOLE cell at once)
        # still finds the +6px rigid shift.
        busy_lo, busy_hi = X_START + 20, X_END - 20
        top = min(NOMINAL_YS) - 2
        bottom = max(NOMINAL_YS) + 6 + 2
        binary[top:bottom, busy_lo:busy_hi] = 0
        pws = PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])
        staff = pws.staves[0]
        cell = me._build_measure_cell(pws, staff, 0, X_START + 5, X_END - 5, 0)
        assert cell is not None
        line_prov = cell.__dict__.get("line_grid_localized")
        assert line_prov is not None, "orange should have measured this cell's shift"
        assert line_prov["offset_px"] == 6
        local = getattr(cell, "local_line_paths_px", None)
        assert local is not None, "the comb should still trace (even if it never commits)"
        _, paths = local
        # The comb never finds a commit-worthy clean run in this busy cell,
        # so every column holds its start -- which must be orange's +6, not 0.
        assert np.allclose(paths[0], NOMINAL_YS[0] + 6, atol=0.5), paths[0][:5]
