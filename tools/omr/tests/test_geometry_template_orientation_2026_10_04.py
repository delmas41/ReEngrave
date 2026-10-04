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
