"""The staff frame survives the file boundary.

OMR is a sequence of erasures — binarize, deskew, crop, rescale, remove the
staff lines — and each one is safe only because what it destroys is written
down somewhere else. In memory that held: `MeasureCell` keeps the original
image beside the staff-line-removed one, and carries the staff's five lines
along with it, which is why `clef_geometry` can tell an alto clef from a tenor
(same glyph, one line apart) without ever looking at a pixel of the erased
image.

The output JSON used to break that chain. It emitted the *readings* — clef,
pitch, key signature — but not the five lines they were measured against, so
nothing downstream could check a clef against its staff, re-derive a pitch
from a box, or repeat a snap. These tests pin the frame in place: a consumer
holding only the JSON must be able to reproduce what the pipeline decided.

Synthetic — no PDF, no weights — so it runs in the default suite.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.omr.clef_geometry import resolve_clef, resolve_clef_for_detection
from tools.omr.measure_extractor import _build_measure_cell
from tools.omr.pitch_resolver import _pitch_from_position, pitch_for_notehead
from tools.omr.template_matcher import SymbolDetection
from tools.omr.transcribe import _staff_geometry
from tools.omr.types import PageImage, PageWithStaves, Staff


PAGE_W, PAGE_H = 1000, 400
STAFF_YS = [100, 120, 140, 160, 180]  # spacing 20, span 80
MEASURE_X0, MEASURE_X1 = 50, 250


def _cell_and_staff():
    """One real MeasureCell off a synthetic page, plus the Staff it came from.

    Built through `_build_measure_cell` rather than by hand so the canonical
    rescale is the production one — the scale factor and the canonical line
    positions are whatever the real code computes.
    """
    page = PageImage(
        pdf_path=Path("synthetic.pdf"),
        page_index=0,
        dpi=300,
        rgb=np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8),
        binary=np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8),
    )
    staff = Staff(
        page_index=0, staff_index=0, line_ys=list(STAFF_YS),
        x_start=MEASURE_X0, x_end=850, system_index=0,
    )
    pws = PageWithStaves(page=page, staves=[staff])
    cell = _build_measure_cell(pws, staff, 0, MEASURE_X0, MEASURE_X1, 0)
    assert cell is not None
    return cell, staff


def _emit(cell, staff) -> tuple[dict, dict]:
    """The two JSON blocks transcribe writes, built the same way it builds
    them. Everything below consumes ONLY these — no cell, no staff object."""
    return (
        _staff_geometry(staff),
        {
            "bbox_page_px": list(cell.bbox_page_px),
            "staff_line_ys_canonical": [int(y) for y in cell.staff_line_ys_canonical],
            "upscale_factor": round(float(cell.upscale_factor), 6),
        },
    )


class TestFramesAgree:
    """The page frame and the canonical frame describe the same five lines."""

    def test_canonical_lines_derivable_from_page_lines(self):
        geom, measure = _emit(*_cell_and_staff())
        y0 = measure["bbox_page_px"][1]
        scale = measure["upscale_factor"]
        derived = [round((y - y0) * scale) for y in geom["line_ys_page"]]
        assert derived == measure["staff_line_ys_canonical"]

    def test_page_lines_derivable_from_canonical_lines(self):
        # The inverse direction — a consumer working from a canonical box can
        # get back to the page without re-rendering the PDF.
        geom, measure = _emit(*_cell_and_staff())
        y0 = measure["bbox_page_px"][1]
        scale = measure["upscale_factor"]
        derived = [round(y / scale + y0) for y in measure["staff_line_ys_canonical"]]
        assert derived == geom["line_ys_page"]

    def test_upscale_factor_rounding_preserves_the_frame(self):
        # upscale_factor is rounded on the way out. Round it too hard and
        # every canonical y drifts; 6 dp has to survive the round trip.
        cell, staff = _cell_and_staff()
        _, measure = _emit(cell, staff)
        assert abs(measure["upscale_factor"] - cell.upscale_factor) < 1e-6


class TestReadingsAreReproducible:
    """The point of the whole block: a JSON-only consumer reaches the same
    answer the pipeline did."""

    def test_clef_line_resolves_the_same_from_json_as_from_the_cell(self):
        cell, staff = _cell_and_staff()
        geom, measure = _emit(cell, staff)

        # A C clef centred on the middle line — an alto clef. Nothing but the
        # geometry can say so: cClefAlto and cClefTenor are the same drawing
        # one line apart, so the class label alone cannot decide it.
        lines = cell.staff_line_ys_canonical
        spacing = (lines[-1] - lines[0]) / 4.0
        height = int(round(4 * spacing))
        det = SymbolDetection(
            cell=cell, smufl_name="cClefAlto", category="clef",
            x_canonical=10, y_canonical=int(round(lines[2] - height / 2)),
            width_canonical=int(round(2 * spacing)), height_canonical=height,
            confidence=0.9,
        )

        live = resolve_clef_for_detection(det)
        from_json = resolve_clef(
            det.smufl_name,
            y_top=det.y_canonical,
            height=det.height_canonical,
            staff_line_ys=measure["staff_line_ys_canonical"],
        )
        assert live.source == "geometry"      # geometry actually ran
        assert live.name == "alto" and live.line == 3
        assert (from_json.name, from_json.line) == (live.name, live.line)

        # And in the page frame, off staff_geometry instead.
        page_h = height / measure["upscale_factor"]
        page_top = det.y_canonical / measure["upscale_factor"] + measure["bbox_page_px"][1]
        in_page_frame = resolve_clef(
            det.smufl_name, y_top=page_top, height=page_h,
            staff_line_ys=geom["line_ys_page"],
        )
        assert (in_page_frame.name, in_page_frame.line) == (live.name, live.line)

    def test_pitch_resolves_the_same_from_json_as_from_the_cell(self):
        cell, staff = _cell_and_staff()
        _, measure = _emit(cell, staff)
        lines = cell.staff_line_ys_canonical
        spacing = (lines[-1] - lines[0]) / 4.0

        # Walk every line and space across the staff, plus a ledger position
        # either side, and check the JSON-only derivation never diverges.
        for step in range(-2, 11):
            y_center = lines[0] + step * (spacing / 2.0)
            head = int(round(spacing * 0.7))
            det = SymbolDetection(
                cell=cell, smufl_name="noteheadBlack", category="notehead",
                x_canonical=100, y_canonical=int(round(y_center - head / 2)),
                width_canonical=head, height_canonical=head, confidence=0.9,
            )
            live = pitch_for_notehead(det, clef="treble")

            json_lines = measure["staff_line_ys_canonical"]
            half = ((json_lines[-1] - json_lines[0]) / 4.0) / 2.0
            pos = round((det.y_center - json_lines[0]) / half)
            from_json = _pitch_from_position(pos, "treble")

            assert from_json == live, f"diverged at step {step}"


class TestAbstention:
    def test_geometry_is_null_not_missing_when_the_staff_is_unusable(self):
        # A consumer checks one key. Emitting nothing at all would be
        # indistinguishable from an older file that predates the block.
        assert _staff_geometry(None) is None
