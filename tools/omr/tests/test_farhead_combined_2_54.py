"""ROADMAP 2.54 (Sean, 2026-10-01, "combine that way") -- a far head's
position combines geometry and the rung count: AGREE -> take it; DISAGREE
-> the head's OWN printed-ledger evenness decides (uneven -> rungs, even
-> geometry, threshold from the measured split on the 2.44c truth set,
`benchmarks/omr-local-staff-2026-09/ledger_breakdown_r3.py` Table D:
geometry-WRONG heads median 0.419, geometry-RIGHT heads median 0.105);
neither reader can settle it -> UNREAD, counted (CLAUDE.md rule 8).

RED-first: `tools.omr.annotate.ledger_grid` carries no
`combine_farhead_position`/`farhead_gap_evenness` before this lane --
confirmed by `git stash` of `ledger_grid.py` alone, same session
(`ImportError: cannot import name 'combine_farhead_position'`).
"""
from __future__ import annotations

import pytest

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    FARHEAD_EVEN_UNEVEN_THRESHOLD,
    FARHEAD_MIN_RUNGS_FOR_EVENNESS,
    FARHEAD_NEAR_BOUNDARY_RESIDUAL,
    combine_farhead_position,
    farhead_gap_evenness,
)

SPACING = 16.0


# ─────────────────────────────────────────────────────────────────────────
# farhead_gap_evenness -- the pure measure
# ─────────────────────────────────────────────────────────────────────────

def test_evenness_none_below_min_rungs():
    """One rung has no gap to measure at all -- an ABSENCE, not a false
    0.0 'perfectly even' claim."""
    assert farhead_gap_evenness([100.0], SPACING) is None
    assert farhead_gap_evenness([], SPACING) is None


def test_evenness_perfectly_even():
    # two gaps, both exactly one spacing -> deviation 0.0
    rungs = [100.0, 100.0 - SPACING, 100.0 - 2 * SPACING]
    assert farhead_gap_evenness(rungs, SPACING) == pytest.approx(0.0)


def test_evenness_uneven_measured_example():
    # Litolff staff/3/0/0: ledgers 18 / 13 / 20 px against a 15.75 spacing
    # (DECISIONS 2026-09-30) -- real measured unevenness. Three gaps (18,
    # 13, 20) against 15.75: deviations 0.143 / 0.175 / 0.270 -- the max,
    # 0.270, clears FARHEAD_EVEN_UNEVEN_THRESHOLD (0.26).
    sp = 15.75
    rungs = [100.0, 100.0 - 18.0, 100.0 - 18.0 - 13.0,
             100.0 - 18.0 - 13.0 - 20.0]
    dev = farhead_gap_evenness(rungs, sp)
    assert dev is not None and dev > FARHEAD_EVEN_UNEVEN_THRESHOLD


def test_evenness_zero_spacing_is_none():
    assert farhead_gap_evenness([100.0, 84.0], 0.0) is None


# ─────────────────────────────────────────────────────────────────────────
# combine_farhead_position -- the four branches
# ─────────────────────────────────────────────────────────────────────────

def test_agree_takes_the_shared_value():
    rungs = [100.0, 100.0 - SPACING, 100.0 - 2 * SPACING]  # even
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.1,
        rungs_pos=-6, rungs_y=rungs, spacing=SPACING,
    )
    assert out == {"position": -6, "branch": "agree",
                   "max_gap_deviation": pytest.approx(0.0)}


def test_disagree_uneven_takes_rungs():
    sp = 15.75
    rungs = [100.0, 100.0 - 18.0, 100.0 - 18.0 - 13.0,
             100.0 - 18.0 - 13.0 - 20.0]  # uneven, measured (see above)
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.1,
        rungs_pos=-8, rungs_y=rungs, spacing=sp,
    )
    assert out["branch"] == "disagree_rungs"
    assert out["position"] == -8
    assert out["max_gap_deviation"] > FARHEAD_EVEN_UNEVEN_THRESHOLD


def test_disagree_even_takes_geometry():
    rungs = [100.0, 100.0 - SPACING, 100.0 - 2 * SPACING]  # even
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.1,
        rungs_pos=-8, rungs_y=rungs, spacing=SPACING,
    )
    assert out["branch"] == "disagree_geometry"
    assert out["position"] == -6
    assert out["max_gap_deviation"] <= FARHEAD_EVEN_UNEVEN_THRESHOLD


def test_too_few_rungs_is_unread():
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.1,
        rungs_pos=-8, rungs_y=[100.0], spacing=SPACING,  # 1 rung, no gap
    )
    assert out == {"position": None, "branch": "unread",
                   "max_gap_deviation": None}


def test_rungs_undecided_and_geometry_near_boundary_is_unread():
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=FARHEAD_NEAR_BOUNDARY_RESIDUAL + 0.01,
        rungs_pos=None, rungs_y=[], spacing=SPACING,
    )
    assert out["branch"] == "unread"
    assert out["position"] is None


def test_rungs_undecided_but_geometry_confident_takes_geometry():
    """Rungs abstained, but geometry is nowhere near a rounding boundary
    and the head's own rungs (even though the FINAL rung step abstained)
    were found evenly -- nothing to disagree WITH, geometry stands."""
    rungs = [100.0, 100.0 - SPACING, 100.0 - 2 * SPACING]
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.05,
        rungs_pos=None, rungs_y=rungs, spacing=SPACING,
    )
    assert out["branch"] == "disagree_geometry"
    assert out["position"] == -6


def test_rungs_undecided_uneven_and_not_near_boundary_is_unread():
    """Evenness says 'trust rungs', but rungs has no answer to give --
    unread, never a guess."""
    sp = 15.75
    rungs = [100.0, 100.0 - 18.0, 100.0 - 18.0 - 13.0,
             100.0 - 18.0 - 13.0 - 20.0]  # uneven (see above)
    out = combine_farhead_position(
        geom_pos=-6, geom_residual=0.05,
        rungs_pos=None, rungs_y=rungs, spacing=sp,
    )
    assert out["branch"] == "unread"
    assert out["position"] is None


def test_agree_requires_a_decided_rungs_position_not_just_equal_none():
    """`rungs_pos=None` is never 'agreement' with a `geom_pos=None` --
    not reachable in practice (`geom_pos` is always decided for a far
    head, the gate that puts it in this population), but the branch
    logic must not special-case None == None as 'agree'."""
    out = combine_farhead_position(
        geom_pos=None, geom_residual=None,
        rungs_pos=None, rungs_y=[], spacing=SPACING,
    )
    assert out["branch"] == "unread"
