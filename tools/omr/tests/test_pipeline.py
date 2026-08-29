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
from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.staff_line_removal import remove_staff_lines


# Test PDFs — paths set up for the user's local machine. Tests skip if
# the file isn't present, so they're safe to ship as-is.
SCORE_DIR = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
WTC = SCORE_DIR / "PDF Scores" / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"
BEETHOVEN5 = SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"test PDF not present: {path}")


pytestmark = pytest.mark.omr_smoke


# ─── WTC Book 1 — solo keyboard, two-staff systems ────────────────────────────


class TestWTCPage5:
    """Page 5 of WTC Book 1 (rendered at 600 DPI), printed page 6.

    Layout: 5 grand-staff systems (10 staves total) with **3+2+3+3+3**
    measures — 14 in all, so 28 cells.

    Counted off the page barline by barline (2026-08-28). The second system
    has ONE internal barline and the fifth has TWO; earlier revisions of this
    file asserted 3+3+3+3+4, which the page does not support. If these numbers
    start failing again, re-count before changing them: they are ground truth,
    not a record of what the pipeline happened to produce.
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
        assert counts == [3, 2, 3, 3, 3], "counted off the page: 3+2+3+3+3 measures"

    def test_total_cells(self, pipeline_output):
        _, _, cells = pipeline_output
        # 2 staves/system × (3+2+3+3+3 measures) = 28 cells
        assert len(cells) == 28

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

    Layout: 2 systems (top and bottom), 18 staves total, holding measures
    **274-302: 14 in the first system and 15 in the second**.

    That is not an estimate. This edition prints measure numbers, and they
    settle it without counting barlines on a dense orchestral page: p.10 opens
    at 274, its second system at 288, and p.11 opens at 303. So 288-274 = 14
    and 303-288 = 15. An earlier revision of this file bounded the counts to
    5-10 per system, which this page cannot satisfy.
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
        counts = [len(per_sys[i]) for i in sorted(per_sys.keys())]
        # From the printed measure numbers (274 / 288 / 303 — see the class
        # docstring): 14 then 15. Asserted exactly, because the page states
        # the answer; a drift of even one measure here is a real regression.
        assert counts == [14, 15], f"measures 274-302 split 14 + 15, got {counts}"

    def test_cell_quality(self, pipeline_output):
        _, _, cells = pipeline_output
        assert len(cells) > 0
        widths = [c.width for c in cells]
        # Cells are upscaled toward a 2048px ceiling and clamped there. This
        # used to assert max(widths) == 2048 exactly, which tests whether the
        # page's widest measure happens to OVERFLOW the ceiling — an accident
        # of engraving, not a property of the pipeline. On this page the widest
        # comes to 2012 and the assertion failed while nothing was wrong.
        # What is worth pinning: nothing exceeds the ceiling, and the widest
        # cell is being upscaled close to it rather than left small.
        assert max(widths) <= 2048, "canonical width ceiling"
        assert max(widths) >= 1900, f"widest cell only {max(widths)}px — under-upscaled"


# ─── The staff filter must not touch real music ───────────────────────────────


class TestStaffFilterLeavesMusicAlone:
    """The guard that matters for the corpus: a real score must be unaffected
    by the row-projection filter that rejects prose.

    The prose side of this used to be covered by pages of Nottebohm's
    Beethovens Studien, a 19th-century monograph. Those tests are gone —
    a textbook is not the input this project targets — so the filter's
    behaviour ON PROSE is no longer regression-tested. `_line_ink_runs_per_space`
    in staff_detector.py still implements it, and the reasoning is recorded
    there; only the assertion went.
    """

    def test_the_filter_does_not_touch_a_page_of_pure_music(self):
        _require(WTC)
        pws = detect_staves(render_page(WTC, 5, dpi=600))
        assert len(pws.staves) == 10


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
