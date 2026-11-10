"""ROADMAP 2.284 -- the page ledger owns the ink (`page_ledger`, flag `OMR_PAGE_LEDGER_OWNS`). Pure tests of the pool / apply rule and the link."""
from __future__ import annotations

import numpy as np

from tools.omr.staged import page_ledger as PL
from tools.omr.staged import stroke_owner as SO


def _ink(o, kind="vertical", box=(0, 0, 2, 40), length=2.5, thick=0.15):
    return SO.Ink(o, kind, box, length, thick, 0.3, 16.0)


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(PL.ENV, raising=False)
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
    assert cen["page_strokes_seen_twice"] == 1


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
    assert out[0] == (0, 1.0)
    assert out[1] is None


def test_carved_barline_rule_is_a_page_stroke_where_no_other_stroke_stands():
    pm = _Map([], [], barlines=[{"box": (40, 0, 42, 50)}])
    lab = PL.PageLabels(pm, (60, 60))
    rule = np.ones((20, 2), bool)
    out = PL.link_cell_strokes(_Res([(rule, 40, 10)], 1.0), (0.0, 0.0, 60.0, 60.0), 1.0, lab)
    assert out[0] == (0, 1.0)                            # ordinal n_strokes + k = 0 + 0
