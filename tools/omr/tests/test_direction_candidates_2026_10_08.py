"""Candidate-finder fixes from the 10 held-out scan pages (2026-10-08).

Each rule was stated before it was run; the page that motivates it is named.
"""
from __future__ import annotations

import cv2
import numpy as np

from tools.omr.direction_text import (
    DEFAULT_BAND_CONFIG, TextCandidate, _bands_for_page, _blank_detections,
    _cluster_into_words, _letter_components, crop_for)
from tools.omr.tests.test_direction_text import SPACING, _pws, _staff

CFG = DEFAULT_BAND_CONFIG


def test_the_crop_pad_does_not_readmit_ink_the_detector_named():
    """Brahms p7/p12: `p dolce` / `p cresc.` -- the dynamic `p` beside a word is
    blanked from the mask, but the crop's 1.3-space pad cut it back in from the
    original render, so the reader saw `v dolce` and the lexicon refused it."""
    pws = _pws([_staff(0, 500), _staff(1, 1200)])
    rgb = pws.page.rgb
    cv2.rectangle(rgb, (300, 700), (340, 740), (0, 0, 0), -1)        # a detected `p`, left of the word
    cv2.rectangle(rgb, (360, 700), (480, 734), (0, 0, 0), -1)        # the word
    cand = TextCandidate(0, 0, (360, 700, 480, 734), "below", 5)
    erase = np.zeros(rgb.shape[:2], np.uint8)
    erase[696:746, 296:346] = 255
    plain = crop_for(pws.page, cand, SPACING)
    guarded = crop_for(pws.page, cand, SPACING, erase=erase)
    assert (plain < 128).sum() > (guarded < 128).sum()               # control: the p IS in the plain crop
    s = guarded.shape[1] / (480 - 360 + 2 * int(round(1.3 * SPACING)))
    left = guarded[:, : int(8 * s)]                                  # the pad's far-left strip, where the p sits
    assert (left < 128).sum() == 0
    assert (guarded < 128).sum() > 0                                 # the word itself survives


def test_the_crop_is_unchanged_without_an_erase_mask():
    pws = _pws([_staff(0, 500)])
    cand = TextCandidate(0, 0, (300, 700, 480, 734), "below", 6)
    assert crop_for(pws.page, cand, SPACING).shape == crop_for(pws.page, cand, SPACING, erase=None).shape


def test_the_last_band_of_a_system_reaches_five_spaces():
    """Brahms p12: a `dim.` printed 3.4 spaces under the bottom staff sat 11 px
    beyond a 3-space reach and was never in any band."""
    staff = _staff(0, 500)
    bands = _bands_for_page(_pws([staff]), CFG)
    below = [b for _s, p, _t, b in bands if p == "below"][0]
    assert below >= staff.bottom_y + 4.9 * SPACING


def test_a_below_band_starts_close_to_its_staff():
    """Brahms p12 `dim.` under a clarinet: printed 0.2 spaces under the staff, inside
    the old 0.25-space clearance."""
    staff = _staff(0, 500)
    top = [t for _s, p, t, _b in _bands_for_page(_pws([staff]), CFG) if p == "below"][0]
    assert top - staff.bottom_y <= 0.12 * SPACING + 1


def test_a_fused_word_is_one_candidate():
    """Brahms p12 `dim.`: scan ink fuses the letters into ONE component 4.3
    spaces wide and 1.7 tall, which the 2-space letter width refused, leaving no
    cluster at all."""
    h, w = int(1.7 * SPACING), int(4.3 * SPACING)
    mask = np.zeros((int(4 * SPACING), int(12 * SPACING)), np.uint8)
    cv2.rectangle(mask, (100, 20), (100 + w, 20 + h), 255, -1)
    cv2.rectangle(mask, (120, 32), (230, 64), 0, -1)                    # fill ~0.7: a word, not a block
    comps = _letter_components(mask, SPACING, CFG)
    assert len(_cluster_into_words(comps, SPACING, CFG)) == 1


def test_a_wide_flat_rule_or_a_slur_is_still_refused():
    """Positive control for the fused-word rule: it must not admit a hairpin
    stroke (thin) or an arc (low fill)."""
    mask = np.zeros((int(4 * SPACING), int(12 * SPACING)), np.uint8)
    cv2.rectangle(mask, (100, 50), (100 + int(4.3 * SPACING), 50 + int(0.5 * SPACING)), 255, -1)
    cv2.ellipse(mask, (300, 120), (int(2.5 * SPACING), int(0.8 * SPACING)), 0, 180, 360, 255, 3)
    assert _cluster_into_words(_letter_components(mask, SPACING, CFG), SPACING, CFG) == []


def test_a_dynamic_with_a_word_letter_each_side_within_a_space_is_not_blanked():
    """Brahms p7 `espr.` under a horn: three letters read as dynamics, ink within
    0.5-0.9 spaces on both sides, so 1,100 of 1,958 ink pixels were erased."""
    mask = np.zeros((int(4 * SPACING), int(12 * SPACING)), np.uint8)
    box = (200, 40, 30, 36)
    gap = int(0.8 * SPACING)
    cv2.rectangle(mask, (box[0] - gap - 20, 40), (box[0] - gap, 76), 255, -1)
    cv2.rectangle(mask, (box[0] + box[2] + gap, 40), (box[0] + box[2] + gap + 20, 76), 255, -1)
    cv2.rectangle(mask, (box[0], 40), (box[0] + 30, 76), 255, -1)
    page_dict = {"systems": [{"staves": [{"measures": [{"detections": [
        {"category": "dynamic", "bbox_page": list(box)}]}]}]}]}
    out = _blank_detections(mask, page_dict, SPACING, CFG)
    assert out[40:76, 200:230].any()


def test_a_dynamic_with_ink_on_one_side_only_is_still_blanked():
    """Positive control: the `p` BEFORE a word has nothing to its left."""
    mask = np.zeros((int(4 * SPACING), int(12 * SPACING)), np.uint8)
    box = (200, 40, 30, 36)
    gap = int(0.8 * SPACING)
    cv2.rectangle(mask, (box[0] + box[2] + gap, 40), (box[0] + box[2] + gap + 20, 76), 255, -1)
    cv2.rectangle(mask, (box[0], 40), (box[0] + 30, 76), 255, -1)
    page_dict = {"systems": [{"staves": [{"measures": [{"detections": [
        {"category": "dynamic", "bbox_page": list(box)}]}]}]}]}
    assert not _blank_detections(mask, page_dict, SPACING, CFG)[40:76, 200:230].any()
