"""ROADMAP 2.261 -- the three 20261103-night regressions, each behind its own flag (default OFF). Synthetic shapes whose answer is known by
construction. STAGED. Fix 1: a reach find with a stem at both ends is a beam. Fix 2: a word read only on the through-line retry claims no
ink inside detector notehead boxes. Fix 3: only a candidate with a shape witness stops a carried clef."""
from __future__ import annotations

import numpy as np

from tools.omr.hairpin_detection import detect_hairpins, stem_joins
from tools.omr.staged import clef_pagewide as CP
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


def test_flags_are_off_by_default(monkeypatch):
    for env in (hairpin_reach.NOT_A_BEAM_ENV, hairpin_reach.HEADS_ENV, CP.ENV_STRONG_STOP):
        monkeypatch.delenv(env, raising=False)
    assert hairpin_reach.not_a_beam_enabled() is False
    assert hairpin_reach.word_retry_spares_heads_enabled() is False
    assert CP.strong_stop_enabled() is False
    monkeypatch.setenv(hairpin_reach.NOT_A_BEAM_ENV, "1")
    assert hairpin_reach.not_a_beam_enabled() is True


def test_stem_joins_sees_a_stem_at_each_end_and_not_a_barline_in_the_middle():
    page = _page(_wedge())
    page[100:520, 400:406] = 255                       # a barline through the MIDDLE
    assert stem_joins(page, 300, 200, 200, 26, SP) == (0.0, 0.0) or max(stem_joins(page, 300, 200, 200, 26, SP)) < 1.2
    page[226:300, 299:302] = 255                       # a stem down from the left end
    page[226:300, 498:501] = 255                       # and one from the right end
    left, right = stem_joins(page, 300, 200, 200, 26, SP)
    assert left >= 1.2 and right >= 1.2


def test_no_beams_refuses_a_find_with_a_stem_at_both_ends_and_keeps_the_rest():
    plain = _page(_wedge())
    plain[100:520, 400:406] = 255                      # the barline hairpin the reach was built for
    refused: list = []
    got = detect_hairpins(plain, _staves(), reach=True, no_beams=True, refused=refused)
    assert len(got) == 1 and refused == []
    both = _page(_wedge())
    both[226:300, 299:302] = 255
    both[226:300, 498:501] = 255
    assert len(detect_hairpins(both, _staves(), reach=True)) >= 1            # flag off: unchanged
    refused = []
    assert detect_hairpins(both, _staves(), reach=True, no_beams=True, refused=refused) == []
    assert refused and refused[0][1] >= 1.2 and refused[0][2] >= 1.2


def test_retry_word_spares_the_head_boxes():
    binary = np.full((200, 400), 255, np.uint8)
    binary[100:140, 20:30] = 0                          # the f (left)
    binary[110:130, 100:120] = 0                        # a head
    binary[60:130, 118:121] = 0                         # its stem (touches the head)
    binary[110:130, 200:220] = 0                        # a second head
    box = [10.0, 50.0, 260.0, 150.0]
    heads = [[98.0, 108.0, 122.0, 132.0], [198.0, 108.0, 222.0, 132.0]]
    areas, spared = hairpin_reach.word_area_sparing_heads(binary, box, heads, 20.0)
    assert len(spared) == 2
    assert areas and all(not (a[0] < h[2] and a[2] > h[0] and a[1] < h[3] and a[3] > h[1]) for a in areas for h in heads)
    assert any(a[0] <= 20 and a[2] >= 30 for a in areas)                     # the f is still the word's
    same, none = hairpin_reach.word_area_sparing_heads(binary, box, [[300.0, 10.0, 320.0, 30.0]], 20.0)
    assert none == [] and same == [box]
    assert hairpin_reach.is_retry_only_reading("tesseract-lines-tight") and not hairpin_reach.is_retry_only_reading("surya")


class _Row:
    def __init__(self, **detail):
        self.detail = detail


def test_weak_candidate_is_a_stop_off_and_not_on(monkeypatch):
    changes = [(600.0, "bass", _Row())]
    weak = [(691.0, None, _Row(why=CP.WEAK_CANDIDATE_WHY, family="G", body_score=None, strong=False, candidate=True))]
    witnessed = [(691.0, None, _Row(why="f_body_below_read", family="F", body_score=0.73, strong=False, candidate=True))]
    monkeypatch.delenv(CP.ENV_STRONG_STOP, raising=False)
    assert CP.clef_in_force(800.0, changes, weak, "tenor")[0] is None          # OFF: the staff is blanked
    monkeypatch.setenv(CP.ENV_STRONG_STOP, "1")
    assert CP.clef_in_force(800.0, changes, weak, "tenor")[0] == "bass"        # ON: counted, carried
    assert CP.clef_in_force(800.0, changes, witnessed, "tenor")[0] is None     # a shape witness still stops (Sean 2026-11-02)
