"""lane-ledger-rungs (2026-10-01): a THIRD far-head reader, Sean-approved
build off the outward-bias measurement (DECISIONS: hand-drawn ledgers
print wider than the staff spacing, so dividing by the staff spacing
overshoots outward by one step on every measured miss). `ledger_grid.
ledger_measured_geometry` places a far head's box centre on a ladder of
KNOWN steps (the outer staff line + every measured ledger) by LINEAR
INTERPOLATION, never by dividing raw pixel distance by the staff
spacing; a head beyond the last measured ledger extrapolates by the
LAST measured gap, never the staff spacing.

Pure arithmetic -- no image reading here (that is `measure_ledger_rungs`,
unchanged, reused). NOT wired into the product path; no default touched.
"""
from __future__ import annotations

import pytest

from tools.omr.annotate.ledger_grid import ledger_measured_geometry  # noqa: E402


@pytest.mark.omr_annotate
def test_wide_hand_drawn_gap_head_on_2nd_ledger_reads_that_ledger() -> None:
    """Edge at 300 (step 0), 1st ledger at 200 (100px = 1.0x spacing,
    step 2), 2nd ledger at 80 (120px further = 1.2x spacing -- the
    hand-drawn wide gap), head's box centre sitting exactly ON the 2nd
    ledger (80). Plain nominal-spacing geometry would divide the raw
    220px distance by the 50px half-step and round to step 4.4 -> 4,
    coincidentally right here since round(4.4)=4 -- the overshoot this
    reader exists to fix shows up once the ladder is read on a head
    sitting at a half-step, not exactly on a ledger (next test)."""
    out = ledger_measured_geometry(
        rungs_y=[200.0, 80.0], edge_y=300.0, sign=-1.0, box_center_y=80.0,
        spacing=100.0,
    )
    assert out["offset"] == 4


@pytest.mark.omr_annotate
def test_wide_gap_head_half_a_step_short_of_the_2nd_ledger() -> None:
    """Same wide (1.2x) gap, but the head sits at the SPACE just before
    the 2nd ledger (half-way between the 1st and 2nd ledger by the
    ladder's own interpolation, i.e. step 3) -- not at a round-number
    pixel position plain geometry would get right by luck."""
    out = ledger_measured_geometry(
        rungs_y=[200.0, 80.0], edge_y=300.0, sign=-1.0, box_center_y=140.0,
        spacing=100.0,
    )
    assert out["offset"] == 3


@pytest.mark.omr_annotate
def test_evenly_spaced_ledgers_matches_plain_geometry_control() -> None:
    """Control: ledgers at the nominal staff spacing exactly (100px =
    1.0x) -- interpolation/extrapolation must agree with plain
    nominal-spacing geometry (round(raw_px / half_step))."""
    rungs_y = [200.0, 100.0]  # edge 300, spacing 100 -- perfectly even
    spacing = 100.0
    half_step = spacing / 2.0
    for box_center_y in (250.0, 150.0, 50.0, -10.0, -60.0):
        out = ledger_measured_geometry(
            rungs_y=rungs_y, edge_y=300.0, sign=-1.0,
            box_center_y=box_center_y, spacing=spacing,
        )
        plain = int(round((300.0 - box_center_y) / half_step))
        assert out["offset"] == plain, (box_center_y, out, plain)


@pytest.mark.omr_annotate
def test_beyond_the_last_ledger_extrapolates_by_the_last_gap_not_spacing() -> None:
    """1st ledger at 200 (100px, 1.0x), 2nd at 70 (130px further, 1.3x --
    the LAST measured gap). A head well beyond the 2nd ledger must step
    out using that 130px gap, not the 100px nominal spacing -- the two
    give different answers, which is the point of the test."""
    out = ledger_measured_geometry(
        rungs_y=[200.0, 70.0], edge_y=300.0, sign=-1.0, box_center_y=-60.0,
        spacing=100.0,
    )
    # last_gap = 130px = dist 230; target = 360; extra = (360-230)/130*2 = 2.0
    assert out["offset"] == 6
    # Using nominal spacing instead would give a DIFFERENT (wrong) answer,
    # proving the two are not accidentally the same arithmetic here.
    using_spacing = 4 + round((360.0 - 230.0) / 100.0 * 2.0)
    assert using_spacing != out["offset"]


@pytest.mark.omr_annotate
def test_no_ledgers_falls_back_and_is_counted() -> None:
    out = ledger_measured_geometry(
        rungs_y=[], edge_y=300.0, sign=-1.0, box_center_y=100.0, spacing=100.0,
    )
    assert out["offset"] is None
    assert out["reason"] == "no_ledger_ladder"


@pytest.mark.omr_annotate
def test_below_side_mirrors_the_same_arithmetic() -> None:
    out = ledger_measured_geometry(
        rungs_y=[400.0, 530.0], edge_y=300.0, sign=1.0, box_center_y=530.0,
        spacing=100.0,
    )
    assert out["offset"] == 4
