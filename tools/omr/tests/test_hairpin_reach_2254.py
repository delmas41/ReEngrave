"""ROADMAP 2.254 -- hairpin reach (STAGED GATHER, flag OMR_HAIRPIN_REACH, default OFF).

Synthetic shapes whose answer is known by construction: a hairpin crossed by a barline, touched by a stem, crossed by a slur; and the
things the reach must still refuse (a beam pair stripped of its stems, a word glued into a band, an arc). Plus the one-note wedge
abstention in ADJUDICATE.
"""
from __future__ import annotations

import os

import numpy as np

from tools.omr.hairpin_detection import (converges, detect_hairpins, extent_trend, measure_component, reach_inks,
                                         robust_outline_rms, straight_runs)
from tools.omr.staged import hairpin_reach

SP = 20.0


def _staves():
    return [{"index": 0, "top": 100.0, "bottom": 180.0, "spacing": SP}]


def _wedge(width=200, opening=20, thick=3):
    h = opening + 6
    m = np.zeros((h, width), np.uint8)
    for x in range(width):
        half = (x / (width - 1)) * opening / 2.0
        mid = h / 2.0
        m[int(round(mid - half)):int(round(mid - half)) + thick, x] = 255
        m[int(round(mid + half)):int(round(mid + half)) + thick, x] = 255
    return m


def _page(mask, at=(200, 300)):
    page = np.zeros((600, 900), np.uint8)
    y, x = at
    page[y:y + mask.shape[0], x:x + mask.shape[1]] = mask
    return page


def test_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv(hairpin_reach.ENV, raising=False)
    assert hairpin_reach.enabled() is False
    monkeypatch.setenv(hairpin_reach.ENV, "1")
    assert hairpin_reach.enabled() is True


def test_a_barline_through_the_hairpin_hides_it_off_and_not_on():
    """The cause: a barline crossing the band makes the hairpin one component with it (not straight, not isolated)."""
    page = _page(_wedge())
    page[20:580, 400:406] = 255                      # a barline from the staff above to the staff below
    assert detect_hairpins(page, _staves()) == []
    got = detect_hairpins(page, _staves(), reach=True)
    assert len(got) == 1 and got[0].kind == "crescendo"
    assert got[0].x <= 302 and got[0].x + got[0].width >= 498     # the two halves are one hairpin again


def test_a_stem_touching_the_hairpin_is_cut_away_on():
    page = _page(_wedge())
    page[20:213, 450:453] = 255                      # a stem from above, touching the upper arm
    assert detect_hairpins(page, _staves()) == []
    assert len(detect_hairpins(page, _staves(), reach=True)) == 1


def test_a_slur_crossing_an_arm_is_cut_away_on():
    page = _page(_wedge())
    for x in range(330, 470):                        # a steep arc crossing the wedge's lower arm
        t = (x - 330) / 140.0
        y = int(round(250 - 70 * 4 * t * (1 - t)))
        page[y:y + 3, x] = 255
    assert detect_hairpins(page, _staves()) == []
    assert len(detect_hairpins(page, _staves(), reach=True)) == 1


def test_a_beam_pair_without_its_stems_does_not_converge():
    """Removing the stems makes a beam as isolated as a hairpin; the arms of a hairpin meet, a beam's do not."""
    page = np.zeros((600, 900), np.uint8)
    page[205:212, 300:500] = 255
    page[222:229, 300:500] = 255
    for x in (300, 400, 497):
        page[205:280, x:x + 3] = 255                 # stems
    assert detect_hairpins(page, _staves(), reach=True) == []
    m = measure_component(np.vstack([np.full((7, 200), 255, np.uint8), np.zeros((10, 200), np.uint8),
                                     np.full((7, 200), 255, np.uint8)]), SP)
    assert not converges(m)


def test_a_word_glued_by_the_rejoin_has_no_trend():
    """Letters of one height glued into a band: flat extent, no steady opening."""
    m = np.zeros((20, 120), np.uint8)
    for x0 in range(0, 120, 16):
        m[2:18, x0:x0 + 3] = 255
        m[2:5, x0:x0 + 12] = 255
        m[15:18, x0:x0 + 12] = 255
    assert extent_trend(m) < 0.5
    assert extent_trend(_wedge()) > 0.9


def test_robust_outline_forgives_a_dot_glued_at_one_end():
    w = _wedge()
    w[0:8, 0:10] = 255                                # a blob at the apex end
    plain = measure_component(w, SP)["outline_rms_spaces"]
    assert robust_outline_rms(w, SP) < plain


def test_reach_inks_and_straight_runs_keep_the_arms():
    page = _page(_wedge())
    page[20:580, 400:406] = 255
    search, iso = reach_inks(page, page, _staves())
    kept = straight_runs(search, SP)
    assert kept[200:230, 300:500].sum() > 0.8 * _wedge().sum()
    assert kept[20:190, 400:406].sum() < 0.02 * page[20:190, 400:406].sum()   # the barline is gone


def test_off_is_unchanged_on_an_isolated_wedge():
    page = _page(_wedge())
    a = detect_hairpins(page, _staves())
    b = detect_hairpins(page, _staves(), reach=True)
    assert len(a) == len(b) == 1 and a[0].kind == b[0].kind


def test_one_note_wedge_abstains_only_with_the_flag():
    import inspect
    from tools.omr.staged.adjudicators import ownership
    src = inspect.getsource(ownership._wedge_page_binding)
    assert '"one_note_wedge"' in src and "_hairpin_reach.enabled()" in src
    assert "one_note_wedge" in inspect.getsource(ownership)


def test_a_word_box_gives_up_the_hairpin_inside_it():
    """Brahms p8: the OCR box of 'dim.' held a real hairpin. The word keeps its letters' ink; the wedge is left out."""
    binary = np.full((300, 600), 255, np.uint8)            # 0 = ink
    for x0 in (20, 40, 60):                                 # three letter-sized blobs
        binary[110:130, x0:x0 + 12] = 0
    w = _wedge()
    binary[105:105 + w.shape[0], 120:320][w > 0] = 0       # a hairpin right of them, inside the same box
    area, dropped = hairpin_reach.word_area_without_wedges(binary, [10, 100, 330, 140], SP)
    assert len(dropped) == 1 and area[2] <= 80
    area2, dropped2 = hairpin_reach.word_area_without_wedges(binary, [10, 100, 90, 140], SP)
    assert dropped2 == [] and area2 == [10.0, 100.0, 90.0, 140.0]


def _owner_case(hairpin_box, monkeypatch, on):
    """test_staged_owner_conventions' hairpin case: a head at y 150 under UPPER (bottom line 140), a hairpin filed under UPPER at y 200."""
    from tools.omr.tests import test_staged_owner_conventions as T
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q, READERS
    if on:
        monkeypatch.setenv(hairpin_reach.ENV, "1")
    else:
        monkeypatch.delenv(hairpin_reach.ENV, raising=False)
    case = T.TestHairpinSeparates()
    log = case._log_with_head_and_lines(head_y=150.0)
    log.observe(R.glyph(T.UPPER.page, T.UPPER.system, T.UPPER.staff, 3, 0), Q.WEDGE_BOX, "diminuendo",
                reader=READERS.CV_HAIRPINS, frame="page", bbox_page_px=hairpin_box,
                x_center_page=(hairpin_box[0] + hairpin_box[2]) / 2, y_center_page=200.0)
    return T._decide(log), T


def test_hairpin_separates_is_local_with_the_flag(monkeypatch):
    """Brahms p25: a Vc hairpin (bars 473-474) gave the K.-B.'s flats two bars to its RIGHT to the Vc, because the old term reads y
    only. ON, a hairpin whose x span does not hold the glyph says nothing (page-facts: notes NEXT TO a hairpin)."""
    far = [900.0, 195.0, 970.0, 205.0]                       # the head is at x 505
    v_off, T = _owner_case(far, monkeypatch, on=False)
    assert v_off.reason == "hairpin_separates"               # OFF: unchanged (the old y-only rule)
    v_on, T = _owner_case(far, monkeypatch, on=True)
    assert v_on.reason == "range_veto" and v_on.value == T.LOWER.to_key()
    near = [490.0, 195.0, 560.0, 205.0]
    v_near, T = _owner_case(near, monkeypatch, on=True)
    assert v_near.reason == "hairpin_separates" and v_near.value == T.UPPER.to_key()
