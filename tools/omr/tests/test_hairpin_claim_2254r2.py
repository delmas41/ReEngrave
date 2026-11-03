"""ROADMAP 2.254 round 2 -- the hairpin read CLAIMS its arms (STAGED GATHER, flag OMR_HAIRPIN_REACH, default OFF), and the word reader's mask
leaves them out. Synthetic shapes whose answer is known by construction."""
from __future__ import annotations

import types

import numpy as np

from tools.omr import direction_text as DT
from tools.omr.staged import hairpin_reach as HR
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged import claim_order as CO
from tools.omr.staged.adjudicators import stroke_owner as ASO

SP = 20.0


def _cresc(width=200, opening=20, thick=3, at=(100, 50)):
    """A crescendo drawn on a page; returns (page uint8 255=ink, bbox)."""
    page = np.zeros((300, 400), np.uint8)
    y0, x0 = at
    h = opening + thick
    for x in range(width):
        half = (x / (width - 1)) * opening / 2.0
        mid = y0 + opening / 2.0
        page[int(round(mid - half)):int(round(mid - half)) + thick, x0 + x] = 255
        page[int(round(mid + half)):int(round(mid + half)) + thick, x0 + x] = 255
    return page, [float(x0), float(y0), float(x0 + width), float(y0 + h)]


def test_arms_meet_at_the_narrow_end():
    c = HR.arms("crescendo", [0, 0, 100, 20])
    assert c[0][:2] == [0.0, 10.0] and c[1][:2] == [0.0, 10.0]
    assert {tuple(s[2:]) for s in c} == {(100.0, 0.0), (100.0, 20.0)}
    d = HR.arms("diminuendo", [0, 0, 100, 20])
    assert d[0][:2] == [100.0, 10.0] and {tuple(s[2:]) for s in d} == {(0.0, 0.0), (0.0, 20.0)}


def _res(masks):
    return types.SimpleNamespace(masks=masks, scale=1.0)


def test_the_arms_are_claimed_and_a_crossing_stem_is_not():
    page, bb = _cresc()
    arm = page[int(bb[1]) - 2:int(bb[3]) + 2, int(bb[0]):int(bb[2])] > 0
    stem = np.zeros((80, 3), bool)                       # a stem 4 sp long crossing the hairpin at x = 150
    stem[:, :] = True
    res = _res([(arm, int(bb[0]), int(bb[1]) - 2), (stem, 150, 80)])
    got = HR.claim_strokes(res, [0, 0, 400, 300], 1.0, HR.arms("crescendo", bb), bb, HR.band_px(SP))
    assert [i for i, _s in got] == [0]
    assert got[0][1] >= 0.9


def test_a_beam_parallel_under_the_hairpin_is_not_claimed():
    page, bb = _cresc()
    beam = np.ones((8, 150), bool)                        # a horizontal beam 2 sp below the box
    res = _res([(beam, 60, int(bb[3]) + 40)])
    assert HR.claim_strokes(res, [0, 0, 400, 300], 1.0, HR.arms("crescendo", bb), bb, HR.band_px(SP)) == []


def test_the_word_mask_loses_the_arms_and_keeps_a_letter_in_the_opening():
    page, bb = _cresc()
    page[108:114, 200:206] = 255                          # a dot / letter inside the mouth, clear of both arms
    entry = {"bbox_page_px": bb, "segments": HR.arms("crescendo", bb), "band_px": HR.band_px(SP)}
    out = DT._blank_detections(page, {"systems": [], "erase_ink": [entry]}, SP, DT.DEFAULT_BAND_CONFIG)
    assert out[108:114, 200:206].all()                    # the letter stays
    arms_left = (out > 0).sum() - 36
    assert arms_left <= 0.02 * (page > 0).sum()           # the arms are gone


def test_no_erase_key_is_the_old_mask_exactly():
    page, _bb = _cresc()
    out = DT._blank_detections(page, {"systems": []}, SP, DT.DEFAULT_BAND_CONFIG)
    assert np.array_equal(out, page)


def test_the_claim_is_a_page_wide_tier_and_the_readout_sees_it():
    assert HR.FAMILY in SO.TIERS[0]
    assert CO.layer_of(HR.FAMILY) == CO.LAYER_NAMES.index("arc_hairpin")
    assert CO.layer_of(HR.FAMILY) < CO.L_CONSUMER


class _Ev:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, *_a, **_k):
        return self._rows


def test_the_stroke_owner_reads_the_claim_only_with_the_flag(monkeypatch):
    row = types.SimpleNamespace(id="obs:1", value=[[3, 0], [3, 2], [4, 1]], detail={"owner": "hairpin", "unit": "ink"})
    cell = types.SimpleNamespace(cell=3)
    monkeypatch.delenv(HR.ENV, raising=False)
    assert ASO._hairpin_claims(_Ev([row]), cell) == []
    monkeypatch.setenv(HR.ENV, "1")
    got = ASO._hairpin_claims(_Ev([row]), cell)
    assert len(got) == 1 and got[0].family == HR.FAMILY and tuple(got[0].covers) == (0, 2)


def test_a_beam_refused_on_a_claimed_hairpin_arm_counts_as_not_a_beam_only_with_the_flag(monkeypatch):
    from tools.omr.staged import inferences as I
    v = types.SimpleNamespace(reason=I.BARE_STEM_REASON, detail={
        "beam_evidence": "none_over_this_note", "stems_attached": 1, "bare_stem_tip_window_clean": True,
        "refused_strokes": [{"id": "a", "why": "ink:owned_by_another_mark", "at_tip": False}, {"id": "b", "why": "arc", "at_tip": False}]})
    monkeypatch.delenv(HR.ENV, raising=False)
    assert I.arc_ink_not_beam_decline(v) == "a_refusal_that_is_not_a_slur_reading:ink:owned_by_another_mark"
    monkeypatch.setenv(HR.ENV, "1")
    assert I.arc_ink_not_beam_decline(v) is None
