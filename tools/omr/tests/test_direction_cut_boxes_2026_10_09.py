"""ROADMAP 2.68 (open item, 2026-10-09): `sempre più p` read as `sempre p`.

Litolff p8 prints `sempre più p` on every staff. The detector boxed the `iù` of
`più` as a CLEF, a REST, an ORNAMENT or a stand-alone DYNAMIC; the detection
subtraction erased it; the word's box stopped after the `p`; the OCR was handed
`sempre p`, which the lexicon accepts. Three rules, each beside the case it must
leave alone (STAGED only, `refine_boxes` / `scan_order`):

1. HIDDEN LETTERS -- ink under a clef/rest/time-signature/ornament box, letter
   sized and on the word's line against its end, is the next letter of the
   word. Ink under a notehead is a note and is not.
2. A reading that ENDS in a dynamic letter with another dynamic standing against
   its box's end is the middle of a longer marking: it is read again with that
   dynamic and kept only if the longer reading keeps its terms; otherwise it is
   dropped (unread, never `sempre p`).
3. A reading whose box is far wider than its letters is read once more from the
   tight crop and dropped if any rung reads the same words and then MORE.

RED against the tree before the commit: (1) the box stopped at the `p`, (2) the
joined re-read skipped every reading that already carried a dynamic, and (3) did
not exist.
"""
from __future__ import annotations

import cv2

from tools.omr import direction_text as DT
from tools.omr.tests.test_direction_text import _page_dict, _pws, _staff

TEXT_Y = 760          # in the gap under staff 0 (staff 0 lines 500..660); 1 space = 40 px


def _ink(pws, x, w, y=TEXT_Y, h=34):
    cv2.rectangle(pws.page.rgb, (x, y), (x + w - 1, y + h - 1), (0, 0, 0), -1)


def _word_then_thin_letters(det_category, gap_px=8):
    """Four letters (x 400..511), then the thin `i` and `u` of `piu` standing
    `gap_px` after them, with ONE detection of `det_category` over the thin
    pair."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    for x in (400, 430, 460, 490):
        _ink(pws, x, 22)
    t0 = 512 + gap_px
    _ink(pws, t0, 12)
    _ink(pws, t0 + 20, 12)
    dets = {0: [{"category": det_category, "class": "x",
                 "bbox_page": [t0 - 4, TEXT_Y - 4, 44, 42]}]}
    return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)], dets), t0 + 32


def _the_word(pws, page_dict, refine=True):
    found = DT.find_candidates(pws, page_dict, refine_boxes=refine)
    assert len(found) == 1, found
    return found[0].bbox_page


# ── 1. hidden letters ───────────────────────────────────────────────────────

def test_letters_boxed_as_a_clef_are_the_end_of_the_word():
    pws, page_dict, end = _word_then_thin_letters("clef")
    assert _the_word(pws, page_dict)[2] >= end


def test_the_same_ink_boxed_as_a_rest_or_an_ornament_is_too():
    for category in ("rest", "ornament", "time_sig_digit"):
        pws, page_dict, end = _word_then_thin_letters(category)
        assert _the_word(pws, page_dict)[2] >= end, category


def test_the_same_ink_boxed_as_a_notehead_is_a_note_and_stays_out():
    pws, page_dict, end = _word_then_thin_letters("notehead")
    assert _the_word(pws, page_dict)[2] < 516


def test_letters_a_long_way_off_under_a_clef_box_do_not_join():
    pws, page_dict, end = _word_then_thin_letters("clef", gap_px=90)   # 2.25 spaces
    assert _the_word(pws, page_dict)[2] < 516


def test_the_frozen_legacy_boxes_do_not_grow_over_hidden_letters():
    pws, page_dict, end = _word_then_thin_letters("clef")
    assert _the_word(pws, page_dict, refine=False)[2] < 516


# ── 2. a reading that ends in a dynamic with another dynamic against its end ─

def _sempre_p_page(second_dynamic_x):
    """Four letters, the last of them the `p` of `piu` (detected as a dynamic
    and kept as a letter because ink stands on both sides of it), then a second
    dynamic box at `second_dynamic_x`: the `iu` of `piu` boxed as a dynamic."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    for x in (400, 430, 460, 490):
        _ink(pws, x, 22)
    _ink(pws, second_dynamic_x + 4, 12)
    _ink(pws, second_dynamic_x + 24, 12)
    dets = [{"category": "dynamic", "class": "dynamicM",
             "bbox_page": [second_dynamic_x, 756, 44, 42]}]
    if second_dynamic_x < 600:      # (a `p` with no ink beside it would be blanked as a dynamic)
        dets.insert(0, {"category": "dynamic", "class": "dynamicP",
                        "bbox_page": [490, 756, 22, 42]})
    dets = {0: dets}
    return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)], dets)


def _width_reader(shorter, longer, threshold=470):
    """The box alone makes a crop under `threshold` px wide, the box with the
    dynamic beside it a crop over it (staff space 40 px, crops upscaled 2x)."""
    def read(crops):
        return [longer if c.shape[1] > threshold else shorter for c in crops]
    return read


def _read(pws, page_dict, shorter, longer):
    return DT.read_directions(pws, page_dict, scan_order=True, readers=[
        ("tesseract", _width_reader(shorter, longer)),
        ("surya", _width_reader("", ""))])


def test_sempre_p_with_the_rest_of_piu_standing_against_it_is_read_whole():
    pws, page_dict = _sempre_p_page(516)
    words, info = _read(pws, page_dict, "sempre p", "sempre piu p")
    assert [(w.text, w.dynamics) for w in words] == [("sempre piu p", ("p",))]
    assert info["n_cut_tail_extended"] == 1


def test_sempre_p_is_dropped_when_the_longer_reading_cannot_be_made():
    """The OCR cannot read the whole: `sempre p` for a print of `sempre piu p` is
    a wrong marking, and nothing is better than that."""
    pws, page_dict = _sempre_p_page(516)
    words, info = _read(pws, page_dict, "sempre p", "sempre ptr")
    assert words == []
    assert info["n_cut_tail_dropped"] == 1


def test_sempre_p_with_a_dynamic_standing_clear_is_kept():
    """The control that stops the rule refusing everything: a dynamic 3 spaces
    after the word is a dynamic, and `sempre p` is what is printed."""
    pws, page_dict = _sempre_p_page(640)
    words, info = _read(pws, page_dict, "sempre p", "sempre piu p")
    assert [w.text for w in words] == ["sempre p"]
    assert info["n_cut_tail_dropped"] == 0 and info["n_cut_tail_extended"] == 0


def _sempre_p_before_a_clef_box(clef_x):
    """Four plain letters read `sempre p`; a clef box (the detector's reading of
    the `iu` after them, tangled with a sharp) starts at `clef_x`."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    for x in (400, 430, 460, 490):
        _ink(pws, x, 22)
    _ink(pws, clef_x + 4, 12)
    dets = {0: [{"category": "clef", "class": "clefG",
                 "bbox_page": [clef_x, 756, 44, 42]}]}
    return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)], dets)


def test_sempre_p_with_a_clef_box_1_3_spaces_after_it_is_dropped():
    """Litolff p8 staff 6: the `iu` stood under three clef boxes 1.3 spaces past
    the `p`, too tangled with a sharp to join the box -- but a clef cannot stand
    in a line of text, so the word is known to be cut."""
    pws, page_dict = _sempre_p_before_a_clef_box(565)
    words, info = _read(pws, page_dict, "sempre p", "sempre p")
    assert words == []
    assert info["n_cut_tail_dropped"] == 1


def test_sempre_p_with_a_clef_box_3_spaces_after_it_is_kept():
    pws, page_dict = _sempre_p_before_a_clef_box(640)
    words, _info = _read(pws, page_dict, "sempre p", "sempre p")
    assert [w.text for w in words] == ["sempre p"]


# ── 3. a reading that is only the front of a longer one ─────────────────────

def _wide_word_page(pitch):
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    for k in range(5):
        _ink(pws, 400 + k * pitch, 22)
    return pws, _page_dict([0, 1], [(100, 1000), (1000, 2000)])


def _stateful(outputs):
    """Each call answers the next of `outputs` (then the last, for ever)."""
    seq = iter(outputs)
    last = [outputs[-1]]

    def read(crops):
        try:
            last[0] = next(seq)
        except StopIteration:
            pass
        return [last[0]] * len(crops)
    return read


def test_a_wide_box_read_as_the_front_of_a_longer_reading_is_dropped():
    pws, page_dict = _wide_word_page(pitch=100)          # 10.5 spaces for 5 letters
    words, info = DT.read_directions(pws, page_dict, scan_order=True, readers=[
        ("tesseract", _stateful(["dolce", "dolce piu"])), ("surya", _width_reader("", ""))])
    assert words == []
    assert info["n_front_of_a_longer_reading_dropped"] == 1


def test_a_wide_box_whose_second_reading_agrees_is_kept():
    pws, page_dict = _wide_word_page(pitch=100)
    words, _info = DT.read_directions(pws, page_dict, scan_order=True, readers=[
        ("tesseract", _stateful(["dolce", "dolce"])), ("surya", _width_reader("", ""))])
    assert [w.text for w in words] == ["dolce"]


def test_an_ordinary_box_is_not_read_again():
    pws, page_dict = _wide_word_page(pitch=34)           # 3.2 spaces for 5 letters
    words, info = DT.read_directions(pws, page_dict, scan_order=True, readers=[
        ("tesseract", _stateful(["dolce", "dolce piu"])), ("surya", _width_reader("", ""))])
    assert [w.text for w in words] == ["dolce"]
    assert info["n_front_of_a_longer_reading_dropped"] == 0


def test_the_front_of_a_reading_is_words_then_more_words_not_a_dynamic():
    assert DT._is_the_front_of("sempre", "sempre piu: °")
    assert not DT._is_the_front_of("piu", "piu f")          # a dynamic is the joined step's
    assert not DT._is_the_front_of("dim", "dim.")           # same words, nothing more
    assert not DT._is_the_front_of("dolce", "poco dolce")   # not a front
