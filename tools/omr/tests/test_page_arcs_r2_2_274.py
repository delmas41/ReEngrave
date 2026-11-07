"""ROADMAP 2.274 round 2: the page-ink arc reader closes each miss at its cause. Drawn canvases only (no detector, no record, no library). Each test has a
CONTROL that must fail the other way, so it can fail: the same drawing with the mechanism's input changed gives the old answer."""
import numpy as np

from tools.omr.staged import page_arcs as PA

SP = 16.0


def _canvas(h=300, w=700):
    return np.full((h, w), 255, np.uint8)


def _bow(c, x0, x1, y_end, rise, thick=5):
    xs = np.arange(x0, x1 + 1)
    t = (xs - x0) / float(x1 - x0)
    ys = y_end - rise * 4 * t * (1 - t)
    for x, y in zip(xs, ys):
        c[int(round(y)) - thick // 2:int(round(y)) + thick // 2 + 1, x] = 0
    return c


def _whole(res, x0, x1):
    return any(r["box"][0] <= x0 + 8 and r["box"][2] >= x1 - 8 for r in res["runs"])


def test_an_arc_crosses_a_dynamic_on_its_own_slope_but_not_a_head():
    # THICK-ROUGH bucket, "arcs through stems cut by blanked boxes": a claimed mark claims its own ink, not the arc's
    c = _bow(_canvas(), 100, 500, 200, 40)
    c[145:176, 270:340] = 0                        # a dynamic's glyph sits on the arc's apex (y 160), 4.4 sp wide
    through = PA.read_runs(c, SP, [], [("dynamicF", [268, 143, 342, 178])], [])
    assert _whole(through, 100, 500) and len(through["runs"]) == 1
    cut = PA.read_runs(c, SP, [], [("noteheadBlackInSpace", [268, 143, 342, 178])], [])      # CONTROL: a head is where an arc ENDS
    assert not _whole(cut, 100, 500)


def test_a_single_arc_with_its_apex_in_a_hole_is_one_run_but_two_touching_arcs_are_two():
    # ROUGH bucket: the cusp rule cut a short clean arc at the barline gap at its apex; the turn at the hole must be against the pieces' bow
    one = _bow(_canvas(), 100, 300, 200, 36)
    one[:, 196:206] = 255                          # a carved barline column through the apex
    r = PA.read_runs(one, SP, [], [], [])
    assert len(r["runs"]) == 1 and _whole(r, 100, 300)
    two = _canvas()
    _bow(two, 100, 300, 200, 36)
    _bow(two, 300, 500, 200, 36)                   # two arcs whose ends TOUCH (no hole): a V corner against both bows
    r2 = PA.read_runs(two, SP, [], [], [])
    assert len(r2["runs"]) == 2


def test_a_tie_cut_by_an_erased_staff_line_is_one_run():
    # "ties on staff lines": the eraser parts the arc where it lies on the line; the staff-line row is a crossing, not an end
    c = _bow(_canvas(), 100, 360, 200, 14, thick=7)      # r3: 7 px (0.44 sp); a UNIFORM 0.56-sp stroke is a beam by the r3 taper rule
    c[199:202, :] = 255                            # the erased band of a staff line through the tie
    joined = PA.read_runs(c, SP, [200.0], [], [])
    assert _whole(joined, 100, 360)
    unjoined = PA.read_runs(c, SP, [], [], [])     # CONTROL: no staff line known -> the old behaviour (the slivers are too thin for an arc)
    assert not _whole(unjoined, 100, 360)


def test_thickness_is_no_longer_a_knife_edge():
    # THICK bucket: a heavy print's slur (0.44 sp) was refused by a 0.42 median cap that duplicated the column cap; it is an arc
    c = _bow(_canvas(), 100, 500, 200, 40, thick=int(round(0.46 * SP)))
    res = PA.read_runs(c, SP, [], [], [])
    assert _whole(res, 100, 500)


def test_short_flat_runs_and_fermatas_are_not_arcs():
    # fakes: a ledger line / head base / beam stub (short, flat), a fermata (a hump with a dot under it)
    flat = _canvas()
    flat[120:126, 100:150] = 0
    flat[119, 100:104] = 0
    assert PA.short_and_flat(0.04, 3.0) and not PA.short_and_flat(0.4, 3.0) and not PA.short_and_flat(0.04, 6.0)
    hump = _bow(_canvas(), 200, 260, 150, -30)
    hump = _bow(_canvas(), 200, 262, 180, 18)
    dots = np.array([[231.0, 160.0]])
    res = PA.read_runs(hump, SP, [], [], [])
    assert len(res["runs"]) == 1
    pts = np.array(res["runs"][0]["pts"], float)
    top = float(pts[:, 1].min())
    dots = np.array([[231.0, top + 0.8 * SP]])
    assert PA.is_a_fermata(pts, dots, res["runs"][0]["sagitta_sp"], res["runs"][0]["width_sp"], SP)
    assert not PA.is_a_fermata(pts, np.array([[231.0, top + 4 * SP]]), res["runs"][0]["sagitta_sp"], res["runs"][0]["width_sp"], SP)      # CONTROL: a dot far under it


def test_an_arc_touching_a_dynamic_is_carried_on_into_it(monkeypatch):
    # "arcs through stems / claimed marks": the arc's start lies inside the dynamic's blanked box; the run follows its own slope back into it
    c = _bow(_canvas(), 100, 500, 200, 40)
    dyn = PA.read_runs(c, SP, [], [("dynamicF", [96, 150, 150, 215])], [])
    assert dyn["runs"][0]["box"][0] <= 110
    monkeypatch.setattr(PA, "EXT_ALL", 0)           # CONTROL: with the extension limited to what a dynamic / word claims, a head's box keeps the old cut
    head = PA.read_runs(c, SP, [], [("noteheadBlackInSpace", [96, 150, 150, 215])], [])
    assert head["runs"][0]["box"][0] >= 148 - 2
    monkeypatch.setattr(PA, "EXT_ALL", 1)           # and on, the same head is where the arc is attached to its note
    head_on = PA.read_runs(c, SP, [], [("noteheadBlackInSpace", [96, 150, 150, 215])], [])
    assert head_on["runs"][0]["box"][0] <= 110
