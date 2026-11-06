"""ROADMAP 2.274 step 1: the page-ink arc reader (`staged/page_arcs.py`) on a drawn canvas -- no detector, no record, no library.

The controls that can fail: a bowed arc drawn ACROSS a stem and a barline-sized hole reads as ONE run; a straight line, a hairline and a run on a staff-line row
read as none; two arcs meeting at a blanked head read as two; a detector arc box is a witness only (a run is found with no box at all)."""
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


def test_one_arc_across_a_stem_is_one_run():
    c = _bow(_canvas(), 100, 500, 200, 40)
    c[60:260, 300:306] = 0                         # a stem through the arc: a hole the track bridges
    res = PA.read_runs(c, SP, [], [], [])
    assert len(res["runs"]) == 1
    r = res["runs"][0]
    assert r["box"][0] <= 105 and r["box"][2] >= 495      # whole, end to end, not cut at the stem


def test_a_straight_line_a_hairline_and_a_staff_row_are_not_arcs():
    c = _canvas()
    c[120:125, 50:650] = 0                         # straight and long
    c[200, 50:300] = 0                             # one pixel thick: a staff line's residue
    res = PA.read_runs(c, SP, [], [], [])
    assert res["runs"] == []


def test_two_arcs_meeting_at_a_blanked_head_are_two_runs():
    c = _canvas()
    _bow(c, 100, 300, 200, 40)
    _bow(c, 300, 500, 200, 40)
    c[185:215, 288:312] = 0                        # the head both end on
    boxes = [("noteheadBlackInSpace", [286, 183, 314, 217])]
    res = PA.read_runs(c, SP, [], boxes, [])
    assert len(res["runs"]) == 2


def test_a_detector_box_is_only_a_witness():
    c = _bow(_canvas(), 100, 500, 200, 40)
    res = PA.read_runs(c, SP, [], [], [])
    by_run, alone = PA.witnesses_of(res["runs"], [], SP)
    assert len(res["runs"]) == 1 and by_run[res["runs"][0]["id"]] == [] and alone == []      # a run with no box
    box = dict(subject="glyph/0/0/0/0/0", cls="slur", box=[100.0, 150.0, 500.0, 205.0])
    by_run, alone = PA.witnesses_of(res["runs"], [box], SP)
    assert by_run[res["runs"][0]["id"]] == ["glyph/0/0/0/0/0"] and alone == []
    far = dict(subject="glyph/0/0/0/1/0", cls="tie", box=[100.0, 20.0, 500.0, 60.0])           # a box over blank paper: no run answers it
    _by, alone = PA.witnesses_of(res["runs"], [far], SP)
    assert alone == [far]


def test_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv(PA.ENV, raising=False)
    assert not PA.enabled()
    monkeypatch.setenv(PA.ENV, "1")
    assert PA.enabled()
