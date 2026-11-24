"""ROADMAP 2.342 -- the stroke map measures a stroke in its OWN staff's spacing (`OMR_STROKE_SPACE_OWN_STAFF`, `stroke_map.LocalStaff`).

STAGED GATHER. Built from the REAL page (CLAUDE rule 7): the ink strips are Litolff p2 system 0 staff 1 and p6 system 0 staves 0 and 2 at 600
dpi, three staff spaces above and below the recorded lines (`data_stroke_space_own_staff_2_342.npz`). On main the walk across p2 staff 1 took
a column inside the treble clef with two lines run together and held it flat to the staff's right end: 11.76 px where the lines stand 15.75
apart (323 strokes on that page). The control fails there with the flag OFF.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from tools.omr.staged import stroke_map as SM

DATA = Path(__file__).with_name("data_stroke_space_own_staff_2_342.npz")


def _strip(name):
    z = np.load(DATA)
    h, w = (int(v) for v in z[name + "_shape"])
    ink = np.unpackbits(z[name + "_ink"], axis=1)[:, :w].astype(np.float32)
    return ink, [float(v) for v in z[name + "_lines"]]


def _staff(name, on, monkeypatch):
    if on:
        monkeypatch.setenv(SM.STROKE_SPACE_OWN_STAFF_ENV, "1")
    else:
        monkeypatch.setenv(SM.STROKE_SPACE_OWN_STAFF_ENV, "0")
    ink, lines = _strip(name)
    return SM.LocalStaff(ink, lines, 15.75), ink, lines


def _spaces(ls, w):
    return np.array([(ls.lines_at(x)[4] - ls.lines_at(x)[0]) / 4.0 for x in range(300, w - 200, 10)])


@pytest.mark.parametrize("name", ["p2_s0_st1", "p6_s0_st2"])
def test_every_x_measures_its_own_staff_spacing(name, monkeypatch):
    ls, ink, lines = _staff(name, True, monkeypatch)
    own = (lines[4] - lines[0]) / 4.0
    sp = _spaces(ls, ink.shape[1])
    assert np.all(np.abs(sp / own - 1.0) <= 0.05), (sp.min(), sp.max(), own)
    assert abs(float(np.median(sp)) / own - 1.0) <= 0.03


@pytest.mark.parametrize("name", ["p2_s0_st1", "p6_s0_st2"])
def test_control_fails_on_main(name, monkeypatch):
    """The control can fail: with the flag OFF the clef column's space is held across the staff."""
    ls, ink, lines = _staff(name, False, monkeypatch)
    own = (lines[4] - lines[0]) / 4.0
    assert float(np.median(_spaces(ls, ink.shape[1]))) < 0.8 * own


def test_a_staff_that_was_right_stays_identical(monkeypatch):
    off, _ink, _l = _staff("p6_s0_st0", False, monkeypatch)
    on, _ink, _l = _staff("p6_s0_st0", True, monkeypatch)
    assert on._xs == off._xs and on._rows == off._rows


def test_two_lines_run_together_are_never_the_staff():
    """The clef column main took on p2 staff 1 (page rows): lines 4 and 5 2.4 px apart."""
    nominal = [549.0, 565.0, 581.0, 596.0, 612.0]
    assert not SM._at_own_spacing([555.9, 570.5, 587.0, 601.6, 604.0], nominal)
    assert SM._at_own_spacing([555.0, 570.8, 586.6, 602.4, 618.2], nominal)
    assert not SM._at_own_spacing([555.0, 567.0, 579.0, 591.0, 603.0], nominal)       # a staff a quarter short: another spacing
