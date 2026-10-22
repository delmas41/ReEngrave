"""Reading the bracket at a system's left edge (tools/omr/bracket_reader.py).

Synthetic pages: staves are five horizontal rules; a "bracket" is a thick
vertical rule drawn just left of where the staff lines start, spanning exactly
the staves of its block; the "systemic barline" is a thin rule spanning the
whole system.

The case that matters is the one the incumbent CANNOT read: a page whose
interior barlines cross every gap, so `gap_bridging_counts` sees no boundary at
all, while the printed brackets state one.  That is `Beethoven 5 p.38 system 0`
in miniature — the page
`benchmarks/omr-bracket-stability-2026-09/FINDINGS.md` §1a diagnoses — except
that here the brackets DO stop, which on that Litolff page they do not.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.omr.bracket_reader import (
    covered_staves,
    is_rule,
    read_brackets,
    strokes_at_left_edge,
)
from tools.omr.types import Staff

W, H = 1200, 1400
X0, X1 = 200, 1100
LINE_SPACING = 12


def _blank() -> np.ndarray:
    return np.full((H, W), 255, np.uint8)


def _draw_staff(img: np.ndarray, top: int) -> list[int]:
    ys = [top + LINE_SPACING * i for i in range(5)]
    for y in ys:
        img[y:y + 2, X0:X1] = 0
    return ys


def _vrule(img: np.ndarray, x: int, y_top: int, y_bot: int, width: int) -> None:
    img[y_top:y_bot + 1, x:x + width] = 0


def _staves(groups: list[list[int]]) -> list[Staff]:
    return [Staff(page_index=0, staff_index=i, line_ys=ys, x_start=X0, x_end=X1)
            for i, ys in enumerate(groups)]


def _page(tops: list[int], blocks: list[tuple[int, int]], *,
          systemic_barline: bool = True,
          interior_barlines: bool = True) -> tuple[np.ndarray, list[Staff]]:
    """A system with a bracket per block.

    `interior_barlines` draws bars through EVERY gap, which is what makes the
    incumbent's crossing-count rule blind here.
    """
    img = _blank()
    groups = [_draw_staff(img, t) for t in tops]
    top_y, bot_y = groups[0][0], groups[-1][-1] + 1
    # brackets: thick, 8 px left of the staff start
    for first, last in blocks:
        _vrule(img, X0 - 14, groups[first][0], groups[last][-1] + 1, 8)
    if systemic_barline:                       # thin, 2 px left of the staves
        _vrule(img, X0 - 3, top_y, bot_y, 3)
    if interior_barlines:
        for k in range(6):
            _vrule(img, X0 + 100 + k * 130, top_y, bot_y, 3)
    return img, _staves(groups)


TOPS = [100, 220, 340, 500, 620, 740]          # 6 staves, wider gap at 2|3


# ── the case the incumbent cannot read ───────────────────────────────────────

def test_a_bracket_that_stops_states_the_boundary():
    img, staves = _page(TOPS, [(0, 2), (3, 5)])
    r = read_brackets(img, staves)
    assert r["verdict"] == "partial"
    assert r["blocks"] == [[0, 1, 2], [3, 4, 5]]
    assert r["boundaries"] == [2]
    # and the gaps INSIDE a bracket are asserted NOT to be boundaries — the
    # half a boundary-only reading throws away
    assert r["interior"] == [0, 1, 3, 4]


def test_the_incumbent_is_blind_to_that_page():
    """RED-side control.  If the crossing-count rule ever starts reading this
    page, the test above has stopped testing anything and this fails loudly.
    """
    from tools.omr import system_grouping as sg
    img, staves = _page(TOPS, [(0, 2), (3, 5)])
    counts = sg.gap_bridging_counts(img, staves)
    inner = [c for c in counts if c >= 0]
    threshold = float(np.median(inner)) * sg.GROUP_BOUNDARY_RATIO
    assert all(c >= threshold for c in counts), counts


def test_three_blocks_state_two_boundaries():
    img, staves = _page(TOPS, [(0, 1), (2, 3), (4, 5)])
    r = read_brackets(img, staves)
    assert r["blocks"] == [[0, 1], [2, 3], [4, 5]]
    assert r["boundaries"] == [1, 3]


# ── abstentions ──────────────────────────────────────────────────────────────

def test_one_bracket_over_the_whole_system_states_no_boundary():
    """Litolff and Simrock print exactly this, and it is not a failure to read
    it — the page states that there is no BRACKET boundary, and says nothing
    about the instrument families."""
    img, staves = _page(TOPS, [(0, 5)])
    r = read_brackets(img, staves)
    assert r["verdict"] == "spanning_only"
    assert r["boundaries"] == []
    assert r["blocks"] is None


def test_a_bare_left_edge_reads_nothing():
    img, staves = _page(TOPS, [], systemic_barline=False)
    r = read_brackets(img, staves)
    assert r["verdict"] == "no_rule"
    assert r["boundaries"] == []


# ── the two measurement traps the module documents ───────────────────────────

def test_the_staff_lines_do_not_become_one_staff_brackets():
    """Trap 1.  The 0.6-spacing closing bridges the white between two staff
    lines, so every column inside the staff produces one solid run per staff.
    `gap_bridging_counts` never sees this (it looks only between staves); a
    left-edge reader does, and the artefact is shaped exactly like a bracket
    over a single staff.  The gap-crossing filter is what removes it.
    """
    img, staves = _page(TOPS, [(0, 5)])
    strokes, _geom = strokes_at_left_edge(img, staves)
    for st in strokes:
        assert len(covered_staves(st, staves)) >= 2, st
    # The artefact is really there, so the filter is not guarding an empty
    # case: with the filter off and nothing beside it to be absorbed into, one
    # stroke per staff appears.
    bare, _bs = _page(TOPS, [], systemic_barline=False)
    unfiltered, _g = strokes_at_left_edge(bare, staves, require_gap_crossing=False)
    assert sum(len(covered_staves(st, staves)) == 1
               for st in unfiltered) == len(staves)


def test_the_artefact_does_not_corrupt_the_rule_it_stands_beside():
    """The same trap, one step downstream, and the reason the filter runs at
    the RUN level rather than the stroke level.

    The staff-line artefact is x-adjacent to the systemic barline and fully
    contained in its run, so containment linking absorbs it; the stroke's
    median y_top/y_bot then follows the many short runs instead of the one
    long one.  Before the run-level filter this synthetic page reported a
    single stroke "covering staves 2-3" — a confident, wrong two-staff
    bracket on a page with one bracket over everything.
    """
    img, staves = _page(TOPS, [(0, 5)])
    strokes, _g = strokes_at_left_edge(img, staves)
    assert strokes, "the bracket and the barline should both be found"
    for st in strokes:
        assert covered_staves(st, staves) == list(range(len(staves))), st


def test_a_thick_blob_is_not_a_rule():
    """A beam or a clef body reaching left of the staff is straight-ish and
    tall, and is rejected on WIDTH: measured over 380 strokes on five
    publishers, printed rules run 0.28-1.62 staff spacings and the junk
    2.2-3.5."""
    img, staves = _page(TOPS, [(0, 5)])
    _vrule(img, X0 - 60, staves[1].top_y, staves[3].bottom_y, 40)
    strokes, _g = strokes_at_left_edge(img, staves)
    blobs = [s for s in strokes if s.thickness_px >= 40]
    assert blobs, "the blob should be found as a stroke"
    assert not any(is_rule(s) for s in blobs)
    # and it must not reach the reading
    assert read_brackets(img, staves)["verdict"] == "spanning_only"


def test_reading_a_two_staff_system_does_not_crash():
    img, staves = _page([100, 220], [(0, 1)])
    assert read_brackets(img, staves)["verdict"] in ("spanning_only", "no_rule")
