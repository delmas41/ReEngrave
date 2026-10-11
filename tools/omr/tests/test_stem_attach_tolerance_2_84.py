"""ROADMAP 2.84, `OMR_STEM_FINDER=attach_tolerance`: a stem box standing within
one stem thickness of a notehead's box is that head's stem.

Four readers each re-derived "does this stem touch this head" as box overlap
with NO tolerance (`rhythm._stems_on`, `rhythm._stem_joined`,
`notehead_precision._stem_rows_on`, `stem_value.adjudicate_head_stem`); they
now share `geometry.stem_touches_head`. Brahms 317803 p0: four of Sean's
stemmed heads had their stem found 0.00, 0.02, 0.02 and 0.10 spaces off the
head box and filed `no_stem`.

Flag OFF is the shipped reader: an exact-overlap test, argument for argument.
The positive control for every refusal: the same geometry one notch wider
must still NOT attach (a tolerance that attaches everything is not one).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.omr.line_detection import STEM_FINDER_ENV
from tools.omr.staged import geometry as G
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.adjudicators import rhythm as RH

HEAD = (100.0, 100.0, 130.0, 100.0)               # x, y, w, h  (h = one space)


def _stem(gap: float):
    """A stem box whose left edge stands `gap` px right of the head's right edge."""
    return (HEAD[0] + HEAD[2] + gap, 20.0, 8.0, 300.0)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(STEM_FINDER_ENV, "attach_tolerance")


@pytest.fixture
def off(monkeypatch):
    monkeypatch.setenv(STEM_FINDER_ENV, "")


def test_off_exact_overlap_only(off):
    assert G.stem_touches_head(_stem(0.0), HEAD)
    assert not G.stem_touches_head(_stem(2.0), HEAD)


def test_on_a_stem_within_one_stem_thickness_attaches(on):
    assert G.stem_touches_head(_stem(0.0), HEAD)
    assert G.stem_touches_head(_stem(2.0), HEAD)
    assert G.stem_touches_head(_stem(0.12 * HEAD[3]), HEAD)


def test_on_control_a_stem_one_notch_wider_does_not(on):
    assert not G.stem_touches_head(_stem(0.12 * HEAD[3] + 1.0), HEAD)
    assert not G.stem_touches_head(_stem(0.5 * HEAD[3]), HEAD)


def test_tolerance_scales_with_the_head_not_a_constant(on):
    big = (100.0, 100.0, 260.0, 200.0)             # a head twice the size
    s = (big[0] + big[2] + 0.2 * 100.0, 20.0, 8.0, 300.0)   # 20 px off
    assert G.stem_touches_head(s, big)             # 20 <= 0.12 * 200
    assert not G.stem_touches_head(s, HEAD)        # 20 >  0.12 * 100


def test_tolerance_is_in_y_as_well(on):
    below = (HEAD[0] + 10, HEAD[1] + HEAD[3] + 5.0, 8.0, 200.0)
    assert G.stem_touches_head(below, HEAD)
    far = (HEAD[0] + 10, HEAD[1] + HEAD[3] + 40.0, 8.0, 200.0)
    assert not G.stem_touches_head(far, HEAD)


def _row(box):
    return SimpleNamespace(value=list(box), id="r")


def test_the_readers_share_it_rhythm_stems_on(on):
    assert RH._stems_on(HEAD, [_row(_stem(2.0))]) != []
    assert RH._stems_on(HEAD, [_row(_stem(40.0))]) == []


def test_the_readers_share_it_notehead_precision(on):
    assert NP._stem_rows_on(HEAD, [_row(_stem(2.0))]) != []
    assert NP._stem_rows_on(HEAD, [_row(_stem(40.0))]) == []


def test_off_the_readers_are_the_shipped_ones(off):
    assert RH._stems_on(HEAD, [_row(_stem(2.0))]) == []
    assert NP._stem_rows_on(HEAD, [_row(_stem(2.0))]) == []
