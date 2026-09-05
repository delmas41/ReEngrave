"""The three tests that separate a hairpin from everything else in the band.

Each is pinned against a synthetic shape whose answer is known by construction,
because the real-page numbers in
`benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md` are counts against counts and
cannot pin behaviour.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.hairpin_detection import (
    MAX_COMPONENT_GROWTH,
    SPAN_CLASSES,
    blank_point_detections,
    detect_hairpins,
    measure_component,
    staves_from_result,
)

SP = 20.0          # staff space, px


def _wedge(width=200, opening=20, flip=False) -> np.ndarray:
    """Two straight arms meeting at a point — a hairpin."""
    h = opening + 6
    m = np.zeros((h, width), np.uint8)
    for x in range(width):
        frac = x / (width - 1)
        if flip:
            frac = 1.0 - frac
        half = frac * opening / 2.0
        mid = h / 2.0
        m[int(round(mid - half)):int(round(mid - half)) + 2, x] = 255
        m[int(round(mid + half)):int(round(mid + half)) + 2, x] = 255
    return m


def _arc(width=200, rise=20) -> np.ndarray:
    """One curved stroke — a slur."""
    h = rise + 8
    m = np.zeros((h, width), np.uint8)
    for x in range(width):
        t = x / (width - 1)
        y = int(round((h - 4) - rise * 4 * t * (1 - t)))
        m[y:y + 3, x] = 255
    return m


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------


def test_a_wedge_opens_and_a_stroke_does_not():
    """⚠️ The open-extent test ALONE is useless — 302 of 312 real band
    components clear it — but it is still necessary: a stroke never opens."""
    w = measure_component(_wedge(), SP)
    a = measure_component(_arc(), SP)
    assert w["open_spaces"] > 0.5
    assert a["open_spaces"] < 0.3, "an arc's per-column extent is its thickness"


def test_a_wedges_outlines_are_straight_and_an_arcs_are_not():
    """The test that does the separating: a hairpin is two STRAIGHT arms; a
    slur is one curved stroke, so neither of its outlines fits a line."""
    assert measure_component(_wedge(), SP)["outline_rms_spaces"] < 0.10
    assert measure_component(_arc(), SP)["outline_rms_spaces"] > 0.10


def test_the_direction_falls_out_of_the_same_measurement():
    """Apex left is a crescendo — no extra reading, and it is the one thing the
    class label used to supply."""
    assert measure_component(_wedge(), SP)["kind"] == "crescendo"
    assert measure_component(_wedge(flip=True), SP)["kind"] == "diminuendo"


def test_too_few_columns_abstains():
    assert measure_component(np.zeros((10, 3), np.uint8), SP) is None


# --------------------------------------------------------------------------
# Isolation — Sean's rule, and the sharpest of the three
# --------------------------------------------------------------------------


def _page_with(mask, at=(200, 300), attach_stem=False):
    page = np.zeros((600, 900), np.uint8)
    y, x = at
    page[y:y + mask.shape[0], x:x + mask.shape[1]] = mask
    if attach_stem:
        # A stem running up out of the band, as a beam would have. ⚠️ It must
        # actually TOUCH the wedge — an earlier version of this fixture stopped
        # two pixels short and the test passed for the wrong reason, reporting
        # the isolation rule broken when the fixture was.
        page[20:y + mask.shape[0] // 2 + 2, x + 10:x + 13] = 255
    return page


def _staves():
    return [{"index": 0, "top": 100.0, "bottom": 180.0, "spacing": SP}]


def test_an_isolated_wedge_is_found():
    page = _page_with(_wedge())
    got = detect_hairpins(page, _staves())
    assert len(got) == 1 and got[0].kind == "crescendo"
    assert got[0].staff_index == 0


def test_the_same_wedge_attached_to_a_stem_is_rejected():
    """⚠️ A beam is always connected to something — its stems — and a hairpin is
    connected to nothing. On a real page the attached components' full extent is
    3248x their own at p75, against 1.0x at p50, with nothing between.
    """
    page = _page_with(_wedge(), attach_stem=True)
    assert detect_hairpins(page, _staves()) == []


def test_isolation_is_judged_on_the_whole_page_not_the_band():
    """⚠️ The band crop severs a beam from its stems and makes it look exactly
    as isolated as a hairpin. Passing only the band would pass the shape."""
    page = _page_with(_wedge(), attach_stem=True)
    band_only = page[190:260, :].copy()
    # the same ink, judged inside a crop that excludes the stem, would survive
    assert measure_component(_wedge(), SP)["outline_rms_spaces"] < 0.10
    # ...but whole-page isolation rejects it
    assert detect_hairpins(page, _staves()) == []
    assert band_only.any()


def test_an_arc_in_the_band_is_rejected_on_shape():
    assert detect_hairpins(_page_with(_arc()), _staves()) == []


# --------------------------------------------------------------------------
# The band, and the blanking
# --------------------------------------------------------------------------


def test_ink_above_the_band_is_not_searched():
    """A hairpin belongs below its staff — 8 of 8 in the engraved page truth."""
    page = _page_with(_wedge(), at=(40, 300))     # above the staff
    assert detect_hairpins(page, _staves()) == []


def test_blanking_erases_a_notehead_but_not_a_slur():
    """⚠️ A slur, tie or beam box is mostly the PAPER its arc crosses, so
    blanking it erases whatever stands under it — here, the hairpin. Same rule
    and the same trap as `direction_text`."""
    ink = np.full((100, 100), 255, np.uint8)
    out = blank_point_detections(
        ink, [(10, 10, 8, 8, "noteheadBlackOnLine"), (0, 0, 90, 90, "slur")], SP)
    assert out[12, 12] == 0, "the notehead should be erased"
    assert out[60, 60] == 255, "the slur's box must NOT be erased"


@pytest.mark.parametrize("cls", sorted(SPAN_CLASSES))
def test_every_span_class_is_spared(cls):
    ink = np.full((60, 60), 255, np.uint8)
    out = blank_point_detections(ink, [(0, 0, 50, 50, cls)], SP)
    assert out.all()


def test_a_wide_box_is_spared_even_with_an_unknown_class():
    ink = np.full((60, 300), 255, np.uint8)
    out = blank_point_detections(ink, [(0, 0, 280, 50, "somethingNew")], SP)
    assert out.all(), "width alone must spare a span, not only the class list"


def test_growth_threshold_sits_in_the_measured_gap():
    """1.0x against 3248x — any value in between gives the same answer."""
    assert 1.0 < MAX_COMPONENT_GROWTH < 100.0


def test_staves_from_result_needs_five_lines_and_a_spacing():
    ok = {"pages": [{"systems": [{"staves": [
        {"staff_index": 3, "staff_geometry": {
            "line_ys_page": [10, 20, 30, 40, 50], "line_spacing_px": 10.0}}]}]}]}
    assert staves_from_result(ok) == [
        {"index": 3, "top": 10.0, "bottom": 50.0, "spacing": 10.0}]
    bad = {"pages": [{"systems": [{"staves": [
        {"staff_index": 0, "staff_geometry": {"line_ys_page": [10, 20]}}]}]}]}
    assert staves_from_result(bad) == []


def test_no_staves_means_no_hairpins_not_a_crash():
    assert detect_hairpins(np.zeros((50, 50), np.uint8), []) == []
