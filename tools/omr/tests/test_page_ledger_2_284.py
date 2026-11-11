"""ROADMAP 2.284 -- the page ledger owns the ink (`page_ledger`, flag `OMR_PAGE_LEDGER_OWNS`). Pure tests of the pool / apply rule and the link."""
from __future__ import annotations

import numpy as np

from tools.omr.staged import page_ledger as PL
from tools.omr.staged import stroke_owner as SO


def _ink(o, kind="vertical", box=(0, 0, 2, 40), length=2.5, thick=0.15):
    return SO.Ink(o, kind, box, length, thick, 0.3, 16.0)


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(PL.ENV, raising=False)
    assert PL.enabled()                         # landed ON 2026-11-10
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv(PL.ENV, off)
        assert not PL.enabled()
    monkeypatch.setenv(PL.ENV, "1")
    assert PL.enabled()


def test_a_neighbour_cells_copy_takes_the_one_owner():
    # cell A: the barline area claim stands on its stroke 0; cell B sees the same page ink (its stroke 3) with no claimant
    a = SO.own_strokes([_ink(0)], [SO.Claim("area-1", "barline", "barline", (0,), (), "r1", area=True)])
    b = SO.own_strokes([_ink(3)], [])
    assert a[0].family == "barline" and b[3].state == "unclaimed"
    page, cen = PL.pool({"A": a, "B": b}, {"A": {0: (7, 0.95)}, "B": {3: (7, 1.0)}}, SO.TIERS)
    assert page[7].state == "decided" and page[7].family == "barline"
    nb, ch = PL.apply(b, {3: (7, 1.0)}, page)
    assert nb[3].family == "barline" and nb[3].ordinal == 3
    assert ch == {"unclaimed:->decided:barline": 1}
    assert cen["seen_twice"] == 1


def test_a_fused_piece_keeps_its_cells_own_verdict():
    # cell B's stroke is only 60% on page stroke 7 (fused with another mark): never linked, its claims never reach the page stroke
    a = SO.own_strokes([_ink(0)], [])
    b = SO.own_strokes([_ink(3)], [SO.Claim("area-1", "barline", "barline", (3,), (), "r1", area=True)])
    page, cen = PL.pool({"A": a, "B": b}, {"A": {0: (7, 1.0)}, "B": {3: (7, 0.6)}}, SO.TIERS)
    assert page[7].state == "unclaimed"
    nb, ch = PL.apply(b, {3: (7, 0.6)}, page)
    assert nb[3].family == "barline" and not ch
    assert cen["unlinked_strokes"] == 1


def test_two_families_on_one_page_stroke_stay_contested_never_chosen():
    head = _ink(0, "blob", (0, 0, 10, 10), 0.6, 0.3)
    a = SO.own_strokes([head], [SO.Claim("gA", "dynamic", "dynamicP", (0,), (), "g1")])  # both shapes CLEAR on a small blob
    b = SO.own_strokes([_ink(5, "blob", (0, 0, 10, 10), 0.6, 0.3)], [SO.Claim("gB", "mark", "articStaccatoAbove", (5,), (), "g2")])
    page, _ = PL.pool({"A": a, "B": b}, {"A": {0: (1, 1.0)}, "B": {5: (1, 1.0)}}, SO.TIERS)
    assert page[1].state == "contested"


def test_twin_boxes_of_one_family_are_merged():
    a = SO.own_strokes([_ink(0, "blob", (0, 0, 20, 16), 1.3, 1.0)], [SO.Claim("hA", "head", "noteheadBlack", (0,), (), "g1")])
    b = SO.own_strokes([_ink(2, "blob", (0, 0, 20, 16), 1.3, 1.0)], [SO.Claim("hB", "head", "noteheadBlack", (2,), (), "g2")])
    page, _ = PL.pool({"A": a, "B": b}, {"A": {0: (4, 1.0)}, "B": {2: (4, 0.9)}}, SO.TIERS)
    assert page[4].state == "merged" and set(page[4].owners) == {"hA", "hB"}


class _Map:
    def __init__(self, masks, strokes, scale=1.0, barlines=()):
        self.masks, self.strokes, self.scale, self.barlines = masks, strokes, scale, list(barlines)


class _Res:
    def __init__(self, masks, scale=1.0):
        self.masks, self.scale = masks, scale


def test_link_finds_the_page_stroke_under_a_cell_stroke_and_its_share():
    m0 = np.zeros((10, 2), bool)
    m0[:, :] = True                                     # page stroke 0: a 2x10 vertical at page (20..21, 30..39)
    pm = _Map([(m0, 20, 30)], [object()])
    lab = PL.PageLabels(pm, (100, 100))
    # the cell starts at page (10, 25); upscale 2 (canonical = 2 x page), its reduced frame = canonical x 0.5 = page px
    cm = np.zeros((5, 2), bool)
    cm[:, :] = True                                     # the lower half of the same ink, as the cell cut it
    far = np.ones((3, 3), bool)                         # ink where the page map has none
    res = _Res([(cm, 10, 10), (far, 60, 60)], scale=0.5)
    out = PL.link_cell_strokes(res, (10.0, 25.0, 90.0, 90.0), 2.0, lab)
    assert out[0] == (0, 1.0, 0.5)                      # all its ink on page stroke 0, half of page stroke 0's ink
    assert out[1] is None


def test_carved_barline_rule_is_a_page_stroke_where_no_other_stroke_stands():
    pm = _Map([], [], barlines=[{"box": (40, 0, 42, 50)}])
    lab = PL.PageLabels(pm, (60, 60))
    rule = np.ones((20, 2), bool)
    out = PL.link_cell_strokes(_Res([(rule, 40, 10)], 1.0), (0.0, 0.0, 60.0, 60.0), 1.0, lab)
    assert out[0][:2] == (0, 1.0)                        # ordinal n_strokes + k = 0 + 0


def test_a_box_claim_from_a_cut_view_never_settles_a_stroke_another_cell_sees_whole():
    # cell A sees the stem whole, no claimant (a consumer's); cell B's padding cut it to a sliver its neighbour head box "could" own: left out
    a = SO.own_strokes([_ink(0)], [])
    b = SO.own_strokes([_ink(4, "blob", (0, 0, 3, 10), 0.6, 0.19)], [SO.Claim("hB", "head", "noteheadBlack", (4,), (), "g2")])
    assert b[4].family == "head"
    page, cen = PL.pool({"A": a, "B": b}, {"A": {0: (9, 1.0, 1.0)}, "B": {4: (9, 1.0, 0.2)}}, SO.TIERS)
    assert page[9].state == "unclaimed" and cen["cut_view_claims_left_out"] == 1
    # ... nor a register claim's centre rule on a cut edge (round 3: a barline area took a judged eighth's head) ...
    b2 = SO.own_strokes([_ink(4)], [SO.Claim("area-1", "barline", "barline", (4,), (), "r1", area=True)])
    page2, _ = PL.pool({"A": a, "B": b2}, {"A": {0: (9, 1.0, 1.0)}, "B": {4: (9, 1.0, 0.2)}}, SO.TIERS)
    assert page2[9].state == "unclaimed"
    # ... but where no cell sees the stroke whole, every view is pooled
    page3, _ = PL.pool({"A": a, "B": b2}, {"A": {0: (9, 1.0, 0.5)}, "B": {4: (9, 1.0, 0.4)}}, SO.TIERS)
    assert page3[9].family == "barline"


def test_an_arc_claims_only_its_own_traced_pixels_never_a_head_box(monkeypatch):
    from tools.omr.staged import arc_claim as AC
    from tools.omr.staged import claim_final as CF
    m = np.ones((4, 10), bool)                          # a piece lying on the trace: page x 0..9, y 0..3 (scale 1, up 1, cell at 0, 0)
    trace = {x: (0.0, 3.0) for x in range(0, 10)}
    assert AC.on_trace_share(m, 0, 0, 1.0, (0, 0, 0, 0), 1.0, trace, 10.0) == 1.0
    # the rim of a hollow head: the same pixels inside a head box are never the arc's
    assert AC.on_trace_share(m, 0, 0, 1.0, (0, 0, 0, 0), 1.0, trace, 10.0, skip_boxes=[(0, 0, 6, 4)]) == 0.4
    monkeypatch.setenv(PL.ENV, "0")
    assert "arc_trace" in CF.mark_only()
    monkeypatch.setenv(PL.ENV, "1")
    assert "arc_trace" not in CF.mark_only() and "hairpin_trace" not in CF.mark_only()


def test_r5_a_piece_the_cell_split_off_inside_its_crop_is_not_a_view():
    # Litolff p6 cell 6/1/8/10 (Sean's 2.284 tiles 3-4): the page map fused a dynamic f with a beam-stem blob the cell keeps apart. The f's piece
    # (stroke 0) and the blob (stroke 1) both lie wholly on page stroke 9, each a small share of it, neither cut by the cell edge. The f's claim
    # must not reach the blob through the page stroke: the blob keeps its own (unclaimed) verdict.
    a = SO.own_strokes([_ink(0, "blob", (0, 0, 10, 10), 0.6, 0.3), _ink(1, "blob", (40, 0, 5, 8), 0.4, 0.3)],
                       [SO.Claim("f", "dynamic", "dynamicF", (0,), (), "g1")])
    assert a[0].family == "dynamic" and a[1].state == "unclaimed"
    links = {"A": {0: (9, 1.0, 0.15, 0.0), 1: (9, 0.85, 0.05, 0.0)}}
    page, cen = PL.pool({"A": a}, links, SO.TIERS)
    assert cen["split_differently"] == 2 and 9 not in page
    na, ch = PL.apply(a, links["A"], page)
    assert na[1].state == "unclaimed" and not ch
    # control (rule 7): with the old rule (no cut fact filed, a 3-tuple link) the f's claim does reach the blob
    links3 = {"A": {0: (9, 1.0, 0.15), 1: (9, 0.85, 0.05)}}
    page3, _ = PL.pool({"A": a}, links3, SO.TIERS)
    na3, _ = PL.apply(a, links3["A"], page3)
    assert na3[1].family == "dynamic"


def test_r5_a_piece_the_cell_edge_cut_is_still_a_view():
    # the barline case stays: the neighbour cell's piece of the rule is CUT by its crop (top and bottom), so it takes the one owner
    a = SO.own_strokes([_ink(0)], [SO.Claim("area-1", "barline", "barline", (0,), (), "r1", area=True)])
    b = SO.own_strokes([_ink(3)], [])
    links = {"A": {0: (7, 1.0, 0.03, 1.0)}, "B": {3: (7, 1.0, 0.03, 1.0)}}
    page, _ = PL.pool({"A": a, "B": b}, links, SO.TIERS)
    nb, _ = PL.apply(b, links["B"], page)
    assert nb[3].family == "barline"
    links0 = {"A": {0: (7, 1.0, 0.03, 0.0)}, "B": {3: (7, 1.0, 0.03, 0.0)}}
    page0, _ = PL.pool({"A": a, "B": b}, links0, SO.TIERS)
    nb0, _ = PL.apply(b, links0["B"], page0)
    assert nb0[3].state == "unclaimed"
