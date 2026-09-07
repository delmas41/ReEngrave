"""Phase 1 records what it threw away.

An audit on 2026-09-06 found that most of the deletion sites in
`staff_detector` and `measure_extractor` wrote no counter at all — a candidate
staff, a candidate barline or a whole measure cell would vanish leaving nothing
behind, so the only deletions anyone could reason about were the handful
someone had already gone looking at. `PageWithStaves.deletion_counts` is the
census; these tests pin each site.

⚠️ **Every assertion here was run RED first** by deleting the `_bump(...)` call
it names, and the anti-doubling test by emptying
`_DETECT_BARLINES_COUNTER_KEYS`. A counter test that passes with its counter
removed is testing nothing.

⚠️ The counters are DIAGNOSTIC. Nothing branches on one, and the byte-identity
gate on both a scan and an engraved page is what proves it — so these tests
assert that numbers are RECORDED, never that a particular verdict follows from
them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.omr import measure_extractor as me
from tools.omr import staff_detector as sd
from tools.omr.types import PageImage, PageWithStaves, Staff


def _five(top: int, spacing: int = 20) -> list[int]:
    return [top + spacing * i for i in range(5)]


def _orchestral_page(n_staves: int = 6) -> PageWithStaves:
    """One system, barlines through every staff and every gap."""
    tops = [100 + 100 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    img = np.full((tops[-1] + 300, 1000), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
    for x in (60, 260, 460, 660, 860):
        img[all_ys[0][0]:all_ys[-1][-1] + 2, x:x + 3] = 0
    staves = [Staff(page_index=0, staff_index=i, line_ys=ys,
                    x_start=40, x_end=960, system_index=0)
              for i, ys in enumerate(all_ys)]
    page = PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    return PageWithStaves(page=page, staves=staves)


def _page_with_junk(n_staves: int = 6) -> PageWithStaves:
    """`_orchestral_page` plus the ink a real page carries and Phase 1 has to
    throw away: a blob too wide to be a barline, a column closer to a real
    barline than a bar can be, and a stem aligned across every staff that
    crosses none of the gaps."""
    pws = _orchestral_page(n_staves)
    img = pws.page.binary
    top = pws.staves[0].line_ys[0]
    bot = pws.staves[-1].line_ys[-1] + 2
    img[top:bot, 300:340] = 0                       # too wide
    img[top:bot, 466:469] = 0                       # within thinning distance
    for st in pws.staves:                           # stems: no gap ink
        img[st.line_ys[0]:st.line_ys[-1] + 2, 700:703] = 0
    return pws


# ─── the container ──────────────────────────────────────────────────────────


def test_deletion_counts_defaults_to_empty_and_is_per_page():
    """Optional field, empty by default, and NOT shared between pages — a
    mutable default would have made every page's census the same object."""
    img = np.full((50, 50), 255, np.uint8)
    page = PageImage(pdf_path=Path("x.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    a = PageWithStaves(page=page, staves=[])
    b = PageWithStaves(page=page, staves=[])
    assert a.deletion_counts == {} and b.deletion_counts == {}
    a.deletion_counts["n_probe"] = 1
    assert b.deletion_counts == {}, "the default dict is shared between pages"


def test_bump_is_a_no_op_without_a_counts_dict():
    """Every helper that takes `counts` defaults it to None, which is what a
    direct call from a test or another module gets. No behaviour may depend on
    a caller having opted in."""
    for bump in (me._bump, sd._bump):
        bump(None, "n_whatever")          # must not raise
        d: dict[str, int] = {}
        bump(d, "n_zero", 0)
        assert d == {}, "a zero delta must not create a key"
        bump(d, "n_two", 2)
        bump(d, "n_two", 1)
        assert d == {"n_two": 3}


# ─── staff_detector sites ───────────────────────────────────────────────────


def test_spacing_outlier_rejection_is_counted():
    """The phantom group — one line borrowed from each of several staves.
    Dropping it is right; the count is what says the comb pass now has
    recovery work to do."""
    counts: dict[str, int] = {}
    real = [100, 120, 140, 160, 180]          # spacing 20
    phantom = [200, 340, 480, 620, 760]       # spacing 140
    kept = sd._reject_spacing_outliers([real, phantom], 20.0, counts=counts)
    assert kept == [real]
    assert counts["n_staff_groups_dropped_spacing_outlier"] == 1


def test_comb_overlap_rejection_is_counted():
    counts: dict[str, int] = {}
    strict = [[100, 120, 140, 160, 180]]
    comb = [[110, 130, 150, 170, 190],        # overlaps -> refused
            [400, 420, 440, 460, 480]]        # clear -> admitted
    out = sd._merge_staff_groups(strict, comb, counts=counts)
    assert len(out) == 2
    assert counts["n_comb_staves_dropped_overlapping_strict"] == 1


def test_uneven_peak_windows_are_counted():
    counts: dict[str, int] = {}
    # One clean staff, then five rows whose gaps are wildly uneven.
    peaks = np.array([100, 120, 140, 160, 180, 300, 305, 400, 402, 700])
    groups = sd._group_into_staves(peaks, counts=counts)
    assert groups == [[100, 120, 140, 160, 180]]
    assert counts.get("n_peak_windows_rejected_uneven_spacing", 0) >= 1


def test_a_real_page_records_a_staff_detector_census():
    """`detect_staves` hands its census to the page it returns. The key that
    must be ABSENT on music-only input is the body-text drop: a non-zero
    `n_staves_dropped_as_body_text` here would be a real regression."""
    img = np.full((900, 1000), 255, np.uint8)
    for top in (100, 300, 500):
        for y in _five(top):
            img[y:y + 2, 40:960] = 0
    page = PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    pws = sd.detect_staves(page)
    assert len(pws.staves) == 3
    assert isinstance(pws.deletion_counts, dict)
    assert pws.deletion_counts.get("n_staves_dropped_as_body_text", 0) == 0


# ─── measure_extractor sites ────────────────────────────────────────────────


def test_barline_component_shape_rejections_are_counted_apart():
    """Three shape gates, three keys — they are three different mistakes to
    make, and a single `n_dropped` total could not tell them apart.

    ⚠️ The `too_short` stroke has to TOUCH the band's own top edge, and that
    is a fact about the code rather than a fixture trick. The morphological
    opening uses a kernel exactly `min_height` tall, so in the middle of the
    band it erases anything shorter and the explicit height gate would be dead
    code. At the border it is not: OpenCV's erosion treats outside-the-image as
    maximum, so a stem running off the top or bottom of the crop survives the
    opening at well under `min_height` and the gate is what stops it. Measured
    on real pages, this is where the branch's volume comes from — 23 of 33
    surviving components on the first Brahms staff are 87 px against a
    `min_height` of 132, every one of them touching an edge.
    """
    counts: dict[str, int] = {}
    ys = _five(100)
    img = np.full((400, 600), 255, np.uint8)
    for y in ys:
        img[y:y + 2, 40:560] = 0
    img[95:185, 200:203] = 0        # a real barline, full staff span
    img[100:140, 300:303] = 0       # touches the band's top edge, half height
    img[95:185, 400:440] = 0        # too wide
    staff = Staff(page_index=0, staff_index=0, line_ys=ys,
                  x_start=40, x_end=560, system_index=0)
    found = me._detect_barlines_in_window(img, staff, 40, 561, counts=counts)
    assert found == [201], f"the real barline must be the only survivor: {found}"
    assert counts["n_barline_components_dropped_too_short"] == 1
    assert counts["n_barline_components_dropped_too_wide"] == 1


def test_per_staff_thinning_is_counted():
    """⚠️ The site that loses a real barline to a note stem — the reason
    `prefer="tallest"` exists at all. It thinned silently."""
    counts: dict[str, int] = {}
    found = [(100, 90), (104, 60), (400, 90)]   # first two within min distance
    kept = me._dedup_barline_candidates(found, counts=counts)
    assert len(kept) == 2
    assert counts["n_barline_candidates_dropped_too_close_on_staff"] == 1


def test_system_edge_barlines_are_counted():
    """The opening and closing rules, which divide no two measures. Two per
    system is the expected figure; more means the system's edges were
    measured wrong and real barlines are being eaten."""
    counts: dict[str, int] = {}
    staff = Staff(page_index=0, staff_index=0, line_ys=_five(100),
                  x_start=100, x_end=1100, system_index=0)
    from tools.omr.types import Barline
    bls = [Barline(page_index=0, x=x, y_top=95, y_bottom=185, system_index=0)
           for x in (105, 500, 800, 1095)]
    me._measure_x_boundaries(bls, [staff], counts=counts)
    assert counts["n_barlines_dropped_at_system_edge"] == 2


def test_a_degenerate_cell_is_counted_not_merely_dropped():
    """⚠️ The highest-consequence deletion in the file: a dropped cell is a
    measure that never reaches the detector at all."""
    pws = _orchestral_page(n_staves=2)
    cell = me._build_measure_cell(pws, pws.staves[0], 0, 400, 405, 0)
    assert cell is None
    assert pws.deletion_counts["n_measure_cells_dropped_too_narrow"] == 1


def test_steered_split_rejections_are_counted_by_reason():
    counts: dict[str, int] = {}
    me._select_steered_splits([(0, 0, 400, [])], shortfall=1, median_w=200.0,
                              counts=counts)
    assert counts["n_steered_splits_rejected_no_barline_ink"] == 1

    counts = {}
    me._select_steered_splits([(0, 0, 600, [200, 400])], shortfall=1,
                              median_w=200.0, counts=counts)
    assert counts["n_steered_splits_rejected_would_overshoot"] == 1

    counts = {}
    me._select_steered_splits([(0, 0, 400, [395])], shortfall=1,
                              median_w=200.0, counts=counts)
    assert counts["n_steered_splits_rejected_sliver_piece"] == 1


# ─── the whole pass ─────────────────────────────────────────────────────────


def test_an_immaculate_page_records_an_empty_census():
    """A key is ABSENT when its site never fired, and that is the honest
    reading — not zero-filled, because a zero would be indistinguishable from
    a site that no longer exists. This synthetic page carries nothing but
    staff lines and five clean barlines, so nothing is discarded."""
    pws = me.detect_barlines(_orchestral_page())
    assert len(pws.barlines) == 5
    assert pws.deletion_counts == {}


def test_detect_barlines_records_a_census_when_there_is_junk_to_drop():
    """The same page plus the three shapes a real one carries: a wide blob, a
    pair of columns closer together than a bar can be, and a stem column that
    aligns across the staves without crossing the gaps."""
    pws = me.detect_barlines(_page_with_junk())
    counts = pws.deletion_counts
    assert counts, "detect_barlines recorded nothing at all"
    assert counts.get("n_barline_components_dropped_too_wide", 0) >= 1
    assert counts.get("n_barline_candidates_dropped_too_close_on_staff", 0) >= 1


def test_the_census_does_not_double_when_detect_barlines_re_runs():
    """`detect_barlines` resets `pws.barlines` and is re-entered whenever
    `extract_measures` finds the list empty, so its counters must reset with
    them. A census that disagrees with the list it describes is worse than no
    census.

    This is also the anti-drift test for `_DETECT_BARLINES_COUNTER_KEYS`: a
    counter added inside `detect_barlines` and not listed there doubles here.
    """
    pws = _page_with_junk()
    once = dict(me.detect_barlines(pws).deletion_counts)
    assert once, (
        "vacuous: the fixture records nothing, so nothing could double")
    twice = dict(me.detect_barlines(pws).deletion_counts)
    assert once == twice, (
        "these keys doubled on a second pass — add them to "
        "_DETECT_BARLINES_COUNTER_KEYS: "
        + repr({k: (once.get(k), twice.get(k))
                for k in twice if once.get(k) != twice.get(k)}))
    assert set(once) <= me._DETECT_BARLINES_COUNTER_KEYS


def test_extract_measures_records_into_the_same_census():
    pws = _orchestral_page()
    before = dict(me.detect_barlines(pws).deletion_counts)
    me.extract_measures(pws)
    after = pws.deletion_counts
    assert set(before) <= set(after), "extract_measures clobbered the census"
    assert after.get("n_barlines_dropped_at_system_edge", 0) >= 1
