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
    # the head's pixels fused into the slur stroke (r2: a head is tall, most of its ink is OFF the curve): a long slur, a head 18 x 18 px on it
    trace = {x: (10.0, 11.0) for x in range(0, 200)}
    m = np.zeros((18, 200), bool)
    m[2:4, :] = True
    m[:, 100:118] = True
    head = ("glyph/2/0/9/15/4", (100.0, 8.0, 118.0, 26.0))
    got = AC.claim_pixels(_res((m, 0, 8)), (0, 0, 300, 100), 1.0, trace, 10.0, [head])
    # the stroke holds ALL the head box's ink: a crossing -- marked with its own pixels, never taken
    assert got["claimed"] == [] and got["line_boxes"] == []
    assert len(got["crossings"]) == 1 and got["crossings"][0]["box"] == head[0] and got["crossings"][0]["box_share"] == 1.0
    assert got["crossings"][0]["box_on_line"] < AC.BOX_ON_LINE_MIN


def test_a_ledger_box_lying_along_the_arc_is_the_arcs_own_ink():
    # Litolff p4 tile 3 (Sean 2026-11-10: "part of an arc"): a `ledgerLine` box that is the arc's own thick stretch
    trace = {x: (10.0, 11.0) for x in range(0, 200)}
    slur = (np.ones((2, 200), bool), 0, 10)
    led = ("glyph/4/0/7/1/10", (60.0, 9.0, 100.0, 13.0))
    got = AC.claim_pixels(_res(slur), (0, 0, 300, 100), 1.0, trace, 10.0, [led])
    assert got["crossings"] == [] and [o for o, _ in got["claimed"]] == [0]
    assert got["line_boxes"] and got["line_boxes"][0][0] == led[0] and got["line_boxes"][0][1] >= AC.BOX_ON_LINE_MIN
    # the control that can fail: r6's rule (`line_boxes_free=False`) keeps the arc's ink as a crossing and claims nothing
    old = AC.claim_pixels_on(_res(slur), (0, 0, 300, 100), 1.0, lambda px, py: AC._on_curve(px, py, trace, 10.0), [led], 0.5, False)
    assert old["claimed"] == [] and len(old["crossings"]) == 1


def test_a_letter_crossing_the_arc_stays_a_crossing():
    # tiles 1 and 8 (p, flat: right): most of the mark's ink is off the curve
    trace = {x: (10.0, 11.0) for x in range(0, 400)}
    m = np.zeros((30, 400), bool)
    m[2:4, :] = True
    m[:, 100:112] = True
    flat = ("glyph/f", (100.0, 8.0, 112.0, 38.0))
    got = AC.claim_pixels(_res((m, 0, 8)), (0, 0, 500, 100), 1.0, trace, 10.0, [flat])
    assert got["claimed"] == [] and len(got["crossings"]) == 1


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


def test_a_hairpin_claims_its_arm_pixels_by_the_same_rule():
    from tools.omr.staged import hairpin_reach as HR
    bb = [0.0, 0.0, 400.0, 40.0]
    segs = HR.arms("crescendo", bb)
    on = HR.on_arms_fn(segs, bb, HR.band_px(10.0))
    # a stroke along the lower arm (from the left point at y 20 to the right end at y 40) with a small blob fused at its right end
    m = np.zeros((60, 401), bool)
    for x in range(401):
        m[int(round(20 + x * 20 / 400.0)), x] = True
    m[42:46, 370:401] = True
    res = _res((m, 0, 0))
    assert [o for o, _ in AC.claim_pixels_on(res, (0, 0, 500, 100), 1.0, on, [], HR.ON_ARMS_SHARE_MIN)["claimed"]] == [0]
    # a box that holds the blob (most of its ink is off the arm): the stroke is a crossing, marked not taken
    got = AC.claim_pixels_on(res, (0, 0, 500, 100), 1.0, on, [("glyph/h", (370.0, 36.0, 401.0, 50.0))], HR.ON_ARMS_SHARE_MIN)
    assert got["claimed"] == [] and len(got["crossings"]) == 1


# ---- r2: a printed dynamic is ONE mark (Sean 2026-11-10: ff, sf claimed letter by letter) ----------------------------------------------------

def _runs(letters, spacing=15.75):
    from tools.omr.staged import claims as CL
    from tools.omr.staged.adjudicators.text import DYNAMIC_WORDS
    return CL.spell_letter_runs(letters, spacing, DYNAMIC_WORDS)


def test_ff_joins_though_another_staffs_letter_stands_between_in_x():
    # Litolff p10 tile 4: the two f of an ff (x 1736 and 1754) with an f of the STAFF ABOVE at x 1741 between them in x order
    L = [([1735.9, 2571.3, 1769.9, 2610.7], "f", 1), ([1741.3, 2450.0, 1775.0, 2484.0], "f", 2), ([1753.9, 2572.1, 1785.8, 2613.8], "f", 3)]
    runs = _runs(L)
    spelled = [r for r in runs if r["text"] == "ff"]
    assert len(spelled) == 1 and spelled[0]["read"] and set(spelled[0]["rows"]) == {1, 3}
    # the letter of the other staff stays its own lone letter (r6 compared each slot with the previous one in x order: that letter broke the pair)
    assert [r["rows"] for r in runs if r["why"] == "lone_letter"] == [[2]]


def test_the_two_f_of_an_ff_are_not_twins_but_one_f_boxed_twice_is():
    from tools.omr.staged import claims as CL
    assert not CL._is_twin([1736.0, 2571.0, 1770.0, 2611.0], [1754.0, 2572.0, 1786.0, 2614.0])        # centres 0.53 of a width apart
    assert CL._is_twin([1723.6, 2765.9, 1758.1, 2793.0], [1716.4, 2766.2, 1758.0, 2817.1])           # one f seen by two cells


def test_four_boxes_of_one_ff_spell_ff_not_f():
    # Litolff p10 tile 5: two f, each boxed by two cells
    L = [([1741.3, 2765.0, 1779.2, 2793.0], "f", 1), ([1723.6, 2765.9, 1758.1, 2793.0], "f", 2),
         ([1716.4, 2766.2, 1758.0, 2817.1], "f", 3), ([1734.8, 2764.9, 1779.7, 2812.7], "f", 4)]
    runs = _runs(L)
    assert [(r["text"], r["read"]) for r in runs] == [("ff", True)]


def test_a_single_slot_far_wider_than_a_letter_is_a_word_of_unknown_length_not_an_f():
    narrow = [([100.0 + 80 * i, 10.0, 134.0 + 80 * i, 50.0], "f", i) for i in range(6)]
    wide = [([1000.0, 10.0, 1075.0, 55.0], "f", 99)]
    runs = _runs(narrow + wide)
    w = [r for r in runs if 99 in r["rows"]][0]
    assert w["text"] is None and w["why"] == "wide_letter_box" and not w["read"]
    assert all(r["text"] == "f" and r["why"] == "lone_letter" for r in runs if r is not w)
