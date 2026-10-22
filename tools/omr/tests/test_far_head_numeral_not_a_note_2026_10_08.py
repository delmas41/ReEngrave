"""lane-numeral-not-a-note (Sean, DECISIONS 2026-10-08, `brahms 26/0/11/0/17`): a printed "2" boxed as a half notehead.

The far-head reader refuses (abstains `not_a_note:<reason>`, deletes nothing) a notehead-class box that is a number:
  * `on_numeral`     -- a detector fingering/tuplet digit box lies over it;
  * `numeral_shaped` -- its ink is a separate, numeral-sized mark that is not a solid oval.
Spacing is 16 px; a real head is ~1.3 sp = 21 px wide.
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH

SP = 16.0
CLS = "noteheadHalfInSpace"
BOX = (100.0, 100.0, 124.0, 122.0)


def _page(draw):
    img = np.full((220, 220), 255, np.uint8)
    draw(img)
    return img


def _two(img):
    cv2.putText(img, "2", (104, 121), cv2.FONT_HERSHEY_SIMPLEX, 0.95, 0, 3, cv2.LINE_AA)


def _oval(img):
    cv2.ellipse(img, (112, 111), (11, 8), -20, 0, 360, 0, -1)       # a solid oval head, ~1.4 sp wide


def _ring_with_slit(img):
    cv2.ellipse(img, (112, 111), (11, 8), -20, 0, 360, 0, -1)
    cv2.line(img, (104, 116), (120, 106), 255, 2)                   # a scanned half head: a thin white slit


def _shape(draw):
    return FH.isolated_ink_shape(_page(draw), BOX, SP)


def test_a_printed_two_is_numeral_shaped_and_refused():
    shape = _shape(_two)
    assert shape and shape["isolated"] and shape["solidity"] < FH.NUMERAL_SOLIDITY_MAX
    r = FH.not_a_note_reason(BOX, CLS, SP, ink_shape=shape)
    assert r and r["reason"] == "numeral_shaped" and "number" in r["words"]


def test_real_heads_are_not_refused_positive_control():
    """Same class, same box, same code path: a solid oval and a scanned half head (oval with a thin slit)."""
    for draw in (_oval, _ring_with_slit):
        shape = _shape(draw)
        assert shape and shape["isolated"]
        assert FH.not_a_note_reason(BOX, CLS, SP, ink_shape=shape) is None


def test_a_head_joined_to_a_staff_line_is_never_refused_by_shape():
    def joined(img):
        _two(img)
        cv2.line(img, (60, 112), (170, 112), 0, 2)                  # a line through it: not isolated, so no verdict
    shape = _shape(joined)
    assert not shape["isolated"]
    assert FH.not_a_note_reason(BOX, CLS, SP, ink_shape=shape) is None


def test_a_numeral_box_over_the_head_refuses_it_and_a_bracket_class_is_ignored():
    r = FH.not_a_note_reason(BOX, CLS, SP, numeral_boxes=[(98.0, 98.0, 126.0, 124.0)])
    assert r and r["reason"] == "on_numeral"
    assert FH.not_a_note_reason(BOX, CLS, SP, numeral_boxes=[(0.0, 0.0, 30.0, 30.0)]) is None
    assert FH.NUMERAL_CLASS_PREFIXES == ("fingering", "tuplet")


def test_no_ink_shape_means_no_refusal():
    assert FH.not_a_note_reason(BOX, CLS, SP, ink_shape=None) is None
    assert FH.isolated_ink_shape(np.full((50, 50), 255, np.uint8), (10, 10, 30, 30), SP) is None
