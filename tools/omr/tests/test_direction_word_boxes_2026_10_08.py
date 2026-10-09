"""ROADMAP 2.66: the candidate BOX of a direction word on a scan (STAGED).

Sean's round-3/4 misses (DECISIONS 2026-10-08) -- `Adagio`, `pizz.` -- were
words whose box covered only part of the print: letters fused to each other or
to a stem failed the letter tests (`agio.`, `zz.`), and stem stubs left by the
notehead subtraction stretched the box into the notes (`nee`, `val.`). Two
rules, both only under `refine_boxes` (the frozen legacy reader keeps its
boxes): a STUB is dropped from the letters, and a word GROWS over oversized ink
on its own line. Each rule is paired with the case it must leave alone.
"""
from __future__ import annotations

import numpy as np

from tools.omr import direction_text as DT

SP = 16.0   # one staff space, px


def _band(h=80, w=240):
    return np.zeros((h, w), np.uint8)


def _box(mask, x, y, w, h):
    mask[y:y + h, x:x + w] = 255


# ── stubs ───────────────────────────────────────────────────────────────────

def test_a_thin_stroke_running_into_erased_ink_is_a_stub():
    erased = _band()
    _box(erased, 50, 10, 16, 14)            # the blanked notehead
    stroke = (60, 24, 4, 20, 80)            # its stem, below it, touching
    assert DT._is_a_stub(stroke, erased, SP)


def test_the_same_stroke_with_nothing_erased_at_its_end_is_a_letter():
    erased = _band()
    _box(erased, 120, 10, 16, 14)           # a blanked glyph, but elsewhere
    stroke = (60, 24, 4, 20, 80)            # an `l` / `i`
    assert not DT._is_a_stub(stroke, erased, SP)


def test_a_fat_component_touching_erased_ink_is_not_a_stub():
    erased = _band()
    _box(erased, 50, 10, 16, 14)
    letter = (52, 24, 14, 14, 150)          # an `n` fused under an ornament
    assert not DT._is_a_stub(letter, erased, SP)


# ── growing along the line ──────────────────────────────────────────────────

def _word_band():
    """Three letters at x 100..160 on a line centred at y 40, and room left."""
    band = _band()
    letters = []
    for x in (100, 122, 144):
        _box(band, x, 32, 14, 16)
        letters.append((x, 32, 14, 16, 14 * 16))
    word = (100, 32, 158, 48, 3)
    return band, letters, word


def test_a_fused_pair_of_letters_beside_the_word_joins_it():
    band, letters, word = _word_band()
    _box(band, 58, 26, 40, 30)              # `Ad`: 2.5 x 1.9 spaces, 2 px gap
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out[0] == 58 and out[2] == 158


def test_without_its_own_letters_nothing_grows():
    band, _letters, word = _word_band()
    _box(band, 58, 26, 40, 30)
    out = DT._grow_along_baseline(word, [], band, np.zeros_like(band, bool), SP)
    assert out == word


def test_a_barline_beside_the_word_does_not_join_it():
    band, letters, word = _word_band()
    _box(band, 90, 6, 9, 70)                # 0.56 spaces wide, a scan's barline
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out == word


def test_a_detected_dynamic_beside_the_word_stays_the_dynamics():
    band, letters, word = _word_band()
    _box(band, 160, 26, 36, 40)             # the `f` of `più f`
    dynamic = np.zeros_like(band, bool)
    dynamic[20:72, 158:200] = True          # the detector's dynamic box
    out = DT._grow_along_baseline(word, letters, band, dynamic, SP)
    assert out == word
    # ... and the same ink, NOT boxed as a dynamic, does join (the control)
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out[2] == 196


def test_a_mass_off_the_words_line_does_not_join_it():
    band, letters, word = _word_band()
    _box(band, 60, 52, 38, 26)              # beside, but entirely below the centre line
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out == word


def test_find_candidates_keeps_the_legacy_boxes_by_default():
    import inspect
    sig = inspect.signature(DT.find_candidates)
    assert sig.parameters["refine_boxes"].default is False


def test_a_barline_fused_to_a_grown_letter_is_trimmed_off_the_box():
    """`pizz.` on Litolff p9: the `p` descender's foot runs into the barline, so
    the grown piece carries it and the box would start ON the barline -- the
    word filed a bar early. The column crossing the whole line is cut off."""
    band, letters, word = _word_band()
    _box(band, 70, 0, 6, 80)                # barline, through the whole line
    _box(band, 76, 30, 22, 20)              # `pi`, fused to it at the foot
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out[0] == 76 and out[2] == 158


def test_a_tall_letter_with_a_gap_under_it_is_not_trimmed():
    band, letters, word = _word_band()
    _box(band, 58, 30, 40, 20)              # `Ad`, shorter than the line
    _box(band, 60, 22, 4, 26)               # the `d` ascender ...
    _box(band, 60, 52, 4, 20)               # ... and a stem stub under it, 4 px apart
    out = DT._grow_along_baseline(word, letters, band, np.zeros_like(band, bool), SP)
    assert out[0] == 58


def test_a_sibling_window_is_filed_in_the_bar_of_the_word_it_echoes():
    """Litolff p9: `pizz.` read on staff 10 just right of a barline; the window
    looking for it on staff 8 is padded 0.3 spaces left of that x, across the
    barline, and was filed by its padded edge -- a bar early. The window looks
    for the SAME word at the SAME x, so it is filed where that x is."""
    import cv2
    from tools.omr.direction_text import (DEFAULT_BAND_CONFIG, DirectionText,
                                          TextCandidate, sibling_candidates)
    from tools.omr.tests.test_direction_text import SPACING, _page_dict, _pws, _staff
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    for x0, y0 in ((1004, 700), (1006, 1400)):          # a word just past the barline at 1000
        for k in range(6):
            cv2.rectangle(pws.page.rgb, (x0 + k * 30, y0), (x0 + k * 30 + 22, y0 + 34), (0, 0, 0), -1)
    page_dict = _page_dict([0, 1], [(100, 1000), (1000, 2000)])
    cands = [TextCandidate(0, 1, (1004, 700, 1154, 734), "below", 6)]
    accepted = {0: DirectionText(0, 1, 1004, "pizz.", "expression", "below", ("pizz",), "tesseract")}
    extra = sibling_candidates(pws, page_dict, DT._page_ink(pws.page), cands, accepted,
                               SPACING, DEFAULT_BAND_CONFIG)
    assert [c.staff_index for c in extra] == [1]
    assert extra[0].measure_index == 1


# ── a tempo word belongs to the staff BELOW it (Sean 2026-10-08) ──────────

def _two_staff_reading(category, terms, text, system_of_lower=0):
    from tools.omr.direction_text import DirectionText, TextCandidate
    from tools.omr.tests.test_direction_text import _page_dict, _pws, _staff
    pws = _pws([_staff(0, 500), _staff(1, 1000, system=system_of_lower)])
    page_dict = _page_dict([0, 1], [(100, 1000), (1000, 2000)])
    # printed in the gap under staff 0 (bottom line 660) and over staff 1 (top 1000)
    cands = [TextCandidate(0, 1, (1100, 760, 1300, 800), "below", 6)]
    accepted = {0: DirectionText(0, 1, 1100, text, category, "below", terms, "tesseract")}
    return pws, page_dict, cands, accepted


def test_a_tempo_word_in_the_gap_is_the_lower_staffs():
    """Litolff p9: the oboe's `Adagio`, printed in the gap ABOVE the oboe staff,
    was filed on the empty staff over it. Sean: 'it belongs to the staff
    beneath it ... tempo is always above the staff.'"""
    pws, page_dict, cands, accepted = _two_staff_reading("tempo", ("adagio",), "Adagio.")
    DT._give_tempo_to_the_staff_below(pws, page_dict, cands, accepted)
    d = accepted[0]
    assert (d.staff_index, d.measure_index, d.placement) == (1, 1, "above")
    assert cands[0].staff_index == 1


def test_an_expression_word_in_the_gap_stays_the_upper_staffs():
    pws, page_dict, cands, accepted = _two_staff_reading("expression", ("dolce",), "dolce")
    DT._give_tempo_to_the_staff_below(pws, page_dict, cands, accepted)
    assert (accepted[0].staff_index, accepted[0].placement) == (0, "below")


def test_a_tempo_word_under_a_systems_last_staff_stays_there():
    """No staff beneath it in the system: the foot of a system (Brahms p3
    `Allegro` under the basses) is not moved onto the next system."""
    pws, page_dict, cands, accepted = _two_staff_reading("tempo", ("allegro",), "Allegro",
                                                         system_of_lower=1)
    DT._give_tempo_to_the_staff_below(pws, page_dict, cands, accepted)
    assert (accepted[0].staff_index, accepted[0].placement) == (0, "below")
