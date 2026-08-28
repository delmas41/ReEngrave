"""Phase 1 regression tests — staff detection, barlines, measure extraction.

These assert structural counts on pages whose layout is HAND-VERIFIED and
recorded in `benchmarks/omr-phase1-baseline/ground-truth.json`. Any change to
Phase 1 that breaks one of them is a regression the author needs to consciously
accept.

Read the ground-truth file before changing a number here. The previous version
of this module asserted counts that had been eyeballed and never checked, and
two of them were wrong in the direction that hides bugs:

  * It asserted 18 staves on Beethoven 5 p.10, which has 22. Five lightly
    printed wind staves were losing all but one line each to the ink gates, and
    the five survivors were being grouped into ONE phantom staff — so the page
    reported 18, the assertion passed, and every note on those five staves was
    invisible to the rest of the pipeline.
  * It asserted 3 bars in WTC p.6 system 2, which has 2. The extra "bar" came
    from a false barline where two stems align, and the measure that fell after
    it was being silently dropped from the page.

Marked `omr_smoke` so they can be skipped in fast CI loops:

    pytest tools/omr/tests/                              # run smoke tests
    pytest tools/omr/tests/ -k 'wtc'                      # one piece
    pytest tools/omr/tests/ -m 'not omr_smoke'            # everything else
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.staff_line_removal import remove_staff_lines


# Test PDFs — paths set up for the user's local machine. Tests skip if
# the file isn't present, so they're safe to ship as-is.
SCORE_DIR = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
WTC = SCORE_DIR / "PDF Scores" / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"
BEETHOVEN5 = SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"

GROUND_TRUTH = json.loads(
    (Path(__file__).resolve().parents[3] / "benchmarks" / "omr-phase1-baseline"
     / "ground-truth.json").read_text()
)["pages"]


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"test PDF not present: {path}")


def _layout(pdf: Path, page_index: int, dpi: int = 600):
    """Run Phase 1 and reduce it to the counts the ground truth records."""
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    per_system: dict[int, set] = {}
    for c in cells:
        per_system.setdefault(c.system_index, set()).add(c.measure_index)
    staves_per_system: dict[int, int] = {}
    for s in pws.staves:
        staves_per_system[s.system_index] = staves_per_system.get(s.system_index, 0) + 1
    return {
        "page": page,
        "pws": pws,
        "cells": cells,
        "n_staves": len(pws.staves),
        "n_systems": len(staves_per_system),
        "staves_per_system": [staves_per_system[i] for i in sorted(staves_per_system)],
        "measures_per_system": [len(per_system[i]) for i in sorted(per_system)],
        "n_cells": len(cells),
    }


pytestmark = pytest.mark.omr_smoke


# ─── WTC Book 1 — solo keyboard, two-staff systems ────────────────────────────


class TestWTCPage5:
    """PDF page index 5 (printed page 6) of WTC Book 1 at 600 DPI.

    Ground truth: 5 grand-staff systems, 3+2+3+3+3 bars. Note the 2 — system 2
    really does hold two bars, and an ink probe independent of the detector
    agrees (`benchmarks/omr-phase1-baseline/ground-truth.json`).
    """

    GT = GROUND_TRUTH["wtc-p5"]

    @pytest.fixture(scope="class")
    def out(self):
        _require(WTC)
        layout = _layout(WTC, 5)
        remove_staff_lines(layout["cells"])
        return layout

    def test_render_size(self, out):
        page = out["page"]
        assert (page.width, page.height) == (5100, 6600), "600 DPI letter-page render"

    def test_staff_count(self, out):
        assert out["n_staves"] == self.GT["n_staves"]

    def test_system_count(self, out):
        assert out["n_systems"] == self.GT["n_systems"]

    def test_staves_per_system(self, out):
        assert out["staves_per_system"] == self.GT["staves_per_system"]

    def test_measures_per_system(self, out):
        assert out["measures_per_system"] == self.GT["measures_per_system"]

    def test_total_cells(self, out):
        assert out["n_cells"] == self.GT["n_cells"]

    def test_no_page_content_is_dropped_after_the_last_barline(self, out):
        """Every system's last cell must reach its staff's right edge.

        This is the invariant the WTC system-2 bug broke: a false barline near
        the end of a system made the real final measure look like the blank
        strip after a final barline, and it was discarded. Absorbing the tail
        instead of dropping it is what keeps this true.
        """
        by_staff: dict[tuple[int, int], list] = {}
        for c in out["cells"]:
            by_staff.setdefault((c.system_index, c.staff_index), []).append(c)
        for (sys_i, staff_i), cells in by_staff.items():
            last = max(cells, key=lambda c: c.measure_index)
            staff = next(s for s in out["pws"].staves if s.staff_index == staff_i)
            assert last.bbox_page_px[2] >= staff.x_end - 2, (
                f"system {sys_i} staff {staff_i}: last cell ends at "
                f"{last.bbox_page_px[2]} but the staff runs to {staff.x_end} — "
                f"page content after the final detected barline was dropped"
            )

    def test_cell_canonical_size(self, out):
        for c in out["cells"]:
            assert c.width <= 2048
            assert c.height > 200, f"cell too small: {c.width}x{c.height}"

    def test_staff_line_removal_present(self, out):
        for c in out["cells"]:
            assert c.image_no_staff is not None
            assert c.image_no_staff.shape == c.image.shape[:2]


# ─── Beethoven 5 — pocket orchestral score, lightly printed wind staves ───────


class TestBeethoven5Page10:
    """PDF page index 10 of the Beethoven 5 pocket score (m274 / m288).

    Ground truth (Sean, 2026-08-28): two systems of 11 staves, 14 and 15 bars.
    This is the page whose five wind staves were collapsing into one phantom.
    """

    GT = GROUND_TRUTH["beet5-p10"]

    @pytest.fixture(scope="class")
    def out(self):
        _require(BEETHOVEN5)
        return _layout(BEETHOVEN5, 10)

    def test_staff_count(self, out):
        assert out["n_staves"] == self.GT["n_staves"], (
            "22 staves: 2 systems x 11. Reading 18 here is the phantom-staff "
            "bug — five wind staves collapsed into one group of 142px spacing."
        )

    def test_no_phantom_staves(self, out):
        """No staff's line spacing may stand far above the page's.

        A phantom is built from one line of each of several staves, so its
        spacing is a MULTIPLE of the real spacing — that is what makes it
        detectable without knowing the right answer, and it holds on any page.
        """
        spacings = [float(s.line_spacing_px) for s in out["pws"].staves]
        median = float(np.median(spacings))
        worst = max(spacings)
        assert worst <= median * 1.6, (
            f"staff spacing {worst:.1f} against a page median of {median:.1f} — "
            f"that group is one line borrowed from each of several staves"
        )

    def test_measures_per_system_are_read_correctly(self, out):
        """Bar counts per system, ignoring how the staves were grouped.

        Asserted as a sorted multiset because the system SPLIT (see xfail
        below) changes how bars are attributed without changing how many the
        page has.
        """
        counts = sorted(out["measures_per_system"], reverse=True)[:2]
        assert counts == sorted(self.GT["measures_per_system"], reverse=True)

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "KNOWN GAP: staff 0 splits into its own system because "
            "_staff_x_extent returns the longest contiguous ink run, and on "
            "these lightly printed staves that is a fragment (staff 0 reads "
            "x=353..1379, staff 1 x=1715..2633 — no overlap, so _assign_systems "
            "breaks). See known_gaps in ground-truth.json. Being fixed on "
            "branch claude/clef-recognition-improvement-ab75f6; when this test "
            "starts passing, that fix has landed — update it rather than "
            "removing it."
        ),
    )
    def test_system_grouping(self, out):
        assert out["n_systems"] == self.GT["n_systems"]
        assert out["staves_per_system"] == self.GT["staves_per_system"]


# ─── Preprocessing primitives ─────────────────────────────────────────────────


class TestPreprocessing:

    def test_render_page_dimensions(self):
        _require(WTC)
        page = render_page(WTC, 0, dpi=300)  # half DPI for speed
        # US Letter at 300 DPI ≈ 2550x3300; check ballpark
        assert 2400 <= page.width <= 2700
        assert 3200 <= page.height <= 3400

    def test_binary_is_uint8_zero_or_255(self):
        _require(WTC)
        page = render_page(WTC, 0, dpi=300)
        assert page.binary.dtype.name == "uint8"
        unique_vals = set(int(v) for v in page.binary.flatten()[:10000])
        assert unique_vals.issubset({0, 255}), f"binary should be 0/255, got {unique_vals}"


# ─── Gap-bipartition outlier rejection (unit test, no PDF needed) ─────────────


class TestDropCloseOutliers:
    """Direct tests of the gap-bipartition outlier filter — runs without
    needing a PDF, so always executes even in CI."""

    def test_short_lists_are_passthrough(self):
        from tools.omr.measure_extractor import _drop_close_outliers
        assert _drop_close_outliers([100, 200, 300]) == [100, 200, 300]
        assert _drop_close_outliers([]) == []

    def test_outlier_dropped_from_uniform_gaps(self):
        from tools.omr.measure_extractor import _drop_close_outliers
        # Uniform 100-px gaps with one rogue making a 20-px gap. Either
        # member of that small-gap pair is a defensible drop (without
        # more context the algorithm can't tell which is the spurious
        # entry), so we just assert one of them was dropped.
        xs = [0, 100, 120, 220, 320, 420, 520]
        out = _drop_close_outliers(xs)
        assert len(out) == 6, f"exactly one entry should be dropped: got {out}"
        assert (100 not in out) ^ (120 not in out), \
            f"exactly one of (100, 120) should be dropped: got {out}"

    def test_no_drop_when_all_gaps_similar(self):
        from tools.omr.measure_extractor import _drop_close_outliers
        xs = [0, 100, 195, 300, 395, 500, 605, 700]  # gaps ~95-105
        out = _drop_close_outliers(xs)
        assert out == xs, f"no entry should be dropped: got {out}"

    def test_skipped_when_too_few_barlines(self):
        from tools.omr.measure_extractor import _drop_close_outliers
        # Only 4 barlines with one tiny gap — should NOT be filtered
        # because the population is too small for a meaningful median.
        xs = [0, 100, 110, 250]
        out = _drop_close_outliers(xs)
        assert out == xs
