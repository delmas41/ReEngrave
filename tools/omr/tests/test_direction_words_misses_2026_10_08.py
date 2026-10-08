"""Direction-word misses Sean listed on the 10 scan pages (2026-10-08).

Each rule is stated in the test that pins it; the page that motivates it is
named. Written RED against the tree before the change (the lexicon and finder
entries did not exist or refused the string).
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from tools.omr import direction_text as DT
from tools.omr.direction_lexicon import lookup
from tools.omr.direction_text import (
    DEFAULT_BAND_CONFIG, DirectionText, TextCandidate, find_candidates,
    sibling_candidates, tight_crop_for)
from tools.omr.tests.test_direction_text import (
    SPACING, _page_dict, _pws, _staff)


# -- lexicon ---------------------------------------------------------------

@pytest.mark.parametrize("text,category", [
    ("Basso", "part"), ("Bassi.", "part"), ("Vcl.", "part"),   # Litolff p4/p6/p12
    ("marc.", "expression"),                                    # Brahms p12/p24
    ("a2", "part"), ("a 2", "part"), ("a.2", "part"),           # Brahms p3/p12/p24
])
def test_words_sean_asked_for_are_read(text, category):
    hit = lookup(text)
    assert hit is not None and hit.category == category and hit.text == text


@pytest.mark.parametrize("text,expected,dyn", [
    ("più f", "più f", ("f",)),                         # Brahms p3: ONE marking, word + dynamic
    ("piu f", "piu f", ("f",)),
    ("sempre molto p e dolce", "sempre molto p e dolce", ("p",)),   # Brahms p7
    ("p cresc.", "p cresc.", ("p",)),
    ("f marc.", "f marc.", ("f",)),
    ("sempre p", "sempre p", ("p",)),
    ("poco a poco cresc.", "poco a poco cresc.", ()),
    ("pmarc.", "p marc.", ("p",)),                     # Brahms p12, `p` glued on by the OCR
    (", cresc.", "cresc.", ()),                        # OCR punctuation debris at the ends
])
def test_a_dynamic_beside_a_word_is_one_marking_kept_whole(text, expected, dyn):
    """Sean 2026-10-08 (round 4): do NOT drop the dynamic letter; word and
    dynamic mean something only together."""
    hit = lookup(text)
    assert hit is not None and hit.text == expected and hit.dynamics == dyn


def test_ten_is_tenuto():
    assert lookup("ten.").category == "expression"        # Litolff p9


@pytest.mark.parametrize("text", [
    "p", "f", "pp f", "e e e",       # a dynamic alone, connectives alone: still nothing
    "CTESC.", "Crese.", "Vel.",       # NO fuzzy matching: garbled stays refused
    "cresc. cresc. cresc.",           # a looping decoder is still refused
    "a2b", "2", "a 22",
])
def test_noise_and_garbled_words_are_still_refused(text):
    assert lookup(text) is None


def test_a_term_that_starts_with_a_dynamic_letter_is_left_alone():
    assert lookup("piano").text == "piano"
    assert lookup("poco").text == "poco"
    assert lookup("pizz.").text == "pizz."


# -- tight crop ------------------------------------------------------------

def test_the_tight_crop_leaves_out_the_neighbours_the_wide_crop_takes_in():
    """Litolff p4: `cresc.` between two barlines read as '' from the wide crop and
    as `cresc.` from the box cut tight."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    rgb = pws.page.rgb
    cv2.rectangle(rgb, (330, 690), (336, 760), (0, 0, 0), -1)        # a barline 40 px left of the word
    cv2.rectangle(rgb, (380, 700), (480, 734), (0, 0, 0), -1)        # the word
    cand = TextCandidate(0, 0, (380, 700, 480, 734), "below", 5)
    wide = DT.crop_for(pws.page, cand, SPACING)
    tight = tight_crop_for(pws.page, cand, SPACING)
    assert (wide < 128).any(axis=2).sum() > 0
    # wide includes the barline column; tight has it cut away: ink columns span only the word
    def ink_span(img):
        cols = np.where((img < 128).any(axis=(0, 2)))[0]
        return (cols.max() - cols.min()) / img.shape[1]
    assert ink_span(wide) > ink_span(tight) + 0.15                   # control: the wide one holds more
    assert tight[0].min() == 255 and tight[-1].min() == 255          # white margin on top and bottom
    assert tight[:, 0].min() == 255 and tight[:, -1].min() == 255


# -- siblings --------------------------------------------------------------

def _word(rgb, x, y, n=6):
    for k in range(n):
        cv2.rectangle(rgb, (x + k * 30, y), (x + k * 30 + 22, y + 34), (0, 0, 0), -1)


def test_a_word_read_on_one_staff_makes_a_place_to_look_on_the_others_only():
    pws = _pws([_staff(0, 500), _staff(1, 1200), _staff(2, 1900)])
    rgb = pws.page.rgb
    _word(rgb, 300, 700)                    # the word the OCR read, staff 0
    _word(rgb, 310, 1400)                   # the same word at nearly the same x, staff 1 (the finder lost it)
    page_dict = _page_dict([0, 1, 2], [(100, 1000), (1000, 2000)])
    cands = [TextCandidate(0, 0, (300, 700, 450, 734), "below", 6)]
    accepted = {0: DirectionText(0, 0, 300, "cresc.", "dynamic", "below", ("cresc",), "tesseract")}
    ink = DT._page_ink(pws.page)
    extra = sibling_candidates(pws, page_dict, ink, cands, accepted, SPACING, DEFAULT_BAND_CONFIG)
    assert [c.staff_index for c in extra] == [1]                    # staff 2 has no ink there: no window
    assert abs(extra[0].bbox_page[0] - 310) < 30                    # and it sits at the sibling's x


def test_a_part_name_is_not_echoed_onto_other_staves():
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    _word(pws.page.rgb, 300, 700)
    _word(pws.page.rgb, 310, 1400)
    page_dict = _page_dict([0, 1], [(100, 1000), (1000, 2000)])
    cands = [TextCandidate(0, 0, (300, 700, 450, 734), "below", 6)]
    accepted = {0: DirectionText(0, 0, 300, "Basso", "part", "below", ("basso",), "tesseract")}
    assert sibling_candidates(pws, page_dict, DT._page_ink(pws.page), cands, accepted,
                              SPACING, DEFAULT_BAND_CONFIG) == []


# -- tempo strips and the pair `a 2` ----------------------------------------

def test_a_tall_tempo_word_under_the_last_staff_of_a_system_is_a_candidate():
    """Brahms p3: bold `Allegro` under the last staff, capitals 3.1 spaces tall."""
    pws = _pws([_staff(0, 500)])
    bottom = pws.staves[0].bottom_y
    for k in range(7):
        cv2.rectangle(pws.page.rgb, (300 + k * 60, bottom + 15), (300 + k * 60 + 45, bottom + 15 + int(3.1 * SPACING)),
                      (0, 0, 0), -1)
    page_dict = _page_dict([0], [(100, 2000)])
    assert len(find_candidates(pws, page_dict)) == 1


def test_the_same_tall_ink_between_two_staves_of_one_system_is_not():
    pws = _pws([_staff(0, 500), _staff(1, 1000)])
    bottom = pws.staves[0].bottom_y
    for k in range(7):
        cv2.rectangle(pws.page.rgb, (300 + k * 60, bottom + 40), (300 + k * 60 + 45, bottom + 40 + int(3.1 * SPACING)),
                      (0, 0, 0), -1)
    assert find_candidates(pws, _page_dict([0, 1], [(100, 2000)])) == []


def test_the_pair_a_2_is_a_candidate_two_unrelated_marks_are_not():
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    cv2.rectangle(pws.page.rgb, (300, 700), (320, 730), (0, 0, 0), -1)
    cv2.rectangle(pws.page.rgb, (330, 695), (352, 735), (0, 0, 0), -1)
    pd = _page_dict([0, 1], [(100, 2000)])
    assert len(find_candidates(pws, pd)) == 1
    far = _pws([_staff(0, 500), _staff(1, 1200)])
    cv2.rectangle(far.page.rgb, (300, 700), (320, 730), (0, 0, 0), -1)
    cv2.rectangle(far.page.rgb, (500, 695), (522, 735), (0, 0, 0), -1)
    assert find_candidates(far, pd) == []


# -- the scan reading order -------------------------------------------------

def test_the_slow_rung_is_asked_only_where_the_fast_rung_saw_letters():
    """Time: Surya spends ~0.5 s a crop, mostly on beams and stubs. It reads the
    tight crop of a candidate Tesseract saw letters in, and nothing else."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    _word(pws.page.rgb, 300, 700)                                   # a word
    cv2.rectangle(pws.page.rgb, (900, 700), (960, 740), (0, 0, 0), -1)
    cv2.rectangle(pws.page.rgb, (990, 700), (1050, 740), (0, 0, 0), -1)
    cv2.rectangle(pws.page.rgb, (1080, 700), (1140, 740), (0, 0, 0), -1)   # junk blocks
    page_dict = _page_dict([0, 1], [(100, 2000)])
    asked = []

    def tess(crops):
        return ["x" for _c in crops]                                 # one letter: debris

    def surya(crops):
        asked.append(len(crops))
        return ["" for _ in crops]

    surya.tight = surya
    words, info = DT.read_directions(pws, page_dict, readers=[("surya", surya), ("tesseract", tess)],
                                  scan_order=True)
    assert words == []
    assert info["n_lettered"] == 0 and asked == []                  # a single letter: not enough
    assert info["n_candidates"] >= 1


def test_the_tight_crop_gets_a_second_chance_the_wide_crop_did_not():
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    _word(pws.page.rgb, 300, 700)
    cv2.rectangle(pws.page.rgb, (250, 650), (256, 790), (0, 0, 0), -1)       # a barline in the wide crop's pad
    page_dict = _page_dict([0, 1], [(100, 2000)])

    def tess(crops):                    # reads only a crop with no barline in it
        out = []
        for c in crops:
            cols = np.where((c < 128).any(axis=(0, 2)))[0]
            clear_left = len(cols) > 0 and cols.min() > 0.15 * c.shape[1]
            out.append("cresc." if clear_left else "")
        return out

    words, info = DT.read_directions(pws, page_dict, readers=[("tesseract", tess), ("surya", lambda c: [""] * len(c))],
                                  scan_order=True)
    assert [w.text for w in words] == ["cresc."]
    assert words[0].reader == "tesseract-tight"


def test_the_a_due_hit_goes_to_the_staff_below_the_gap_it_is_printed_in():
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    page_dict = _page_dict([0, 1], [(100, 2000)])
    top1 = pws.staves[1].top_y
    cand = TextCandidate(0, 0, (300, top1 - 70, 350, top1 - 30), "below", 2)
    d = DirectionText(0, 0, 300, "a 2", "part", "below", ("a2",), "surya-tight")
    accepted = {0: d}
    DT._give_a_due_to_the_staff_below(pws, page_dict, [cand], accepted)
    assert accepted[0].staff_index == 1
    other = DirectionText(0, 0, 300, "cresc.", "dynamic", "below", ("cresc",), "tesseract")
    accepted = {0: other}
    DT._give_a_due_to_the_staff_below(pws, page_dict, [cand], accepted)
    assert accepted[0].staff_index == 0                              # only `a2` is reattributed


def test_two_readings_of_the_same_ink_on_one_staff_are_one_word():
    c_small = TextCandidate(0, 0, (300, 700, 360, 730), "below", 3)
    c_big = TextCandidate(0, 0, (290, 695, 460, 735), "below", 5)
    mk = lambda t: DirectionText(0, 0, 300, t, "expression", "below", (t,), "tesseract")
    accepted = {0: mk("piu"), 1: mk("piu,")}
    DT._drop_overlapping_readings([c_small, c_big], accepted)
    assert list(accepted) == [0]                                     # the smaller box stays


# -- round 4 ----------------------------------------------------------------

def test_a_cluster_on_two_baselines_is_split_into_two_words():
    """Litolff p6: `Basso` with `pizz.` printed a line lower beside it."""
    from tools.omr.tests.test_direction_text import _letter
    basso = [_letter(100 + i * 40, y=40) for i in range(5)]
    pizz = [_letter(320 + i * 40, y=40 + int(0.8 * SPACING)) for i in range(4)]
    rows = DT._cluster_into_words(basso + pizz, SPACING, DEFAULT_BAND_CONFIG)
    assert len(rows) == 2
    same_line = [_letter(100 + i * 40, y=40) for i in range(9)]       # control: one word stays one
    assert len(DT._cluster_into_words(same_line, SPACING, DEFAULT_BAND_CONFIG)) == 1


def test_a_short_bold_word_of_two_blobs_is_a_candidate():
    """Litolff p15 `Vcl.`: `Vc` fused into one blob plus the `l`."""
    from tools.omr.tests.test_direction_text import _letter
    pair = [_letter(100, y=40, w=50, h=40), _letter(160, y=34, w=14, h=58)]
    assert len(DT._cluster_into_words(pair, SPACING, DEFAULT_BAND_CONFIG)) == 1


def test_the_dynamic_a_marking_includes_is_linked_and_not_exported_twice():
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    det = {"category": "dynamic", "class": "dynamicF", "bbox_page": [440, 700, 30, 36],
           "cell_key": "ck", "detector_index": 3}
    page_dict = _page_dict([0, 1], [(100, 2000)], {0: [det]})
    cand = TextCandidate(0, 0, (300, 700, 420, 734), "below", 4)
    d = DirectionText(0, 0, 300, "più f", "expression", "below", ("più",), "tesseract", ("f",))
    acc = {0: d}
    DT._link_dynamics(page_dict, [cand], acc, SPACING)
    assert acc[0].dynamic_links[0][:2] == ("ck", 3)
    assert det["in_direction_word"] is True
    from tools.omr.export import measure_dynamics
    assert measure_dynamics([{"class": "dynamicF", "bbox": [440, 700, 30, 36], "in_direction_word": True}]) == []
    far = {"category": "dynamic", "class": "dynamicP", "bbox_page": [1500, 700, 30, 36]}
    pd2 = _page_dict([0, 1], [(100, 2000)], {0: [far]})
    acc2 = {0: d}
    DT._link_dynamics(pd2, [cand], acc2, SPACING)
    assert acc2[0].dynamic_links == () and "in_direction_word" not in far      # not beside it: not linked


def test_the_budget_prices_the_direction_reader_at_the_measured_figure():
    from tools.omr.staged import budget
    assert budget.DIRECTION_READER_S_PER_PAGE < 60.0
