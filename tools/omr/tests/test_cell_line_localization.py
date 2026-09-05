"""A cell's stored staff-line grid, moved onto the ink printed under it.

`Staff.line_ys` models a staff as five ideal horizontal rows across its whole
width, and `_build_measure_cell` copies those five constants into every cell of
the staff. A SCANNED staff tilts: measured over 7 staves of 5 editions the
residual runs 8-17 page px at the staff's ends, 0.3-0.65 staff spaces
(`benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md`), which is enough to name
the wrong half-step slot for every note in an end-of-staff bar.

These are synthetic, so the displacement is known by construction rather than
traced: a staff is drawn with a deliberate ramp and the fit is asked to recover
it. No PDFs, no model.

⚠️ THE FLAG-OFF PATH IS PART OF THE CONTRACT. The localization is behind
`OMR_CELL_LINE_TRACE` (ON by default since 2026-09-04), and a run with it disabled must
produce the byte-identical grid it always did — every batch of hand-labeled
cells stores its boxes in a frame derived from these numbers.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr import measure_extractor as me
from tools.omr.types import PageImage, PageWithStaves, Staff

PAGE_W = 900
PAGE_H = 400
SPACING = 20
NOMINAL_YS = [100, 120, 140, 160, 180]
X_START, X_END = 50, 850


def _page(binary: np.ndarray) -> PageImage:
    """⚠️ The RGB carries the same ink as the binary, and it has to. The
    localization reads `page.binary` (0 = ink, Phase 1's convention) while
    `header_ink.refine_staff_lines_in_cell` reads `cell.image`, the RGB — so a
    fixture that inks only the binary makes the refiner see blank paper and
    return 0, which looks exactly like "the refiner agrees" and is really "the
    refiner was handed nothing." That silently emptied this file's first
    attempt at the composition test below.
    """
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8)
    rgb[binary == 0] = 0
    return PageImage(
        pdf_path=Path("synthetic.pdf"),
        page_index=0,
        dpi=300,
        rgb=rgb,
        binary=binary,
    )


def _draw_staff(ramp_px: float = 0.0, thickness: int = 3,
                at_left_px: float = 0.0) -> np.ndarray:
    """Five printed lines whose y drifts linearly from `at_left_px` at
    `X_START` to `ramp_px` at `X_END` — the shape the page probe measured, a
    smooth ramp rather than a step. `at_left_px` is for the case that bows at
    the LEFT end instead (Scheherazade p.4, +7 px there against −1 at the
    right). 0 = ink, the project's binarization convention.
    """
    binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
    for x in range(X_START, X_END):
        frac = (x - X_START) / float(X_END - X_START)
        drift = int(round(at_left_px + (ramp_px - at_left_px) * frac))
        for y in NOMINAL_YS:
            top = y + drift - thickness // 2
            binary[top:top + thickness, x] = 0
    return binary


def _staff() -> Staff:
    return Staff(page_index=0, staff_index=0, line_ys=list(NOMINAL_YS),
                 x_start=X_START, x_end=X_END, system_index=0)


def _pws(binary: np.ndarray) -> PageWithStaves:
    return PageWithStaves(page=_page(binary), staves=[_staff()], barlines=[])


# ─── the fit recovers a displacement it was not told about ───────────────────

class TestCombFitRecoversTheRamp:
    @pytest.mark.parametrize("ramp_px", [-14, -8, 8, 14])
    def test_offset_matches_the_drift_under_the_cell(self, ramp_px):
        """At the far end of the staff the whole ramp is the displacement."""
        pws = _pws(_draw_staff(ramp_px=ramp_px))
        staff = pws.staves[0]
        # A cell at the right end: the drift there is the full ramp.
        got = me._cell_line_offset(pws, staff, X_END - 100, X_END - 5)
        assert got is not None, "the fit abstained on a plainly tilted staff"
        offset, prov = got
        assert abs(offset - ramp_px) <= 2, (offset, ramp_px, prov)

    def test_mid_staff_cell_is_left_alone(self):
        """The ideal fit crosses the real line mid-staff, so there is nothing
        to correct there — and a correction would be the damage."""
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        mid = (X_START + X_END) // 2
        got = me._cell_line_offset(pws, staff, mid - 40, mid + 40)
        # The ramp reaches 7px at the midpoint of a 14px ramp, and line_ys is
        # the fit over the whole staff — so a mid-staff cell may move a little
        # or not at all, but never by the end-of-staff amount.
        if got is not None:
            assert abs(got[0]) < abs(14), got

    def test_a_straight_staff_moves_nothing(self):
        """An engraved page is straight, and this must be a no-op on it —
        the control the engraved orchestral benchmark stands in for."""
        pws = _pws(_draw_staff(ramp_px=0))
        staff = pws.staves[0]
        for x0 in (X_START + 5, 400, X_END - 100):
            got = me._cell_line_offset(pws, staff, x0, x0 + 90)
            assert got is None, (x0, got)


# ─── it abstains rather than dragging the grid onto a glyph ──────────────────

class TestCoverageCountsRowsRatherThanRequiringAllFive:
    """⚠️ Requiring ALL five rows to be inked threw away a correct answer on
    one of the two labels this work exists to have prevented.

    `brahms1-p2-sys1-s20-m6` fits at −0.436 spaces against a hand-measured
    −0.40 with coverage [1.00, 1.00, 0.374, 1.00, 1.00]: the staff's own
    MODELED rows are unevenly spaced (gaps 27, 22, 33, 28 px at spacing 27.5),
    so one comb row cannot sit on the print at any shift. Phase 1's fit is
    distorted there, not merely displaced, and a rigid comb inherits that.
    """

    def test_a_staff_whose_own_model_has_one_bad_row_still_fits(self):
        pws = _pws(_draw_staff(ramp_px=12))
        staff = pws.staves[0]
        # Displace ONE modeled row off the even grid, as phase 1 did there.
        staff.line_ys = [100, 120, 133, 160, 180]
        got = me._cell_line_offset(pws, staff, X_END - 200, X_END - 5)
        assert got is not None, "four rows agreeing is evidence enough"
        assert got[1]["rows_covered"] == 4, got[1]


class TestAbstains:
    def test_no_staff_line_comb_under_the_cell(self):
        """One thick horizontal bar — a beam — is a strong single row, not a
        comb. Counting covered rows is what tells them apart, and it still
        does with the four-of-five rule: a beam covers one."""
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        binary[150:158, 200:400] = 0     # a beam, no staff at all
        pws = _pws(binary)
        got = me._cell_line_offset(pws, pws.staves[0], 200, 400)
        assert got is None, got

    def test_three_rows_is_not_enough(self):
        """The rule is four of five. Three printed lines under a cell is a
        fragment, not a staff — and the bound has to bite somewhere.
        """
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        for y in NOMINAL_YS[:3]:
            binary[y - 1:y + 2, X_START:X_END] = 0
        pws = _pws(binary)
        assert me._cell_line_offset(
            pws, pws.staves[0], X_END - 200, X_END - 5) is None

    def test_blank_paper(self):
        pws = _pws(np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8))
        assert me._cell_line_offset(pws, pws.staves[0], 200, 400) is None

    def test_displacement_beyond_the_bound_is_refused(self):
        """Bounded below one spacing so aliasing is unreachable: past that,
        the nearest printed line to a modeled row is a DIFFERENT line, and a
        confident answer there is confidently wrong.
        """
        # Draw the staff a full spacing below where the model says it is.
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        for y in NOMINAL_YS:
            binary[y + SPACING - 1:y + SPACING + 2, X_START:X_END] = 0
        pws = _pws(binary)
        got = me._cell_line_offset(pws, pws.staves[0], 400, 500)
        # Either it abstains, or it answers something inside its own bound —
        # what it must never do is report the full spacing.
        if got is not None:
            limit = me.CELL_LINE_MAX_SHIFT_SPACES * SPACING
            assert abs(got[0]) <= limit, got

    def test_degenerate_x_range(self):
        pws = _pws(_draw_staff(ramp_px=14))
        assert me._cell_line_offset(pws, pws.staves[0], 500, 501) is None

    def test_a_narrow_cell_has_too_little_evidence(self):
        """A cell a couple of staff spaces wide aliases instead of failing
        quietly — the comb slides a whole spacing, four of its five rows still
        land on a line, and nothing else in the cell votes. Measured on the
        scan corpus: every over-half-a-space answer with the bound raised came
        from a cell 2.2-3.7 spaces wide, at row coverage 1.00, so the
        coherence test cannot catch these.
        """
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        narrow = int(SPACING * (me.CELL_LINE_MIN_WIDTH_SPACES - 1))
        assert me._cell_line_offset(
            pws, staff, X_END - narrow - 5, X_END - 5) is None
        # ... and the same place, measured wide enough, does answer.
        wide = int(SPACING * (me.CELL_LINE_MIN_WIDTH_SPACES + 1))
        assert me._cell_line_offset(
            pws, staff, X_END - wide - 5, X_END - 5) is not None

    def test_one_line_staff_has_no_comb_to_fit(self):
        pws = _pws(_draw_staff(ramp_px=14))
        pws.staves[0].line_ys = [140]
        pws.staves[0].nominal_line_spacing_px = float(SPACING)
        assert me._cell_line_offset(pws, pws.staves[0], 400, 500) is None


# ─── the flag, and what a run without it must produce ────────────────────────

class TestFlag:
    def test_default_is_on(self, monkeypatch):
        # Shipped default-ON 2026-09-04, priced on the widened scan gate
        # (pooled 0.8387 -> 0.8345); OFF is now the explicit opt-out.
        monkeypatch.delenv(me.ENV_CELL_LINE_TRACE, raising=False)
        assert me._cell_line_trace_enabled() is True

    @pytest.mark.parametrize("raw,want", [
        ("1", True), ("true", True), ("YES", True), ("on", True),
        ("0", False), ("false", False), ("OFF", False), ("no", False),
        ("", True), ("maybe", True),
    ])
    def test_env_parsing(self, monkeypatch, raw, want):
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, raw)
        assert me._cell_line_trace_enabled() is want

    def test_flag_off_stores_the_staff_level_rows_unchanged(self, monkeypatch):
        """The contract every labeled batch depends on: with the flag off, a
        cell's grid is `staff.line_ys - y0`, exactly as before."""
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "0")
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        cell = me._build_measure_cell(pws, staff, 0, X_END - 100, X_END - 5, 0)
        assert cell is not None
        y0 = cell.bbox_page_px[1]
        want = [int(round((y - y0) * cell.upscale_factor)) for y in staff.line_ys]
        assert cell.staff_line_ys_canonical == want
        assert "line_grid_localized" not in cell.__dict__

    def test_flag_on_moves_the_grid_and_records_why(self, monkeypatch):
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "1")
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        cell = me._build_measure_cell(pws, staff, 0, X_END - 100, X_END - 5, 0)
        assert cell is not None
        y0 = cell.bbox_page_px[1]
        unmoved = [int(round((y - y0) * cell.upscale_factor))
                   for y in staff.line_ys]
        assert cell.staff_line_ys_canonical != unmoved
        prov = cell.__dict__.get("line_grid_localized")
        assert prov is not None and prov["offset_px"] != 0

    def test_the_staff_level_model_is_never_mutated(self, monkeypatch):
        """Only the per-cell copy localizes — `Staff.line_ys` stays the one
        description of the whole staff that everything else reads."""
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "1")
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        before = list(staff.line_ys)
        me._build_measure_cell(pws, staff, 0, X_END - 100, X_END - 5, 0)
        assert staff.line_ys == before

    def test_the_crop_and_the_span_are_unchanged_by_localizing(self, monkeypatch):
        """A rigid slide of the rows, not a re-cut: the cell's pixels and the
        span it is normalised by must be identical either way, or every box in
        every labeled batch lands somewhere else on the image.
        """
        pws = _pws(_draw_staff(ramp_px=14))
        staff = pws.staves[0]
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "0")
        off = me._build_measure_cell(pws, staff, 0, X_END - 100, X_END - 5, 0)
        monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "1")
        on = me._build_measure_cell(pws, staff, 0, X_END - 100, X_END - 5, 0)
        assert off is not None and on is not None
        assert off.bbox_page_px == on.bbox_page_px
        assert off.upscale_factor == on.upscale_factor
        assert np.array_equal(off.image, on.image)
        # and the rows keep their spacing — slid, not re-fitted
        gaps = lambda ys: [b - a for a, b in zip(ys, ys[1:])]  # noqa: E731
        assert gaps(on.staff_line_ys_canonical) == gaps(off.staff_line_ys_canonical)


class TestComposesWithTheHeaderRefiner:
    """`header_ink.refine_staff_lines_in_cell` already slides a HEADER cell's
    rows onto its ink, and header cells are built through
    `_build_measure_cell` — so the two now run in sequence on the same cell.

    They cannot double-correct: the refiner scores absolute ink at the rows the
    cell currently carries, not a delta from the staff-level model, so it
    finds nothing to do where localization already landed and corrects the
    remainder where it did not. This pins that, because reasoning it through
    is not the same as knowing it.
    """

    def _header_cell(self, monkeypatch, flag: bool):
        from tools.omr.header_ink import refine_staff_lines_in_cell
        # Bows at the LEFT end, where the header sits.
        pws = _pws(_draw_staff(ramp_px=0, at_left_px=12))
        staff = pws.staves[0]
        if flag:
            monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "1")
        else:
            monkeypatch.setenv(me.ENV_CELL_LINE_TRACE, "0")
        cell = me._build_measure_cell(
            pws, staff, 0, X_START, X_START + int(SPACING * 8), 0)
        assert cell is not None
        shift = refine_staff_lines_in_cell(cell)
        return cell, shift

    def test_both_paths_end_on_the_printed_lines(self, monkeypatch):
        off, off_shift = self._header_cell(monkeypatch, flag=False)
        on, on_shift = self._header_cell(monkeypatch, flag=True)
        # Same answer either way — the refiner is the specialist on a header
        # window and localization must not fight it.
        assert on.staff_line_ys_canonical == off.staff_line_ys_canonical
        # ... and with localization on there is less left for it to do.
        assert abs(on_shift) <= abs(off_shift)
