"""ROADMAP 2.284b -- arcs claim only their own pixels (`arc_claim.claim_pixels`); dynamic letters claim page-wide sparing the note marks
(`gather.DYNAMIC_SPARES`). Pure tests (flag `OMR_PAGE_LEDGER_OWNS`); the real-page tests are `test_arcs_dynamics_real_page_2_284b.py` (slow)."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from tools.omr.staged import arc_claim as AC


def _res(*masks):
    return SimpleNamespace(masks=list(masks), scale=1.0)


TRACE = {x: (10.0, 11.0) for x in range(0, 60)}          # a flat curve at page y 10-11, x 0..59


def test_a_slur_stroke_is_claimed_whole_and_its_pixels_counted():
    slur = (np.ones((2, 60), bool), 0, 10)               # lies on the trace
    got = AC.claim_pixels(_res(slur), (0, 0, 100, 100), 1.0, TRACE, 10.0, [])
    assert got["claimed"] == [(0, 1.0)] and got["own_px"] == 120 and got["crossings"] == []


def test_a_neighbour_cells_head_box_is_skipped_by_page_position():
    # the head's pixels fused into the slur stroke: 20 of the stroke's 120 px lie inside a head box another cell boxed
    slur = (np.ones((2, 60), bool), 0, 10)
    head = ("glyph/2/0/9/15/4", (40.0, 8.0, 59.0, 13.0))
    got = AC.claim_pixels(_res(slur), (0, 0, 100, 100), 1.0, TRACE, 10.0, [head])
    # the stroke holds ALL the head box's ink: a crossing -- marked with its own pixels, never taken
    assert got["claimed"] == []
    assert got["crossings"] == [{"stroke": 0, "own_px": 82, "box": head[0], "box_share": 1.0}]


def test_a_stroke_holding_a_sliver_of_a_box_stays_the_arcs():
    # the head has its own blob stroke (the cell map cut it); the slur only grazes the box corner
    slur = (np.ones((2, 60), bool), 0, 10)
    blob = (np.ones((12, 12), bool), 44, 12)              # page x 44..55, y 12..23
    head = ("glyph/h", (44.0, 11.0, 56.0, 24.0))
    got = AC.claim_pixels(_res(slur, blob), (0, 0, 100, 100), 1.0, TRACE, 10.0, [head])
    assert [o for o, _ in got["claimed"]] == [0] and got["crossings"] == []
    assert got["claimed_px_in_marks"] == 12              # the grazed row inside the box is counted, visible
    # the blob itself never lies on the trace: not the arc's
    assert 1 not in [o for o, _ in got["claimed"]]


def test_without_mark_boxes_the_claim_is_the_old_stroke_claim():
    slur = (np.ones((2, 60), bool), 0, 10)
    stem = (np.ones((40, 2), bool), 70, 0)
    res = _res(slur, stem)
    old = AC.claim_strokes(res, (0, 0, 100, 100), 1.0, TRACE, 10.0)
    new = AC.claim_pixels(res, (0, 0, 100, 100), 1.0, TRACE, 10.0, [])
    assert [o for o, _ in old] == [o for o, _ in new["claimed"]] == [0]


def test_a_dynamic_claim_spares_note_family_boxes():
    from tools.omr.staged import gather as G
    for cls in ("noteheadBlackOnLine", "stem", "flag8thUp", "beam", "restQuarter", "accidentalFlat", "augmentationDot", "ledgerLine"):
        assert cls.startswith(G.DYNAMIC_SPARES), cls
    for cls in ("dynamicP", "dynamicF", "staff", "slur", "brace"):
        assert not cls.startswith(G.DYNAMIC_SPARES), cls


def test_the_arc_skip_set_keeps_the_consumer_and_column_boxes_out():
    from tools.omr.staged import gather as G
    from tools.omr.staged.arcs_system import PROTECTED_PREFIXES
    skip = tuple(p for p in PROTECTED_PREFIXES if p not in G.ARC_SKIP_NOT)
    for cls in ("noteheadBlackInSpace", "ledgerLine", "augmentationDot", "dynamicF", "fermataAbove"):
        assert cls.startswith(skip), cls
    for cls in ("stem", "beam", "flag8thUp", "barlineSingle", "slur", "tie"):
        assert not cls.startswith(skip), cls
