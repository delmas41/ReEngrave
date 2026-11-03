"""ROADMAP 2.254 round 3 (STAGED, flag OMR_HAIRPIN_REACH, default OFF) -- synthetic shapes whose answer is known by construction:
(1) a barline / staff line coming into a word's box is whited out of the OCR crop, a letter's own stroke never is
(`direction_text.through_line_mask`); (2) a READ word's box is cut to its own ink round a hairpin it holds (`hairpin_reach.word_ink_boxes`);
(3) the claim readout reads a word's `ink_boxes` in place of its OCR box."""
from __future__ import annotations

import types

import numpy as np

from tools.omr import direction_text as DT
from tools.omr.staged import claim_order as CO
from tools.omr.staged import hairpin_reach as HR

SP = 20.0


def _binary(h=400, w=400):
    return np.full((h, w), 255, np.uint8)        # 0 = ink, as `PageImage.binary`


def test_barline_into_the_box_is_whited_out_letter_kept():
    b = _binary()
    b[0:400, 300:304] = 0                        # a barline the whole page tall
    b[150:175, 290:299] = 0                      # a letter touching it, inside the box
    b[140:178, 200:204] = 0                      # a letter's tall stem, inside the box only
    box = (190, 140, 302, 180)
    m = DT.through_line_mask(b, box, SP, (180, 130, 320, 190))
    assert m[150 - 130, 301 - 180]               # the barline goes
    assert not m[160 - 130, 292 - 180]           # the letter beside it stays
    assert not m[150 - 130, 202 - 180]           # a letter stroke ending inside its box stays


def test_short_barline_piece_inside_the_box_is_not_a_line():
    b = _binary()
    b[145:175, 300:304] = 0                      # a stroke 1.5 sp, wholly inside the box: a letter
    m = DT.through_line_mask(b, (190, 140, 310, 180), SP, (180, 130, 320, 190))
    assert not m.any()


def test_staff_line_through_the_box_is_whited_out():
    b = _binary()
    b[150:153, 0:400] = 0                        # a staff line across the page
    b[155:175, 220:230] = 0
    m = DT.through_line_mask(b, (200, 145, 260, 178), SP, (195, 140, 265, 185))
    assert m[151 - 140, 240 - 195] and not m[165 - 140, 225 - 195]


def test_crops_unchanged_without_the_flag():
    b = _binary()
    b[0:400, 300:304] = 0
    rgb = np.repeat(b[:, :, None], 3, axis=2)
    page = types.SimpleNamespace(rgb=rgb, binary=b)
    c = DT.TextCandidate(0, 0, (250, 140, 302, 180), "below", 1)
    assert np.array_equal(DT.tight_crop_for(page, c, SP), DT.tight_crop_for(page, c, SP, lines=False))
    assert (DT.tight_crop_for(page, c, SP, lines=True) == 0).sum() < (DT.tight_crop_for(page, c, SP) == 0).sum()


def _cresc_entry(x0, y0, x1, y1):
    bb = [float(x0), float(y0), float(x1), float(y1)]
    return {"bbox_page_px": bb, "segments": HR.arms("crescendo", bb), "band_px": HR.band_px(SP)}


def _draw_arms(b, e, thick=2):
    for xa, ya, xb, yb in e["segments"]:
        for t in np.linspace(0.0, 1.0, 400):
            x, y = int(round(xa + t * (xb - xa))), int(round(ya + t * (yb - ya)))
            b[y - thick // 2:y + thick // 2 + 1, x] = 0


def test_word_box_cut_round_a_hairpin_over_its_letters():
    b = _binary()
    e = _cresc_entry(150, 100, 300, 120)
    _draw_arms(b, e)
    b[100:150, 110:135] = 0                      # 'p', tall, left of the hairpin
    b[128:150, 160:180] = 0                      # 'e' under the hairpin
    b[128:150, 190:210] = 0                      # 's'
    boxes = HR.word_ink_boxes(b, (110, 100, 210, 150), [e], SP)
    assert boxes is not None and len(boxes) == 2
    ii = np.zeros_like(b, bool)
    ii[np.where(b == 0)] = True
    for x0, y0, x1, y1 in boxes:                 # no rectangle holds an arm pixel
        seg = ii[int(y0):int(y1), int(x0):int(x1)]
        yy, xx = np.nonzero(seg)
        d = HR.dist_to_segments(xx + x0 + 0.5, yy + y0 + 0.5, e["segments"]) if yy.size else np.array([9e9])
        assert d.min() > HR.ARM_BAND_SPACES * SP
    covered = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in boxes)
    assert covered >= 25 * 50 + 2 * 20 * 22      # every letter kept


def test_word_box_untouched_without_a_hairpin():
    b = _binary()
    b[128:150, 160:180] = 0
    assert HR.word_ink_boxes(b, (150, 120, 200, 160), [_cresc_entry(300, 300, 380, 320)], SP) is None
    assert HR.word_ink_boxes(b, (150, 120, 200, 160), [], SP) is None


def test_claim_readout_reads_ink_boxes_in_place_of_the_ocr_box():
    rows = {"observations": [
        {"quantity": "direction_word", "detail": {"bbox_page_px": [0, 0, 100, 50], "ink_boxes": [[0, 0, 20, 50], [40, 30, 100, 50]]}},
        {"quantity": "direction_word", "detail": {"bbox_page_px": [200, 0, 300, 50]}}]}
    assert CO.reader_boxes(rows) == [[0.0, 0.0, 20.0, 50.0], [40.0, 30.0, 100.0, 50.0], [200.0, 0.0, 300.0, 50.0]]
