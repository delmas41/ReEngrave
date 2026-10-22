"""ROADMAP 2.95 -- a word printed BETWEEN two braced staves names both.

Brahms 1/i (Breitkopf 317803) prints `(C)` beside the upper horn staff, `Hr.`
centred between the two staves, and `(Es)` beside the lower. The margin reader
used to hand the word to whichever tick was nearer (by 2 px of 120) or drop it,
so a staff read a bare crook that no lexicon entry can name.

Positive controls sit beside every refusal: a single-staff label stays on its
own staff, and a word that is not between two crook-only staves does not
spread.
"""
from __future__ import annotations

import types

import numpy as np

from tools.omr import _surya_worker as worker
from tools.omr import staff_labels_surya as sls
from tools.omr.staff_labels_vision import build_margin_crop

# ── the worker's geometry report ────────────────────────────────────────────

TICKS = [100.0, 200.0, 300.0, 420.0, 500.0]   # mean spacing 100, one wide gap
IDX = [10, 11, 12, 13, 14]


def test_a_word_at_the_midpoint_is_reported_between_its_two_staves():
    # midpoint of 300..420 is 360: 60 px from each tick, past the 50 px
    # tolerance, so `_assign` drops it
    assert worker._assign([("Hr.", 360.0, 40.0)], TICKS, IDX) == {}
    out = worker._between([("Hr.", 360.0, 40.0)], TICKS, IDX)
    assert out == [{"text": "Hr.", "upper": 12, "lower": 13, "offset": 0.0,
                    "assigned_to": None}]


def test_a_word_nearer_one_tick_is_reported_with_who_it_was_assigned_to():
    # 12 px short of the midpoint, inside tolerance: `_assign` hands it on
    out = worker._between([("Hr.", 348.0, 40.0)], TICKS, IDX)
    assert len(out) == 1 and out[0]["assigned_to"] == 12
    assert worker._assign([("Hr.", 348.0, 40.0)], TICKS, IDX) == {12: "Hr."}


def test_a_word_beside_one_staff_is_never_between():           # control
    assert worker._between([("Fl.", 100.0, 40.0), ("Ob.", 210.0, 40.0)],
                           TICKS, IDX) == []


def test_a_word_off_the_midpoint_is_not_between():             # control
    # 0.3 of a gap from the midpoint
    assert worker._between([("Hr.", 380.0, 40.0)], TICKS, IDX) == []


def test_a_runaway_block_is_never_between():                   # control
    assert worker._between([("everything", 350.0, 300.0)], TICKS, IDX) == []


# ── the pure spreading rule ─────────────────────────────────────────────────

def _blk(word="Hr.", up=5, lo=6, assigned=None):
    return {"text": word, "upper": up, "lower": lo, "offset": 0.0,
            "assigned_to": assigned}


def test_both_staves_bare_crooks_each_take_the_word_with_their_own_crook():
    texts = {4: "K-Fag.", 5: "(C)", 6: "(Es)", 7: "Pk."}
    new, shared = sls.spread_shared_words(texts, [_blk()])
    assert new[5] == "Hr. (C)" and new[6] == "Hr. (Es)"
    assert shared == {5: "Hr.", 6: "Hr."}
    # nobody else moved
    assert new[4] == "K-Fag." and new[7] == "Pk."


def test_the_word_already_handed_to_one_staff_completes_the_other():
    texts = {5: "(C) Hr.", 6: "(Es)"}
    new, shared = sls.spread_shared_words(texts, [_blk(assigned=5)])
    assert new == {5: "(C) Hr.", 6: "Hr. (Es)"}
    assert shared == {6: "Hr."}


def test_a_staff_with_its_own_full_name_is_not_overwritten():  # control
    texts = {5: "Fag.", 6: "(Es)"}
    new, shared = sls.spread_shared_words(texts, [_blk()])
    assert new == texts and shared == {}


def test_a_flanking_staff_that_read_nothing_stops_the_spread():  # control
    new, shared = sls.spread_shared_words({5: "(C)"}, [_blk()])
    assert new == {5: "(C)"} and shared == {}


def test_a_word_the_lexicon_does_not_know_is_not_spread():     # control
    texts = {5: "(C)", 6: "(Es)"}
    new, shared = sls.spread_shared_words(texts, [_blk(word="Xqz")])
    assert new == texts and shared == {}


def test_a_between_crook_is_not_spread_as_a_word():            # control
    texts = {5: "(C)", 6: "(Es)"}
    new, shared = sls.spread_shared_words(texts, [_blk(word="(F)")])
    assert new == texts and shared == {}


def test_no_between_report_changes_nothing():                  # control
    texts = {5: "(C)", 6: "(Es)"}
    assert sls.spread_shared_words(texts, []) == (texts, {})


def test_two_words_never_claim_the_same_staves():
    texts = {5: "(C)", 6: "(Es)"}
    new, shared = sls.spread_shared_words(
        texts, [_blk(), _blk(word="Tr.")])
    assert new[5] == "Hr. (C)" and new[6] == "Hr. (Es)"


# ── through the reader ──────────────────────────────────────────────────────

class _Staff:
    def __init__(self, index, top, bottom, system_index=0):
        self.staff_index = index
        self.top_y, self.bottom_y = top, bottom
        self.x_start = 400
        self.line_spacing_px = 10.0
        self.system_index = system_index


def _pws(staves, height=900, width=800):
    page = types.SimpleNamespace(
        binary=np.zeros((height, width), dtype=np.uint8),
        rgb=np.full((height, width, 3), 255, dtype=np.uint8))
    return types.SimpleNamespace(page=page, staves=staves)


def test_the_reader_names_both_horn_staves_from_one_printed_word(monkeypatch):
    staves = [_Staff(0, 130, 170), _Staff(1, 330, 370), _Staff(2, 430, 470),
              _Staff(3, 730, 770)]
    payload = {"systems": [{
        "labels": {"0": "Fag.", "1": "(C)", "2": "(Es)", "3": "Pk."},
        "between": [{"text": "Hr.", "upper": 1, "lower": 2, "offset": 0.0,
                     "assigned_to": None}]}]}
    monkeypatch.setattr(sls, "_dispatch", lambda *a, **k: payload)
    labs = {lab.staff_index: lab
            for lab in sls.read_staff_labels_surya(_pws(staves))}
    assert labs[1].text == "Hr. (C)" and labs[2].text == "Hr. (Es)"
    assert labs[1].shared_word == labs[2].shared_word == "Hr."
    assert labs[1].instrument is not None and labs[2].instrument is not None
    assert labs[1].instrument.name == labs[2].instrument.name == "Horn"
    # a single-staff label stays on its own staff, unflagged
    assert labs[0].text == "Fag." and labs[0].shared_word == ""
    assert labs[3].text == "Pk." and labs[3].shared_word == ""


def test_the_reader_without_a_between_report_is_what_it_was(monkeypatch):
    staves = [_Staff(0, 130, 170), _Staff(1, 330, 370)]
    payload = {"systems": [{"labels": {"0": "Fl.", "1": "(Es)"}}]}
    monkeypatch.setattr(sls, "_dispatch", lambda *a, **k: payload)
    labs = {lab.staff_index: lab
            for lab in sls.read_staff_labels_surya(_pws(staves))}
    assert labs[1].text == "(Es)" and labs[1].shared_word == ""
