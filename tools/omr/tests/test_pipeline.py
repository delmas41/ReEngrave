"""Phase 1 regression tests.

These assert structural counts on pages whose ground truth has been
visually verified. Any change to the pipeline that breaks one of these is
a regression that the author needs to consciously accept.

Marked `omr_smoke` so they can be skipped in fast CI loops and run as a
slower verification step:

    pytest tools/omr/tests/                              # run smoke tests
    pytest tools/omr/tests/ -k 'wtc'                      # one piece
    pytest tools/omr/tests/ -m 'not omr_smoke'            # everything else
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures, _drop_close_outliers
from tools.omr.staff_line_removal import remove_staff_lines


# Test PDFs — paths set up for the user's local machine. Tests skip if
# the file isn't present, so they're safe to ship as-is.
SCORE_DIR = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
WTC = SCORE_DIR / "PDF Scores" / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"
BEETHOVEN5 = SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"

# Beethoven 5, 1862 Breitkopf & Härtel Werke edition — sits in the gitignored
# IMSLP training catalog. Used to lock in the orchestral system-grouping fix
# (Phase C, 2026-05-23) since this edition's tighter inter-staff spacing was
# what surfaced the bug.
BEETHOVEN5_BREITKOPF1862 = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp/"
    "beethoven-symphony-5/pdfs/imslp-52624/score.pdf"
)


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"test PDF not present: {path}")


pytestmark = pytest.mark.omr_smoke


# ─── WTC Book 1 — solo keyboard, two-staff systems ────────────────────────────


class TestWTCPage5:
    """Page 5 of WTC Book 1 (rendered at 600 DPI). Verified visually.

    Layout: 5 grand-staff systems (10 staves total) with 3+3+3+3+4 measures.
    """

    @pytest.fixture(scope="class")
    def pipeline_output(self):
        _require(WTC)
        page = render_page(WTC, 5, dpi=600)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        return page, pws, cells

    def test_render_size(self, pipeline_output):
        page, _, _ = pipeline_output
        assert (page.width, page.height) == (5100, 6600), "600 DPI letter-page render"

    def test_staff_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        assert len(pws.staves) == 10, "5 grand-staff systems × 2 = 10 staves"

    def test_system_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        n_systems = 1 + max(s.system_index for s in pws.staves)
        assert n_systems == 5, "should detect 5 systems (grand-staff pairs)"

    def test_each_system_has_two_staves(self, pipeline_output):
        _, pws, _ = pipeline_output
        sizes = [0] * 5
        for s in pws.staves:
            sizes[s.system_index] += 1
        assert sizes == [2, 2, 2, 2, 2]

    def test_measures_per_system(self, pipeline_output):
        _, _, cells = pipeline_output
        per_sys: dict[int, set[int]] = {}
        for c in cells:
            per_sys.setdefault(c.system_index, set()).add(c.measure_index)
        counts = [len(per_sys[i]) for i in sorted(per_sys.keys())]
        assert counts == [3, 3, 3, 3, 4], "verified visually: 3+3+3+3+4 measures"

    def test_total_cells(self, pipeline_output):
        _, _, cells = pipeline_output
        # 2 staves/system × (3+3+3+3+4 measures) = 32 cells
        assert len(cells) == 32

    def test_cell_canonical_size(self, pipeline_output):
        _, _, cells = pipeline_output
        # Every cell should be ≤ 2048 wide (canonical max)
        for c in cells:
            assert c.width <= 2048
            assert c.height > 200, f"cell too small: {c.width}x{c.height}"

    def test_staff_line_removal_present(self, pipeline_output):
        _, _, cells = pipeline_output
        for c in cells:
            assert c.image_no_staff is not None
            assert c.image_no_staff.shape == c.image.shape[:2]


# ─── Beethoven 5 — orchestral score (16+ staves per page) ─────────────────────


class TestBeethoven5Page10:
    """Page 10 of Beethoven 5 score (m274 area). Orchestral, ~18 instruments.

    Layout: 2 systems (top and bottom), 18 staves total. Measure counts
    are partially verified visually — exact counts are bounded rather
    than asserted-equal because dense orchestral pages have over-detection
    margins we accept as Phase 1 limits.
    """

    @pytest.fixture(scope="class")
    def pipeline_output(self):
        _require(BEETHOVEN5)
        page = render_page(BEETHOVEN5, 10, dpi=600)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        return page, pws, cells

    def test_staff_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        assert len(pws.staves) == 18, "Beethoven 5 page 10 has 18 staves"

    def test_system_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        n_systems = 1 + max(s.system_index for s in pws.staves)
        assert n_systems == 2, "two-systems-per-page layout"

    def test_measure_counts_reasonable(self, pipeline_output):
        _, _, cells = pipeline_output
        per_sys: dict[int, set[int]] = {}
        for c in cells:
            per_sys.setdefault(c.system_index, set()).add(c.measure_index)
        for sys, ms in per_sys.items():
            n = len(ms)
            # Verified visually: 6-8 measures per system on this page.
            # Allow a small margin around that.
            assert 5 <= n <= 10, f"system {sys}: {n} measures (expected 5-10)"

    def test_cell_quality(self, pipeline_output):
        _, _, cells = pipeline_output
        assert len(cells) > 0
        # Sample a few cells; all should hit canonical max width or close.
        widths = [c.width for c in cells]
        # At least some cells should be at the upscale ceiling.
        assert max(widths) == 2048


# ─── Beethoven 5, 1862 Breitkopf — orchestral system grouping regression ──────


class TestBeethoven5Breitkopf1862SystemGrouping:
    """Regression test for the orchestral system-grouping bug (Phase C,
    2026-05-23). This edition has tighter inter-staff spacing (~100 px
    intra-system) than other Beethoven editions; the old _assign_systems
    heuristic split it into 8 spurious sub-systems instead of 1.

    Page expectations are confirmed visually against the 1862 B&H Werke
    score (Beethoven 5 in C minor, Op.67, plate B.5, 106 pp). DPI is 300
    here to keep the test under a few seconds — the production pipeline
    runs at 600 DPI but staff grouping is DPI-invariant.
    """

    @pytest.mark.parametrize("page_1indexed, expected_systems, expected_min_staves", [
        (7,  1,  12),   # mvt 1 first music page — 1 system × 12 instruments
        (20, 2,  24),   # mvt 1 mid-movement — 2 stacked orchestral systems
        (56, 1,  16),   # mvt 4 start — 1 system, expanded orchestration
                        # (piccolo + contrabassoon + 3 trombones enter here)
    ])
    def test_system_grouping(self, page_1indexed, expected_systems, expected_min_staves):
        _require(BEETHOVEN5_BREITKOPF1862)
        pi = render_page(BEETHOVEN5_BREITKOPF1862, page_1indexed - 1, dpi=300)
        pws = detect_staves(pi)
        n_systems = 1 + max((s.system_index for s in pws.staves), default=-1)
        assert n_systems == expected_systems, (
            f"page {page_1indexed}: expected {expected_systems} systems, got {n_systems}"
        )
        assert len(pws.staves) >= expected_min_staves, (
            f"page {page_1indexed}: staff detection regressed "
            f"(found {len(pws.staves)}, expected >= {expected_min_staves})"
        )

    def test_page7_barline_count_not_overcounting(self):
        """Bug 2 regression — Beethoven 5 mvt 1 first music page should not
        produce 14+ false-positive barlines from chord-stem clusters.

        Pre-Bug-2-fix this page produced 14 barlines from a system of
        ~7-9 actual measures (chord-stem columns at half-measure spacing
        got rescued by the lenient Prong B 3-vote threshold). After the
        fix it should be in a reasonable range — we assert it's at most
        12 (a conservative upper bound on plausible orchestral measure
        density for a first music page that carries title + tempo + key/
        time-sig setup).
        """
        _require(BEETHOVEN5_BREITKOPF1862)
        pi = render_page(BEETHOVEN5_BREITKOPF1862, 6, dpi=300)  # page 7, 0-indexed
        pws = detect_staves(pi)
        pws = detect_barlines(pws)
        sys0_barlines = [bl for bl in pws.barlines if bl.system_index == 0]
        assert 5 <= len(sys0_barlines) <= 12, (
            f"page 7 sys0: {len(sys0_barlines)} barlines "
            f"(expected 5-12; pre-fix was 14)"
        )


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
