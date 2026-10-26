"""ROADMAP 2.206 -- the staff-line eraser's walk must reach past its own crossing cut (`OMR_ERASER_FIX`).

Synthetic cells (no PDF). The bug: `_vertical_runs_through` walked `cap + 2` rows each side (cap = 0.35 sp, the THICKNESS
cap) while the crossing cut reaches 0.45 sp, so on a fat line a mark HANGING from the line (its run continues past the walk
on one side only) read as walk + the line's other half -- under the cut -- and was erased up to the walk. Every RED case
below has a twin that must NOT change, and the controls fail if the fix is removed (they run the OFF arm and assert the
damage is there).

The bug needs one more thing the first draft of these tests did not have, and the controls caught it: the run is read from the
ANCHOR (the ink row nearest Phase 1's nominal line y), so it fires only where the nominal y sits within ~7 px of the line's edge
AWAY from the mark (Litolff p16: "6 up and 37 down"). Phase 1 fits one straight y per line; a fat, drifting printed line puts
that y off its centre by several px. `_cell(offset=...)` draws the printed line `offset` px from the nominal y.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.omr import staff_line_removal as SLR
from tools.omr.types import MeasureCell

SP = 100
LINE_YS = [100, 200, 300, 400, 500]


def _cell(paint=None, thickness=26, width=600, wander=0, offset=0):
    h = 640
    img = np.full((h, width), 255, dtype=np.uint8)
    for y in LINE_YS:
        for x in range(width):
            dy = int(round(wander * np.sin(x / 90.0)))
            top = y + offset + dy - thickness // 2
            img[max(0, top):max(0, top) + thickness, x] = 0
    if paint is not None:
        paint(img)
    return MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0, image=img, image_no_staff=None,
                       bbox_page_px=(0, 0, width, h), staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0)


def _erase(cell, on, monkeypatch):
    if on:
        monkeypatch.setenv(SLR.ENV_ERASER_FIX, "1")
    else:
        monkeypatch.delenv(SLR.ENV_ERASER_FIX, raising=False)
    return SLR.remove_staff_lines_from_cell(cell, in_place=False)


def _hanging(line_centre, height, x0=250, x1=400, below=True, thickness=26):
    """A solid mark flush with the printed line's outer edge, extending `height` px away from it (a beam / whole rest hanging
    below the line: its top is the line's top; or a mark standing on the line: its bottom is the line's bottom)."""
    def paint(img):
        if below:
            a = line_centre - thickness // 2
            img[a:a + height, x0:x1] = 0
        else:
            b = line_centre - thickness // 2 + thickness
            img[b - height:b, x0:x1] = 0
    return paint


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(SLR.ENV_ERASER_FIX, raising=False)
    assert not SLR.eraser_fix_enabled()
    for v in ("1", "true", "yes", "on", " ON "):
        monkeypatch.setenv(SLR.ENV_ERASER_FIX, v)
        assert SLR.eraser_fix_enabled()
    for v in ("0", "", "off", "no"):
        monkeypatch.setenv(SLR.ENV_ERASER_FIX, v)
        assert not SLR.eraser_fix_enabled()


@pytest.mark.parametrize("cap,cut", [(35, 45.0), (35, 30.0), (10, 45.0), (28, 56.0), (1, 2.0), (35, 36.0)])
def test_walk_for_cut_contract(cap, cut):
    """A run that reaches the walk's bound on ONE side measures taller than the cut, whatever the other side."""
    walk = SLR.walk_for_cut(cap, cut)
    assert walk >= cap
    h = 400
    ink = np.zeros((h, 1), dtype=bool)
    y = 200
    ink[y:h, 0] = True                         # starts AT the anchor row, runs down forever: other side = 0
    heights, _, _, _ = SLR._vertical_runs_through(ink, y, walk)
    assert heights[0] > cut


# ---- RED cases (the bug) and their controls ------------------------------------------------------------------------

@pytest.mark.parametrize("height,label", [(64, "beam 0.64 sp hanging below a line (2.202b's tile)"),
                                         (50, "whole rest 0.5 sp hanging below line 4"),
                                         (60, "a mark 0.6 sp standing on a line")])
def test_a_mark_hanging_from_a_fat_line_survives(height, label, monkeypatch):
    below = "standing" not in label
    off_px = 8 if below else -8                 # nominal y 5 px inside the edge AWAY from the mark
    line = (400 if "line 4" in label else 300) + off_px
    cell = _cell(_hanging(line, height, below=below), offset=off_px)
    a = line - 13 if below else line + 13 - height
    region = slice(a, a + height)
    off = _erase(cell, False, monkeypatch)
    on = _erase(cell, True, monkeypatch)
    kept_off = (off[region, 300:350] == 0).mean()
    kept_on = (on[region, 300:350] == 0).mean()
    # CONTROL: the OFF arm shows the damage (fails if the bug is ever fixed without the flag, or the case stops reaching it)
    assert kept_off < 0.6, f"{label}: OFF kept {kept_off:.0%} -- the case no longer reproduces the bug"
    assert kept_on == 1.0, f"{label}: ON kept only {kept_on:.0%}"


def test_a_head_in_the_space_below_a_fat_line_keeps_its_top(monkeypatch):
    """A black head in a space touches the line above (Litolff p16, crop look): OFF cut ~0.17 sp off its top."""
    def paint(img):
        img[300:393, 250:340] = 0            # printed line 3 spans 295..320 (offset +8); the head touches it, down to line 4
    cell = _cell(paint, offset=8)
    off = _erase(cell, False, monkeypatch)
    on = _erase(cell, True, monkeypatch)
    assert (on[321:383, 250:340] == 0).all()
    assert (off[321:383, 250:340] == 0).mean() < 0.9      # control: OFF takes the head's top


# ---- twins that must NOT change ------------------------------------------------------------------------------------

@pytest.mark.parametrize("thickness", [2, 6, 8, 12, 16])
def test_thin_lines_byte_identical(thickness, monkeypatch):
    """Where the cut is no taller than the walk (2 x thickness <= cap + 2), the bug cannot fire and ON == OFF exactly."""
    def paint(img):
        img[200 - thickness // 2:260, 250:400] = 0      # a hanging block
        img[80:520, 450:458] = 0                         # a stem
        img[270:330, 100:160] = 0                        # a head on line 3
    for off_px in (0, thickness // 2 - 1, -(thickness // 2 - 1)):
        cell = _cell(paint, thickness=thickness, offset=off_px)
        assert np.array_equal(_erase(cell, False, monkeypatch), _erase(cell, True, monkeypatch))


@pytest.mark.parametrize("thickness", [20, 26, 30, 34])
def test_bare_fat_lines_still_erased(thickness, monkeypatch):
    cell = _cell(thickness=thickness, wander=3)
    on = _erase(cell, True, monkeypatch)
    assert int((on == 0).sum()) == 0


def test_a_mark_under_the_cut_is_erased_both_ways(monkeypatch):
    """The fix changes only columns whose run the old walk TRUNCATED: a run genuinely no taller than the cut (a fat line
    with a 10 px bump, total 36 <= 45) is still the line, erased in both arms -- the cut itself is not moved."""
    def paint(img):
        img[300 - 13 - 10:300 - 13, 250:300] = 0
    cell = _cell(paint)
    off, on = _erase(cell, False, monkeypatch), _erase(cell, True, monkeypatch)
    assert np.array_equal(off, on)
    assert (on[300 - 23:300 + 13, 250:300] == 255).all()


def test_a_crossing_stem_and_centred_beam_unchanged(monkeypatch):
    def paint(img):
        img[80:520, 300:308] = 0
        img[300 - 25:300 + 25, 350:550] = 0
    cell = _cell(paint, thickness=28)
    assert np.array_equal(_erase(cell, False, monkeypatch), _erase(cell, True, monkeypatch))


def test_on_equals_the_unbounded_rule(monkeypatch):
    """ON is exactly the documented rule -- erase a column's run iff its WHOLE run is no taller than the cut -- computed
    with an unbounded walk, on a busy synthetic cell of fat lines."""
    rng = np.random.RandomState(2206)

    def paint(img):
        for _ in range(60):
            x, y = rng.randint(0, 560), rng.randint(60, 560)
            img[y:y + rng.randint(3, 70), x:x + rng.randint(3, 60)] = 0
    cell = _cell(paint, thickness=27, wander=2, offset=7)
    on = _erase(cell, True, monkeypatch)
    # the same computation with the walk set to the whole cell
    orig = SLR.walk_for_cut
    monkeypatch.setattr(SLR, "walk_for_cut", lambda cap, cut: 10_000)
    unbounded = _erase(cell, True, monkeypatch)
    monkeypatch.setattr(SLR, "walk_for_cut", orig)
    assert np.array_equal(on, unbounded)
    assert not np.array_equal(on, _erase(cell, False, monkeypatch))   # control: OFF differs on this cell
