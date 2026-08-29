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
# A monograph: prose pages, and music examples set into prose. It is the only
# source here for open score (four voices, full vocal clef set) and for the
# body-text-as-staff filter.
NOTTEBOHM = Path("/Users/seanjohnson/Downloads/Nottebohm-Beethovens-Studien-1873.pdf")
# The corpus's only ONE-LINE staff: Cymbales, twelfth of 21 parts.
LAMER = SCORE_DIR / "PDF Scores" / "IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf"

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

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "REGRESSION FROM A MERGE, not from either side alone: this branch "
            "passes it standalone, and main passes its own suite, but "
            "main + this branch reads Beethoven 5 p.10 as 7+13+15 bars instead "
            "of 14+15. The connectivity grouping in system_grouping.py is NOT "
            "the cause — swapping it for the old gap heuristic on the merged "
            "tree gives an identical [1,10,11]/[7,13,15]. The likely cause is "
            "main's 46ca8c6 (staff x-extent + system edges), which moves the "
            "x extents that barline detection windows on, compounding the "
            "staff-0 split already covered by the xfail below. When this "
            "starts passing, that interaction has been resolved — update it "
            "rather than removing it."
        ),
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


# ─── Nottebohm — open score on a mostly-prose page ────────────────────────────


class TestNottebohmPage46:
    """PDF page 46 (printed p.31) of Nottebohm's Beethovens Studien.

    Three exercises (Nr. 20, 21, 22), each an open score of four staves — one
    voice per staff, in the full vocal clef set. This layout class is absent
    from the two scores above and is where Phase 1 has historically been
    weakest, in two ways it is worth guarding against:

      * staff lines here are dashed enough that taking the longest CONTIGUOUS
        run put the cell's left edge up to 46 staff spaces past the clef;
      * open-score barlines stop at each staff instead of running through the
        gaps between them, so a connectivity filter tuned on orchestral scores
        discards every one of them. When that happened, this page collapsed
        from 88 cells to 12 — one measure per staff, no structure at all.

    The counts below are the ones that can be stated with certainty: Sean read
    the layout off the page, and it is plainly three groups of four. The
    per-measure count is NOT asserted exactly — the engraving is too fine to
    count reliably at the resolution available, and guessing it would repeat
    the mistake this file's other expectations used to make. A floor is enough
    to catch the collapse, which is the regression that actually happened.
    """

    @pytest.fixture(scope="class")
    def pipeline_output(self):
        _require(NOTTEBOHM)
        page = render_page(NOTTEBOHM, 46, dpi=300)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        return page, pws, cells

    def test_staff_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        assert len(pws.staves) == 12, "three exercises of four staves each"

    def test_system_count(self, pipeline_output):
        _, pws, _ = pipeline_output
        n_systems = 1 + max(s.system_index for s in pws.staves)
        assert n_systems == 3, "Nr. 20, Nr. 21, Nr. 22"

    def test_each_system_has_four_staves(self, pipeline_output):
        _, pws, _ = pipeline_output
        sizes = [0, 0, 0]
        for staff in pws.staves:
            sizes[staff.system_index] += 1
        assert sizes == [4, 4, 4]

    def test_measures_are_segmented_at_all(self, pipeline_output):
        _, _, cells = pipeline_output
        # The floor that matters: 12 cells means one measure per staff, i.e.
        # barline detection produced nothing and each system became a single
        # cell. Anything in that region is the collapse, not a near miss.
        per_staff: dict[tuple[int, int], int] = {}
        for c in cells:
            per_staff[(c.system_index, c.staff_index)] = (
                per_staff.get((c.system_index, c.staff_index), 0) + 1
            )
        assert min(per_staff.values()) >= 4, (
            f"a staff segmented into {min(per_staff.values())} measures — "
            "open-score barlines are being discarded again"
        )
        assert len(cells) >= 60, f"only {len(cells)} cells for 12 staves"


class TestBodyTextIsNotAStaff:
    """Paragraphs of body text must not be detected as staves.

    The row-projection detector finds staves by looking for rows carrying a lot
    of ink, and a row of justified prose carries a lot of ink — enough to clear
    the line-length threshold — while five consecutive text baselines are
    evenly enough spaced to pass the 5-line grouping. Before this was filtered,
    a paragraph became a "staff" with a clef and measures of its own: 147 of
    1522 "staves" over 156 pages of this book.

    Nottebohm is a monograph, so it supplies both cases cleanly — pages of
    unbroken prose, and pages where a music example sits inside the prose.
    The page contents below were checked by eye.
    """

    @pytest.mark.parametrize("page_index", [23, 24, 27])
    def test_a_page_of_pure_prose_yields_no_staves(self, page_index):
        _require(NOTTEBOHM)
        pws = detect_staves(render_page(NOTTEBOHM, page_index, dpi=300))
        assert pws.staves == [], (
            f"p{page_index} is unbroken prose but produced "
            f"{len(pws.staves)} staves"
        )

    @pytest.mark.parametrize(
        "page_index,n_music_staves",
        [
            (25, 8),   # prose with one eight-staff example set into it
            (29, 2),   # prose with one two-staff example
        ],
    )
    def test_prose_pages_keep_only_their_music(self, page_index, n_music_staves):
        _require(NOTTEBOHM)
        pws = detect_staves(render_page(NOTTEBOHM, page_index, dpi=300))
        assert len(pws.staves) == n_music_staves

    def test_a_dense_example_page_keeps_all_of_its_music(self):
        """p.90 carries a lot of music among the prose, so it is the case where
        the text filter could plausibly over-reach.

        This asserted exactly 6 and was WRONG — the page was rendered and
        counted (2026-08-28) and holds about thirteen music staves: an incipit,
        three small fragments, and four grand-staff systems with short
        fragments between them. The detector now finds 11 of them, every one
        with a staff-like ink signature (0.03-0.16 ink runs per space against a
        1.7 text threshold), because the comb pass recovers lightly printed
        staves the strict pass drops.

        Asserted as a floor rather than a count: the true number was read off a
        render, but which of the small fragments the detector reaches is a
        moving target, and pinning it would re-make the mistake this file's
        expectations used to make.
        """
        _require(NOTTEBOHM)
        pws = detect_staves(render_page(NOTTEBOHM, 90, dpi=300))
        assert len(pws.staves) >= 10, (
            f"only {len(pws.staves)} staves on a page holding about thirteen"
        )

    def test_the_filter_does_not_touch_a_page_of_pure_music(self):
        # The guard that matters for everything else in the corpus: a real
        # score must be unaffected. WTC p.5 is ten staves and stays ten.
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


# ─── La Mer p.25 — a one-line percussion staff among 21 parts ────────────────


class TestLaMerPage25:
    """PDF page index 25 (printed p.168) at 300 DPI: one 21-staff system whose
    twelfth part, Cymbales, is printed as a SINGLE rule.

    Ground truth read off the page's left margin part by part
    (`benchmarks/omr-phase1-baseline/ground-truth.json`, evidence/ alongside).
    The page is here for what a missed one-line staff COSTS: the detector used
    to report 20 staves, so everything from the harp down — both harp staves,
    four divided violin staves, violas, celli and basses — carried a
    staff_index one lower than its true slot, and slot identity is what feeds
    instrument, transposition and expected clef.
    """

    GT = GROUND_TRUTH["lamer-p25"]

    @pytest.fixture(scope="class")
    def staves(self):
        _require(LAMER)
        return detect_staves(render_page(LAMER, 25, dpi=300)).staves

    def test_staff_count(self, staves):
        assert len(staves) == self.GT["n_staves"]

    def test_one_staff_is_a_single_rule(self, staves):
        singles = [s for s in staves if len(s.line_ys) == 1]
        assert len(singles) == self.GT["n_single_line_staves"]
        assert [s.staff_index for s in singles] == self.GT["single_line_staff_indices"]

    def test_the_single_rule_carries_the_pages_spacing(self, staves):
        """It has no spacing of its own, and everything downstream sizes its
        windows in staff spaces, so it answers with the page's."""
        perc = [s for s in staves if len(s.line_ys) == 1][0]
        five_line = [s.line_spacing_px for s in staves if len(s.line_ys) == 5]
        page_spacing = sorted(five_line)[len(five_line) // 2]
        assert perc.line_spacing_px == pytest.approx(page_spacing, rel=0.05)

    def test_the_staves_below_it_keep_their_slots(self, staves):
        """The harp is the thirteenth part on the page, so it must be
        staff_index 12 — one more than the cymbal rule above it."""
        perc = [s for s in staves if len(s.line_ys) == 1][0]
        below = [s for s in staves if s.top_y > perc.top_y]
        assert below[0].staff_index == perc.staff_index + 1
        assert len(below) == 9, "harp x2, violins x4, violas, celli, basses"
