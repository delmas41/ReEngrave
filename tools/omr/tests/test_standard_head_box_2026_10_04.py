"""Standard-size head box (lane-standard-head-box, 2026-10-04): the box's SIZE
is the page's measured head, its CENTRE is where the template's free position
search lands -- never the detector's size, never a ledger-constrained height.
Synthetic, fast. The module is pure construction; nothing product-side imports
it, so the default reader path is unchanged."""
from __future__ import annotations

import math

import cv2
import numpy as np

from tools.omr.annotate import head_template as ht
from tools.omr.annotate import standard_head_box as shb

SPACING = 20.0
SHAPE = dict(width_sp=1.59, height_sp=1.05, tilt_deg=29.0)


def test_extents_of_a_tilted_oval_come_from_its_axes_not_a_constant():
    w0, h0 = shb.oval_extents_spaces(1.59, 1.05, 0.0)
    assert (round(w0, 3), round(h0, 3)) == (1.59, 1.05)
    w90, h90 = shb.oval_extents_spaces(1.59, 1.05, 90.0)
    assert abs(w90 - 1.05) < 1e-9 and abs(h90 - 1.59) < 1e-9
    w, h = shb.oval_extents_spaces(1.59, 1.05, 29.0)
    t = math.radians(29.0)
    assert abs(w - 2 * math.hypot(0.795 * math.cos(t), 0.525 * math.sin(t))) < 1e-9
    assert h < w and h > 1.05           # tilting a wide oval makes it taller
    # the sign of the tilt does not change an axis-aligned extent
    assert shb.oval_extents_spaces(1.59, 1.05, -29.0) == (w, h)


def test_box_is_centred_where_asked_and_sized_by_measurement():
    box = shb.standard_box_at(300.0, 200.0, SPACING, **SHAPE)
    w_sp, h_sp = shb.oval_extents_spaces(**SHAPE)
    assert abs((box[0] + box[2]) / 2 - 300.0) < 1e-9 and abs((box[1] + box[3]) / 2 - 200.0) < 1e-9
    assert abs((box[2] - box[0]) - w_sp * SPACING) < 1e-9
    assert abs((box[3] - box[1]) - h_sp * SPACING) < 1e-9


def _page(head_cx, head_cy, thickness=3):
    """Five staff lines and one filled, tilted head ON the third line."""
    img = np.full((260, 420), 255, np.uint8)
    for i in range(5):
        y = int(round(60 + i * SPACING))
        img[y - thickness // 2:y - thickness // 2 + thickness, :] = 0
    poly = ht.geometry_outline_poly(head_cx, head_cy, SPACING, SHAPE["tilt_deg"],
                                    SHAPE["width_sp"], SHAPE["height_sp"])
    cv2.fillPoly(img, [poly.astype(np.int32)], 0)
    return img


def _templates():
    kw = dict(width_spaces={"filled": SHAPE["width_sp"], "hollow": SHAPE["width_sp"]},
              height_spaces={"filled": SHAPE["height_sp"], "hollow": SHAPE["height_sp"]})
    return ht.build_geometry_templates(
        {"filled": SHAPE["tilt_deg"], "hollow": SHAPE["tilt_deg"]}, {},
        3.0 * ht.CANONICAL_PX_PER_SPACE / SPACING, **kw)


def _pooled():
    # the scorer's `templates_for_page({"pooled": tm}, 0)` returns this same dict
    return _templates()


HEAD = (200.0, 100.0)                       # the head ON the 3rd line (y = 100)


def _detector_box(dx_sp, dy_sp, w_sp, h_sp):
    cx, cy = HEAD[0] + dx_sp * SPACING, HEAD[1] + dy_sp * SPACING
    return (cx - w_sp * SPACING / 2, cy - h_sp * SPACING / 2, cx + w_sp * SPACING / 2, cy + h_sp * SPACING / 2)


def test_size_is_the_measured_size_and_centre_is_the_searched_one():
    img = _page(*HEAD)
    tm = _pooled()
    w_sp, h_sp = shb.oval_extents_spaces(**SHAPE)
    # a detector box too small and low (grabs the upper half), and one too big
    for det in (_detector_box(0.0, 0.3, 1.2, 0.55), _detector_box(0.2, -0.2, 2.2, 1.9)):
        r = shb.standard_head_box(img, det, SPACING, tm, SHAPE, "filled")
        assert r["placed"]
        # centre from the search: back on the head (< 0.12 sp)
        assert math.hypot(r["centre"][0] - HEAD[0], r["centre"][1] - HEAD[1]) / SPACING < 0.12, r["centre"]
        # size from the measurement, whatever the detector drew
        bx = r["box"]
        assert abs((bx[2] - bx[0]) - w_sp * SPACING) < 1e-6 and abs((bx[3] - bx[1]) - h_sp * SPACING) < 1e-6
        assert abs((bx[0] + bx[2]) / 2 - r["centre"][0]) < 1e-6
        assert abs((bx[2] - bx[0]) - (det[2] - det[0])) > 1.0       # not the detector's size


def test_the_search_can_fail_so_the_test_above_means_something():
    """A start 1.2 sp off the head is outside the +-0.4 sp / +-1.5 sp search:
    the centre does NOT come back to the head (the control must be able to fail)."""
    img = _page(*HEAD)
    det = _detector_box(1.2, 0.0, 1.5, 1.2)
    r = shb.standard_head_box(img, det, SPACING, _pooled(), SHAPE, "filled")
    err = math.hypot(r["centre"][0] - HEAD[0], r["centre"][1] - HEAD[1]) / SPACING
    assert err > 0.5, err


def test_inputs_are_not_touched():
    img = _page(*HEAD)
    before = img.copy()
    det = (180.0, 95.0, 205.0, 112.0)
    shb.standard_head_box(img, det, SPACING, _pooled(), SHAPE, "filled")
    assert det == (180.0, 95.0, 205.0, 112.0) and np.array_equal(img, before)


def test_a_search_with_no_answer_keeps_the_detector_centre_and_says_so():
    img = _page(*HEAD)
    det = (180.0, 95.0, 205.0, 112.0)
    r = shb.standard_head_box(img, det, SPACING, None, SHAPE, "filled")     # no templates
    assert r["placed"] is False
    assert r["centre"] == ((180.0 + 205.0) / 2, (95.0 + 112.0) / 2)


def test_pre_set_gate_constants():
    # set before any scoring (2026-10-04); a retune must be a new, dated decision
    assert shb.FIT_IOU_MIN == 0.70 and shb.FIT_OFFSET_MAX_SPACES == 0.15
    assert shb.DX_RANGE_SPACES == 0.4
