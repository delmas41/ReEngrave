"""Phase 2 regression tests — symbol library, template matcher, pitch resolver.

Marked `omr_phase2`. The library-load and pitch-resolver tests run without
needing any PDFs on disk; the WTC end-to-end test requires the WTC PDF and
is skipped otherwise.

    pytest tools/omr/tests/test_phase2.py -v
    pytest -m omr_phase2 -v
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from tools.omr.symbol_library import SymbolLibrary
from tools.omr.template_matcher import detect_symbols, SymbolDetection
from tools.omr.pitch_resolver import pitch_for_notehead, _pitch_from_position
from tools.omr.types import MeasureCell


pytestmark = pytest.mark.omr_phase2


FIXTURES = Path(__file__).parent / "fixtures"
NOTEHEAD_FIXTURE = FIXTURES / "notehead_black_isolated.png"
WTC_CELL_NOSTAFF = FIXTURES / "wtc_p5_sys0_s0_m1_nostaff.png"
WTC_CELL = FIXTURES / "wtc_p5_sys0_s0_m1.png"


# ─── Symbol library load ──────────────────────────────────────────────────────


class TestSymbolLibrary:

    def test_library_loads(self):
        lib = SymbolLibrary.load()
        assert len(lib) >= 30, f"library should have >= 30 entries, got {len(lib)}"

    def test_library_hu_moment_dim(self):
        lib = SymbolLibrary.load()
        for e in lib.entries:
            assert e.hu_moments.shape == (7,), \
                f"{e.key} has hu shape {e.hu_moments.shape}, expected (7,)"

    def test_library_categories_present(self):
        lib = SymbolLibrary.load()
        cats = set(e.category for e in lib.entries)
        # MVP must cover at least these high-priority categories
        required = {"notehead", "rest", "accidental", "clef"}
        missing = required - cats
        assert not missing, f"missing categories: {missing}"

    def test_template_files_exist(self):
        lib = SymbolLibrary.load()
        for e in lib.entries[:5]:  # spot-check first few
            img = e.load_image(lib.data_dir)
            assert img.ndim == 2
            assert img.dtype == np.uint8
            assert img.shape == tuple(e.shape)


# ─── Notehead match on an isolated crop ──────────────────────────────────────


class TestNoteheadMatch:

    def test_quarter_notehead_match(self):
        """Hand-cropped quarter notehead → top match should be noteheadBlack."""
        if not NOTEHEAD_FIXTURE.exists():
            pytest.skip(f"fixture missing: {NOTEHEAD_FIXTURE}")

        img = cv2.imread(str(NOTEHEAD_FIXTURE), cv2.IMREAD_GRAYSCALE)
        assert img is not None

        # Build a synthetic MeasureCell wrapping the crop. We give it a
        # plausible 5-line staff so notehead-search runs.
        h, w = img.shape
        # Pad to leave room for templates which need to slide
        padded = cv2.copyMakeBorder(img, 30, 30, 30, 30,
                                    cv2.BORDER_CONSTANT, value=255)
        ph, pw = padded.shape
        # Staff lines straddling the notehead vertically
        line_ys = [int(ph * 0.2 + i * 12) for i in range(5)]

        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=padded,
            image_no_staff=padded,
            bbox_page_px=(0, 0, pw, ph),
            staff_line_ys_canonical=line_ys,
            upscale_factor=1.0,
        )

        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib, confidence_threshold=0.5,
                              notehead_threshold=0.5)
        notehead_dets = [d for d in dets if d.category == "notehead"]
        assert notehead_dets, f"no notehead detected; got {[d.smufl_name for d in dets]}"
        # The top notehead detection should be noteheadBlack (quarter)
        top = max(notehead_dets, key=lambda d: d.confidence)
        assert top.smufl_name == "noteheadBlack", \
            f"expected noteheadBlack, got {top.smufl_name}"


# ─── Treble-clef pitch resolution ─────────────────────────────────────────────


class TestPitchResolverTreble:
    """Treble: top line = F5, middle line = B4, bottom line = E4."""

    @staticmethod
    def _synthetic_cell(notehead_y: int) -> MeasureCell:
        """Make a synthetic cell with a 5-line staff and a single 'notehead'
        bbox centered at (50, notehead_y) of size 24x24."""
        img = np.full((300, 100), 255, dtype=np.uint8)
        # Staff lines at y = 100, 112, 124, 136, 148 (line_spacing=12)
        return MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img,
            image_no_staff=img,
            bbox_page_px=(0, 0, 100, 300),
            staff_line_ys_canonical=[100, 112, 124, 136, 148],
            upscale_factor=1.0,
        )

    def _det(self, y_center: int) -> SymbolDetection:
        cell = self._synthetic_cell(y_center)
        return SymbolDetection(
            cell=cell, smufl_name="noteheadBlack", category="notehead",
            x_canonical=40, y_canonical=y_center - 12,
            width_canonical=24, height_canonical=24,
            confidence=1.0,
        )

    def test_top_line_is_F5(self):
        # Top line y = 100, notehead center on top line
        d = self._det(100)
        assert pitch_for_notehead(d, clef="treble") == "F5"

    def test_middle_line_is_B4(self):
        # Middle line y = 124
        d = self._det(124)
        assert pitch_for_notehead(d, clef="treble") == "B4"

    def test_bottom_line_is_E4(self):
        # Bottom line y = 148
        d = self._det(148)
        assert pitch_for_notehead(d, clef="treble") == "E4"

    def test_below_staff_by_one_position_is_D4(self):
        # One half-step below the bottom line (y = 148 + 6 = 154)
        d = self._det(154)
        assert pitch_for_notehead(d, clef="treble") == "D4"

    def test_below_staff_two_positions_is_C4(self):
        d = self._det(160)  # 148 + 12 = 160 (one full line spacing below)
        assert pitch_for_notehead(d, clef="treble") == "C4"

    def test_above_staff_one_position_is_G5(self):
        # One half-step above the top line (y = 100 - 6 = 94)
        d = self._det(94)
        assert pitch_for_notehead(d, clef="treble") == "G5"

    def test_position_math_pure(self):
        # Direct test of the position→pitch function, independent of cell math
        assert _pitch_from_position(0, "treble") == "F5"
        assert _pitch_from_position(4, "treble") == "B4"
        assert _pitch_from_position(8, "treble") == "E4"
        assert _pitch_from_position(-2, "treble") == "A5"


# ─── End-to-end: WTC cell from fixture image ──────────────────────────────────


class TestWTCCellDetection:
    """Run the detector against the saved WTC fixture cell. This test
    bypasses Phase 1 entirely (loads the saved no-staff image instead),
    so it runs even when the WTC PDF isn't on disk."""

    @pytest.fixture(scope="class")
    def cell(self):
        if not WTC_CELL_NOSTAFF.exists():
            pytest.skip(f"fixture missing: {WTC_CELL_NOSTAFF}")
        img = cv2.imread(str(WTC_CELL_NOSTAFF), cv2.IMREAD_GRAYSCALE)
        # Staff lines from the generated cell summary
        line_ys = [209, 261, 313, 364, 418]
        return MeasureCell(
            page_index=5, system_index=0, staff_index=0, measure_index=1,
            image=img,
            image_no_staff=img,
            bbox_page_px=(0, 0, img.shape[1], img.shape[0]),
            staff_line_ys_canonical=line_ys,
            upscale_factor=1.0,
        )

    def test_finds_at_least_four_noteheads(self, cell):
        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib, confidence_threshold=0.55,
                              notehead_threshold=0.6)
        noteheads = [d for d in dets if d.category == "notehead"]
        assert len(noteheads) >= 4, \
            f"WTC p5 m1 should have many noteheads; got {len(noteheads)}"

    def test_notehead_confidences_reasonable(self, cell):
        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib, confidence_threshold=0.55,
                              notehead_threshold=0.6)
        noteheads = [d for d in dets if d.category == "notehead"]
        for d in noteheads:
            assert d.confidence >= 0.5, \
                f"notehead at ({d.x_center},{d.y_center}) conf={d.confidence}"

    def test_pitches_resolvable_for_noteheads(self, cell):
        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib, confidence_threshold=0.55,
                              notehead_threshold=0.6)
        noteheads = [d for d in dets if d.category == "notehead"]
        for d in noteheads:
            p = pitch_for_notehead(d, clef="treble")
            assert p is not None and len(p) >= 2, \
                f"pitch resolution failed for notehead at ({d.x_center},{d.y_center})"


# ─── Robustness: empty / sliver cells should not crash ───────────────────────


class TestRobustness:

    def test_empty_cell_returns_empty_list(self):
        img = np.full((200, 200), 255, dtype=np.uint8)
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img, image_no_staff=img,
            bbox_page_px=(0, 0, 200, 200),
            staff_line_ys_canonical=[80, 90, 100, 110, 120],
            upscale_factor=1.0,
        )
        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib)
        assert dets == []

    def test_tiny_cell_returns_empty_list(self):
        # 10×10 cell — below the minimum threshold
        img = np.full((10, 10), 255, dtype=np.uint8)
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=img, image_no_staff=img,
            bbox_page_px=(0, 0, 10, 10),
            staff_line_ys_canonical=[],
            upscale_factor=1.0,
        )
        lib = SymbolLibrary.load()
        dets = detect_symbols(cell, lib)
        assert dets == []
