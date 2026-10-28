"""ROADMAP 2.217 (`OMR_LEDGERS_FROM_STROKES`): the pure ledger reading (`ledger_strokes.read_head`) on hand-built strokes. Fast tier."""
import os
from unittest import mock

from tools.omr.staged import ledger_strokes as LS
from tools.omr.staged.adjudicators import ledger_read

SP = 20.0                      # page px per staff space; the top line is at y=100, so step s is at y = 100 + s*10


def y_of(step):
    return 100.0 + step * SP / 2.0


def rung(i, step, x0=90, x1=140, thick=0.15, kind="horizontal", state="", family=None, drift=0.0):
    return LS.RungView(i, "obs:%d" % i, kind, state, family, (x0, y_of(step), x1, y_of(step + drift)),
                       (step, step + drift), SP, (x1 - x0) / SP, thick)


def head(step, x=100, w=24):
    yc = y_of(step)
    return (x, yc - 10, x + w, yc + 10)


def test_on_second_ledger_above_counts_the_ink_not_the_spacing():
    # hand-drawn: the rungs stand at -2.2 and -4.6 half-steps, not -2 and -4 -- counted by order
    v = [rung(1, -2.2), rung(2, -4.6)]
    r = LS.read_head(v, head(-4.6), -4.0)
    assert r.fits and r.pos == -4 and "on ledger 2" in r.reason


def test_space_beyond_last_rung():
    v = [rung(1, -2.0)]
    r = LS.read_head(v, head(-3.0), -3.0)
    assert r.fits and r.pos == -3


def test_below_the_staff_counts_from_the_bottom_line():
    v = [rung(1, 10.1), rung(2, 12.0)]
    assert LS.read_head(v, head(12.0), 12.0).pos == 12
    assert LS.read_head(v, head(13.0), 13.0).pos == 13


def test_first_space_outside_needs_no_ledger_and_is_not_a_rung_reading():
    r = LS.read_head([], head(-1.0), -1.0)
    assert r.fits and r.how == "geometry"


def test_a_missing_ledger_is_a_refusal_never_a_position():
    # control that can fail: a head three spaces out with only the first rung drawn
    r = LS.read_head([rung(1, -2.0)], head(-6.0), -6.0)
    assert not r.fits and r.pos is None and "head_beyond_last_rung" in r.reason


def test_no_rungs_is_a_refusal_and_no_stroke_map_is_unread():
    assert not LS.read_head([], head(-4.0), -4.0).fits
    r = LS.read_head(None, head(-4.0), -4.0)
    assert not r.fits and r.unread


def test_a_stroke_another_mark_owns_is_not_a_rung():
    v = [rung(1, -2.0, state="decided", family="accidental")]
    assert not LS.read_head(v, head(-2.0), -2.0).fits
    v = [rung(1, -2.0, state="decided", family="ledger")]
    assert LS.read_head(v, head(-2.0), -2.0).fits


def test_a_contested_stroke_is_no_witness_and_is_named():
    r = LS.read_head([rung(1, -2.0, state="contested")], head(-2.0), -2.0)
    assert not r.fits and "contested_ink" in r.reason and r.contested


def test_a_beam_a_slur_and_a_stroke_inside_the_staff_are_not_rungs():
    assert not LS.read_head([rung(1, -2.0, thick=0.6)], head(-2.0), -2.0).fits
    assert not LS.read_head([rung(1, -2.0, kind="curve")], head(-2.0), -2.0).fits
    assert not LS.read_head([rung(1, 2.0)], head(2.0), -2.0).fits


def test_a_rung_that_does_not_span_the_head_does_not_count():
    assert not LS.read_head([rung(1, -2.0, x0=10, x1=50)], head(-2.0), -2.0).fits


def test_gap_in_chain_when_a_rung_could_hide():
    v = [rung(1, -2.0), rung(2, -7.0)]
    r = LS.read_head(v, head(-7.0), -7.0)
    assert not r.fits and "gap_in_chain" in r.reason


def test_flag_default_off_and_allow_list():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop(LS.ENV, None)
        assert not ledger_read.enabled()
    with mock.patch.dict(os.environ, {LS.ENV: "1"}):
        assert ledger_read.enabled()
    with mock.patch.dict(os.environ, {LS.ENV: "ture"}):
        assert not ledger_read.enabled()
