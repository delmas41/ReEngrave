"""Geometry head templates are drawn WIDE and tilt UP-TO-THE-RIGHT for a
positive tilt (lane-ledger-template-fix, 2026-10-04). Synthetic, fast.

Bug the first review sheet had: `measure_head_tilt._fit_axes` returned the
cv2 fit's raw (minor, major) pair, which the sheet drew as (width, height)
-> upright ovals."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np

from tools.omr.annotate import head_template as ht

_MHT = Path(__file__).resolve().parents[3] / "benchmarks/omr-local-staff-2026-09/measure_head_tilt.py"


def _load_mht():
    import sys
    sys.path.insert(0, str(_MHT.parent))
    spec = importlib.util.spec_from_file_location("measure_head_tilt_t", _MHT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _extent(poly):
    return (poly[:, 0].max() - poly[:, 0].min(), poly[:, 1].max() - poly[:, 1].min())


def test_outline_tilt0_is_wider_than_tall():
    poly = ht.geometry_outline_poly(100, 100, 30.0, 0.0)
    w, h = _extent(poly)
    assert abs(w - 1.3 * 30) <= 2 and abs(h - 1.0 * 30) <= 2


def test_positive_tilt_top_is_right_of_centre():
    poly = ht.geometry_outline_poly(100, 100, 30.0, 30.0)
    top = poly[poly[:, 1] == poly[:, 1].min()][:, 0].mean()
    assert top > 100 + 3
    tmpl = ht.build_geometry_template("filled", "raw", 30.0, None, 3.0)
    ys, xs = np.nonzero(tmpl.img > 0)
    assert xs[ys == ys.min()].mean() > ht.CANONICAL_W / 2.0 + 2
    t0 = ht.build_geometry_template("filled", "raw", 0.0, None, 3.0)
    ys, xs = np.nonzero(t0.img > 0)
    assert (xs.max() - xs.min()) > (ys.max() - ys.min())


def test_fit_axes_reports_long_then_short_matching_tilt_axis():
    mht = _load_mht()
    im = np.zeros((200, 200), np.uint8)
    cv2.ellipse(im, (100, 100), (65, 50), -30, 0, 360, 255, -1)
    long_, short_ = mht._fit_axes(im > 0)
    assert long_ > short_
    assert abs(long_ - 130) < 4 and abs(short_ - 100) < 4
    # and the tilt is read in the same (up-to-the-right) convention
    assert abs(mht._fit_angle(im > 0) - 30) < 2


def _staff_with_head(head_y_in_spaces_from_top, spacing=20.0, tilt=0.0, thickness=3):
    """5 horizontal lines `spacing` apart (`thickness` px) and a filled head at
    a half-step position (0 = top line, 1 = first space, 2 = second line...)."""
    img = np.full((260, 400), 255, np.uint8)
    top = 60.0
    for i in range(5):
        y = int(round(top + i * spacing))
        img[y - thickness // 2:y - thickness // 2 + thickness, :] = 0
    cy = top + head_y_in_spaces_from_top * spacing / 2.0
    poly = ht.geometry_outline_poly(200, cy, spacing, tilt)
    cv2.fillPoly(img, [poly.astype(np.int32)], 0)
    return img, (200 - 13, cy - 10, 200 + 13, cy + 10)


def test_head_on_a_line_is_on_line_and_head_in_a_space_is_in_space():
    """The control heads' failure mode (round 4): an in-staff head ON a line
    answered in_space because the in_space template put its two lines at
    +-1 sp (where an on-line head's NEIGHBOURING staff lines are) instead of
    +-0.5 sp (the lines that bound the space the head sits in)."""
    tm = ht.build_geometry_templates({"filled": 0.0, "hollow": 0.0}, {}, 3.0 * 30.0 / 20.0)
    for off in (0.0, 0.25, -0.25):   # real boxes sit up to ~0.25 sp off the head
        for pos, want in ((2, "on_line"), (4, "on_line"), (6, "on_line"),
                          (1, "in_space"), (3, "in_space"), (5, "in_space"), (7, "in_space")):
            img, box = _staff_with_head(pos)
            box = (box[0], box[1] + off * 20, box[2], box[3] + off * 20)
            m = ht.match_head_template(img, box, 20.0, tm, kind="filled",
                                       dx_range_spaces=0.4, head_ink_mode="opening",
                                       decide="staged")
            assert m["best_variant"] == want, (off, pos, m["best_variant"], m["score_on"], m["score_space"])
            # a decision, not a coin flip: the winning line term clearly beats the other
            assert m["margin"] >= 0.08, (off, pos, m["margin"])


def test_thick_scanned_lines_still_decide_line_vs_space():
    """Litolff prints staff lines ~0.4 sp thick. A correlation over a band the
    ink fills completely has zero variance and scores exactly 0.0 (a
    computation, not a measurement), so on-line and in-space heads came back as
    coin flips. The line term must read ink COVERAGE of the line rows."""
    tm = ht.build_geometry_templates({"filled": 0.0, "hollow": 0.0}, {}, 8.0 * 30.0 / 20.0)
    for pos, want in ((2, "on_line"), (4, "on_line"), (1, "in_space"), (3, "in_space"), (5, "in_space")):
        img, box = _staff_with_head(pos, thickness=8)
        m = ht.match_head_template(img, box, 20.0, tm, kind="filled", dx_range_spaces=0.4,
                                   head_ink_mode="opening", decide="staged", line_term="coverage")
        assert m["best_variant"] == want, (pos, m["best_variant"], m["score_on"], m["score_space"])
        assert m["margin"] >= 0.08, (pos, m["margin"])


def test_horizontal_search_moves_the_oval_onto_an_offset_head():
    """Round 3: the box sits 6 px left of the printed head. Vertical-only
    cannot fix that; a +-0.4 sp horizontal search lands on the ink."""
    spacing = 20.0
    img = np.full((200, 300), 255, np.uint8)
    poly = ht.geometry_outline_poly(156, 100, spacing, 0.0)
    cv2.fillPoly(img, [poly.astype(np.int32)], 0)
    box = (150 - 14, 100 - 11, 150 + 14, 100 + 11)
    tm = ht.build_geometry_templates({"filled": 0.0, "hollow": 0.0}, {}, 4.0)
    moved = ht.match_head_template(img, box, spacing, tm, kind="filled",
                                   dx_range_spaces=0.4, head_ink_mode="opening")
    assert abs(moved["center_x"] - 156) < abs(150 - 156) - 2
