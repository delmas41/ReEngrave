"""lane-stem-end-head -- the head at an orphan stem's end READ from the page ink (flag OMR_STEM_END_HEAD_INK, default OFF)."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from tools.omr.staged import stem_end_heads as SEH
from tools.omr.staged.gather import head_interior_white, notehead_ink_under

SP = 16.0


def page(lines=(100, 116, 132, 148, 164)):
    img = np.full((320, 400), 255, np.uint8)
    for y in lines:
        img[y:y + 2, 20:380] = 0
    return img


def black_head(img, cx, cy):
    cv2.ellipse(img, (cx, cy), (10, 7), -20, 0, 360, 0, -1)


def stem(img, x, y0, y1):
    img[y0:y1, x:x + 2] = 0


def read(img, stem_page, end):
    return SEH.ink_head_at_end(img, stem_page, end, SP, [], head_interior_white, notehead_ink_under)


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(SEH.STEM_END_HEAD_INK_ENV, raising=False)
    assert SEH.ink_enabled() is False
    for v in ("1", "true", "on"):
        monkeypatch.setenv(SEH.STEM_END_HEAD_INK_ENV, v)
        assert SEH.ink_enabled() is True


def test_black_head_left_of_an_up_stem_is_read():
    img = page()
    black_head(img, 150, 140)
    stem(img, 159, 80, 140)
    got = read(img, (160.0, 80.0, 140.0), "bottom")
    assert got["head"], got
    assert got["value"] == "filled"
    tx0, ty0, tx1, ty1 = got["trimmed"]
    assert tx0 < 150 < tx1 and ty0 < 140 < ty1


def test_nothing_at_the_other_end_and_wrong_side_is_not_a_head():
    img = page()
    black_head(img, 150, 140)
    stem(img, 159, 80, 140)
    assert not read(img, (160.0, 80.0, 140.0), "top")["head"]
    img2 = page()
    black_head(img2, 172, 140)                      # the blot is RIGHT of an up-stem: not its head
    stem(img2, 159, 80, 140)
    assert not read(img2, (160.0, 80.0, 140.0), "bottom")["head"]


def test_a_beam_end_is_not_one_head():
    """2.210: a beam end at the tip is ink, but not ONE head"""
    img = page(lines=())
    img[134:142, 100:200] = 0                       # a beam, 0.5 sp thick, running past the head's width both ways
    stem(img, 159, 80, 142)
    got = read(img, (160.0, 80.0, 142.0), "bottom")
    assert not got["head"]


def test_a_bare_stem_tip_is_no_head():
    img = page()
    stem(img, 159, 80, 140)
    assert not read(img, (160.0, 80.0, 140.0), "bottom")["head"]


def test_combine():
    ink = {"head": True, "trimmed": [140, 133, 161, 147]}
    assert SEH.combine([141, 134, 160, 146], ink)[0] == "agree"
    assert SEH.combine([241, 134, 260, 146], ink)[0] == "abstain"
    assert SEH.combine([141, 134, 160, 146], {"head": False, "why": "not_one_head:too_wide"}) == (
        "abstain", "rerun_only_ink_reads:not_one_head:too_wide")
    assert SEH.combine(None, ink)[0] == "ink_only"
    assert SEH.combine(None, {"head": False, "why": "no_head_ink"})[0] == "none"


def test_ink_head_class():
    assert SEH.ink_head_class("filled", 100.0, 100.0, 50.0) == "noteheadBlackOnLine"
    assert SEH.ink_head_class("hollow", 150.0, 100.0, 50.0) == "noteheadHalfInSpace"
