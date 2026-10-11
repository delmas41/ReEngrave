"""`OMR_STEM_FINDER` (ROADMAP 2.84): the stem finder's repairs, one by one.

Drawn ink on synthetic cells (SPACING 100 canonical px per staff space), so the
tests read the real `detect_stems` chain and need no PDF, weights or LilyPond.

Each repair has (a) the case it repairs, (b) a POSITIVE CONTROL IN THE SAME
CLASS that must still be refused/kept (a refusal test with no positive control
passes by refusing everything: CLAUDE.md 6b), and (c) the flag-OFF identity:
this file is on the path every stem arm proves faithful before reporting.

RED FIRST: every `test_*_repairs_*` asserts the repaired result and the same
call with the repair NOT named (`stem_finder=frozenset()`, the shipped reader)
asserts the unrepaired result in the paired `*_off_*` test; the repairs were
written against that unrepaired reader, which returns nothing on the fused
cell (see the commit message).
"""

from __future__ import annotations

import numpy as np

from tools.omr.line_detection import (
    STEM_FINDER_ENV,
    detect_stems,
    mark_kind,
    stem_finder_repairs,
)
from tools.omr.types import MeasureCell

LINE_YS = [100, 200, 300, 400, 500]
OFF = frozenset()
ALL = frozenset({"thin_run", "pair_evidence", "refuse_owned"})


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((900, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 900),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _rect(img, x0, y0, x1, y1):
    img[y0:y1, x0:x1] = 0


def _fused_third(img, heads=True, stem=True):
    """Two heads a third apart (1 space centre to centre => ~2 spaces of ink),
    stem up at their right edge, 5 spaces tall: the run is 1.3 spaces wide."""
    if heads:
        _rect(img, 320, 600, 450, 800)        # two fused heads: 130 x 200
    if stem:
        _rect(img, 442, 200, 450, 800)        # the stem, 8 px wide, up


def _boxes(dets):
    return [(d.x_canonical, d.y_canonical, d.width_canonical,
             d.height_canonical) for d in dets]


# ── thin_run ────────────────────────────────────────────────────────────────

def test_fused_third_off_is_the_shipped_reader_and_finds_nothing():
    assert detect_stems(_cell(_fused_third), stem_finder=OFF) == []


def test_thin_run_repairs_the_fused_third_to_the_stem_alone():
    out = detect_stems(_cell(_fused_third), stem_finder=frozenset({"thin_run"}))
    assert len(out) == 1
    x, y, w, h = _boxes(out)[0]
    assert 440 <= x <= 444 and w <= 12          # the stem, not the 130 px run
    assert y <= 205 and y + h >= 795            # its whole length


def test_thin_run_control_a_solid_block_has_no_stem_inside():
    # same width, same height as the fused run, nothing protruding
    cell = _cell(lambda i: _rect(i, 320, 200, 450, 800))
    assert detect_stems(cell, stem_finder=frozenset({"thin_run"})) == []


def test_thin_run_control_heads_without_a_stem_stay_refused():
    cell = _cell(lambda i: _fused_third(i, stem=False))
    assert detect_stems(cell, stem_finder=frozenset({"thin_run"})) == []


def test_thin_run_control_two_tall_columns_are_not_one_stem():
    def paint(img):
        _rect(img, 320, 200, 328, 800)
        _rect(img, 440, 200, 448, 800)
        _rect(img, 320, 600, 448, 800)
    # the head stack joins two tall columns at the bottom: two bands, refused
    assert detect_stems(_cell(paint), stem_finder=frozenset({"thin_run"})) == []


def test_thin_run_does_not_change_what_a_plain_stem_returns():
    cell = _cell(lambda i: _rect(i, 400, 200, 408, 600))
    assert _boxes(detect_stems(cell, stem_finder=OFF)) == \
        _boxes(detect_stems(cell, stem_finder=frozenset({"thin_run"})))


# ── the flag ────────────────────────────────────────────────────────────────

def test_flag_default_is_empty_and_a_typo_leaves_it_empty(monkeypatch):
    monkeypatch.delenv(STEM_FINDER_ENV, raising=False)
    assert stem_finder_repairs() == frozenset()
    monkeypatch.setenv(STEM_FINDER_ENV, "")
    assert stem_finder_repairs() == frozenset()
    monkeypatch.setenv(STEM_FINDER_ENV, "Thin_Run, refuse_owned")
    assert stem_finder_repairs() == frozenset({"thin_run", "refuse_owned"})


def test_flag_reaches_detect_stems(monkeypatch):
    cell = _cell(_fused_third)
    monkeypatch.setenv(STEM_FINDER_ENV, "")
    assert detect_stems(cell) == []
    monkeypatch.setenv(STEM_FINDER_ENV, "thin_run")
    assert len(detect_stems(cell)) == 1


# ── pair_evidence ───────────────────────────────────────────────────────────

def _stem_beside_a_sharp(img):
    """A real stem (5 spaces) with a sharp's vertical 0.5 space to its left
    that lies on an accidental box. Without the box the pair rule drops both."""
    _rect(img, 400, 200, 408, 700)            # the stem
    _rect(img, 350, 400, 357, 620)            # the sharp's vertical, 2.2 sp


def test_pair_rule_alone_drops_the_stem_beside_a_sharp():
    assert detect_stems(_cell(_stem_beside_a_sharp), stem_finder=OFF) == []


def test_pair_evidence_keeps_the_stem_when_the_partner_is_on_an_accidental():
    marks = [("accidental", (330, 380, 60, 260))]
    out = detect_stems(_cell(_stem_beside_a_sharp), marks=marks,
                       stem_finder=frozenset({"pair_evidence"}))
    assert len(out) == 1 and _boxes(out)[0][0] == 400


def test_pair_evidence_control_a_whole_sharp_is_still_dropped():
    def paint(img):
        _rect(img, 350, 400, 357, 620)
        _rect(img, 375, 400, 382, 620)        # a sharp's two strokes
    marks = [("accidental", (330, 380, 80, 260))]
    assert detect_stems(_cell(paint), marks=marks,
                        stem_finder=frozenset({"pair_evidence"})) == []


def test_pair_evidence_without_boxes_is_the_shipped_pair_rule():
    assert detect_stems(_cell(_stem_beside_a_sharp), marks=None,
                        stem_finder=frozenset({"pair_evidence"})) == []




def test_mark_kind_vocabulary():
    assert mark_kind("clefG") == "clef" and mark_kind("clefCAlto") == "clef"
    assert mark_kind("keyFlat") == "key" and mark_kind("timeSig8") == "digit"
    assert mark_kind("flag8thDown") == "flag" and mark_kind("restWhole") == "rest"
    assert mark_kind("accidentalSharp") == "accidental"
    assert mark_kind("noteheadBlackInSpace") is None and mark_kind("stem") is None
