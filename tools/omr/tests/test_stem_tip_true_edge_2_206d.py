"""ROADMAP 2.206d (`OMR_STEM_TIP_TRUE_EDGE`): the stem-tip window starts at the stem STROKE's edge, and ink first touching the stem far
back from the tip is not a flag. Synthetic rasters, no PDF. Each OFF twin must show the fault (a control that can fail)."""
import numpy as np
import pytest

from tools.omr.staged import gather as G
from tools.omr.staged import stroke_map as SM

SP = 100.0
LINES = [200, 300, 400, 500, 600]


def _stem_img(width=25, x0=300, y0=100, y1=900, slur=True):
    img = np.full((1000, 700), 255, dtype=np.uint8)
    img[y0:y1, x0:x0 + width] = 0
    if slur:        # ink hugging the stem's right side near the tip, thicker than the finder's core: stem side, not a flag
        img[y0 + 150:y0 + 250, x0 + width:x0 + width + 20] = 0
    return img


def test_true_edges_measures_the_stroke_not_the_core():
    img = _stem_img(slur=False)
    res = SM.map_strokes(img, SP, LINES)
    got = SM.stem_true_edges(res, (312, 100, 4, 800))          # the finder's 4 px core of a 25 px stem
    assert got is not None and abs(got[0] - 300) <= 2 and abs(got[1] - 325) <= 2


def test_true_edges_refuses_a_wide_fused_stroke():
    img = _stem_img(width=90, slur=False)
    res = SM.map_strokes(img, SP, LINES)
    assert SM.stem_true_edges(res, (330, 100, 4, 800)) is None


def test_true_edges_none_without_a_stroke():
    img = np.full((1000, 700), 255, dtype=np.uint8)
    img[100:900, 100:104] = 0
    res = SM.map_strokes(img, SP, LINES)
    assert SM.stem_true_edges(res, (500, 100, 4, 800)) is None


def test_window_off_counts_the_stems_own_side_and_true_edge_does_not():
    img = _stem_img(slur=False)
    core = (312.0, 316.0)
    off = G.stem_tip_window(img, core[0], core[1], 100.0, 1.0, SP)
    on = G.stem_tip_window(img, 300.0, 325.0, 100.0, 1.0, SP)
    assert off["right"] > 0.3 and off["found"] is False or off["right"] > on["right"]    # the fault: stem ink read as density
    assert on["right"] == 0.0 and on["found"] is False


def test_root_beyond_tip_only_with_the_flag(monkeypatch):
    img = np.full((1000, 700), 255, dtype=np.uint8)
    img[100:900, 300:312] = 0
    img[100 + 270:100 + 300, 312:342] = 0           # a stub touching the stem 2.7 sp from the tip
    monkeypatch.delenv("OMR_STEM_TIP_TRUE_EDGE", raising=False)
    off = G.stem_tip_ink(img, 300.0, 312.0, 100.0, 1.0, SP)
    monkeypatch.setenv("OMR_STEM_TIP_TRUE_EDGE", "1")
    on = G.stem_tip_ink(img, 300.0, 312.0, 100.0, 1.0, SP)
    assert off["found"] is None and off["why"] == "ink_not_flag_shaped"
    assert on["found"] is False and on["why"] == "root_beyond_tip"


def test_a_real_flag_at_the_tip_is_still_read(monkeypatch):
    img = np.full((1000, 700), 255, dtype=np.uint8)
    img[100:900, 300:312] = 0
    img[100:170, 312:372] = 0                        # a hook leaving the tip itself, 0.6 sp out, 0.7 sp deep
    monkeypatch.setenv("OMR_STEM_TIP_TRUE_EDGE", "1")
    on = G.stem_tip_ink(img, 300.0, 312.0, 100.0, 1.0, SP)
    assert on["found"] is True
