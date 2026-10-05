"""lane-standard-box-hollow (2026-10-04): a half note's counter is filled before
the standard head box's fit; an open ring is closed first; a filled head is
returned untouched (the SAME array)."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from tools.omr.annotate import standard_head_box as shb

SP, T = 16.0, 4.0          # staff spacing, staff-line thickness (px)
LONG, SHORT = 1.59, 1.05   # measured head axes (spaces)


def _page(kind, gap=0):
    g = np.full((120, 120), 255, np.uint8)
    c = (60, 60)
    axes = (int(LONG * SP / 2), int(SHORT * SP / 2))
    cv2.ellipse(g, c, axes, -29, 0, 360, 0, -1)
    if kind in ("closed", "open"):
        inner = (axes[0] - 5, axes[1] - 5)
        cv2.ellipse(g, c, inner, -29, 0, 360, 255, -1)
    if kind == "open" and gap:
        # cut a gap through the ring's wall at the upper right
        cv2.line(g, (60 + 4, 60 - 4), (60 + 20, 60 - 12), 255, gap)
    return g, (c[0] - 13, c[1] - 9, c[0] + 13, c[1] + 9)


def _iou_with_oval(img):
    ink = (img <= 128).astype(np.uint8)
    n, lab = cv2.connectedComponents(ink)
    blob = lab == lab[60, 60 - 8] if lab[60, 52] else lab == 1
    oval = np.zeros(img.shape, np.uint8)
    cv2.ellipse(oval, (60, 60), (int(LONG * SP / 2), int(SHORT * SP / 2)), -29, 0, 360, 1, -1)
    oval = oval.astype(bool)
    return float((blob & oval).sum() / (blob | oval).sum())


def _fill(g, box, hollow):
    return shb.fill_counter(g, box, SP, T, SHORT, LONG, hollow)


def test_closed_half_note_counter_filled_and_fit_passes():
    g, box = _page("closed")
    raw = _iou_with_oval(g)                      # the hole costs the fit (RED before)
    out, info = _fill(g, box, True)
    assert info["pockets"], info
    assert _iou_with_oval(out) >= 0.90 and raw < _iou_with_oval(out) - 0.15
    assert out is not g and (g[60, 60] == 255)   # the page itself is not edited


def test_open_ended_half_note_closed_then_filled():
    g, box = _page("open", gap=3)
    # control: the counter is NOT enclosed as printed (the gap leaks it)
    out_raw, info_raw = _fill(g, box, False)
    assert not info_raw["pockets"] and out_raw is g
    out, info = _fill(g, box, True)
    assert info["pockets"] and info["close_diameter"] == int(2 * T + 1)
    assert _iou_with_oval(out) >= 0.85


def test_filled_head_returns_the_same_array():
    g, box = _page("filled")
    for hollow in (False, True):
        out, info = _fill(g, box, hollow)
        assert out is g and not info["pockets"]


def test_speckle_hole_in_a_black_head_is_not_a_counter():
    g, box = _page("filled")
    g[60, 60] = 255                               # a one-pixel pinhole
    out, info = _fill(g, box, False)
    assert out is g and not info["pockets"]


def test_gap_wider_than_two_strokes_is_not_bridged():
    g, box = _page("open", gap=12)                # a different mark, not a gap in a wall
    out, info = _fill(g, box, True)
    # the notch is not bridged: the filled pixels never reach the gap's outer end
    assert out[60 - 11, 60 + 18] == g[60 - 11, 60 + 18] == 255
