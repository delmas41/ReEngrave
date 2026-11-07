"""ROADMAP 2.274 round 3: the page-ink arc reader keeps an arc whole where it touches other ink. Drawn canvases only (no detector, no record, no library).
Every test has a CONTROL that fails the other way, so the mechanism can fail: the same drawing with the touching ink made not arc-like is not read as an arc."""
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


def _whole(res, x0, x1, tol=10):
    return any(r["box"][0] <= x0 + tol and r["box"][2] >= x1 - tol for r in res["runs"])


def test_an_arc_cut_by_a_barline_inside_a_words_rectangle_is_still_an_arc():
    # lane brief 4 / tile 1: a long "cresc. - - -" rectangle ran over the arc; the carve at the barline left its left half as a component wholly inside it
    c = _bow(_canvas(), 100, 400, 200, 40)
    c[:, 246:254] = 255                              # the carved barline column through the middle
    word = ("word", [20.0, 140.0, 680.0, 215.0])
    res = PA.read_runs(c, SP, [], [], [word])
    assert _whole(res, 100, 400)
    # CONTROL: the same rectangle over letters (several strokes in a column, wide as a word) still claims them: no run
    t = _canvas()
    for x0 in range(100, 400, 30):
        t[150:200, x0:x0 + 5] = 0                    # stems of letters
        t[150:155, x0:x0 + 22] = 0                   # a bar over them: every column holds several strokes at the stems
        t[195:200, x0:x0 + 22] = 0
    txt = PA.read_runs(t, SP, [], [], [word])
    assert not txt["runs"]


def test_fragments_of_one_arc_are_joined_across_a_gap_that_claims_ink_but_a_straight_line_is_not():
    # tiles 5-8: the arc is lost where it touches a stem / head / flag: the pieces either side are one curve
    c = _bow(_canvas(), 100, 460, 200, 50)
    blank = [("flag8thUp", [250.0, 120.0, 330.0, 215.0])]
    c[120:215, 250:331] = 0                          # the claimed mark's own ink fills the gap
    res = PA.read_runs(c, SP, [], blank, [], raw=c)
    assert _whole(res, 100, 460)
    # CONTROL: two collinear straight strokes either side of the same claimed block are one straight line, not an arc (no bow)
    s = _canvas()
    s[198:203, 100:250] = 0
    s[198:203, 331:460] = 0
    s[120:215, 250:331] = 0
    res2 = PA.read_runs(s, SP, [], blank, [], raw=s)
    assert not res2["runs"]


def test_an_arc_on_a_staff_line_is_read_from_the_unerased_raster():
    # tiles 2-4: where the arc lies on a staff line the eraser takes the arc with the line; on the raw raster the ink is thicker than the line is
    raw = _bow(_canvas(), 100, 460, 200, 36, thick=7)
    line_ys = [150.0, 166.0, 182.0, 198.0, 214.0]
    for y in line_ys:
        raw[int(y) - 1:int(y) + 1, :] = 0            # five staff lines, 2 px thick
    canvas = np.full_like(raw, 255)
    canvas[:] = raw
    for y in line_ys:
        canvas[int(y) - 2:int(y) + 3, :] = 255       # the eraser takes the line AND whatever lies in its band
    with_raw = PA.read_runs(canvas, SP, line_ys, [], [], raw=raw)
    assert _whole(with_raw, 100, 460, tol=20)
    # CONTROL: the same lines with no arc on them make no run
    bare = _canvas()
    for y in line_ys:
        bare[int(y) - 1:int(y) + 1, :] = 0
    cb = bare.copy()
    for y in line_ys:
        cb[int(y) - 2:int(y) + 3, :] = 255
    assert not PA.read_runs(cb, SP, line_ys, [], [], raw=bare)["runs"]


def test_a_run_inside_a_header_rectangle_that_is_not_along_its_ink_is_not_the_headers():
    # tile 7: a tie that starts right after the key signature lies inside the key's rectangle, and is not along any of its strokes
    c = _bow(_canvas(), 200, 330, 200, 24)
    c[100:200, 40:60] = 0                            # the key signature's own ink, far to the left of the tie
    area = [("key_signature", [20.0, 90.0, 260.0, 210.0])]
    ink = PA.blank_mask(c == 0, [], area, SP)
    pts = np.array([[x, 200 - 24 * 4 * ((x - 200) / 130.0) * (1 - (x - 200) / 130.0)] for x in range(200, 331, 5)], float)
    assert PA.hugs_a_claimed_mark(pts, [], area, SP, ink) is None
    # CONTROL: a run lying along the key's own stroke is its rim
    rim = np.array([[x, 150.0] for x in range(30, 80, 5)] + [[x, 150.0] for x in range(80, 100, 5)], float)
    c2 = _canvas()
    c2[148:153, 30:100] = 0
    ink2 = PA.blank_mask(c2 == 0, [], [("key_signature", [20.0, 90.0, 260.0, 210.0])], SP)
    assert PA.hugs_a_claimed_mark(rim, [], [("key_signature", [20.0, 90.0, 260.0, 210.0])], SP, ink2) == "claimed_header"


def test_a_thick_run_that_does_not_taper_is_a_beam_and_the_heavy_middle_of_a_slur_is_an_arc():
    # the thick pass reads a slur whose middle is heavier than a column run; a beam is as thick all along and is refused
    slur = _canvas()
    xs = np.arange(100, 460)
    t = (xs - 100) / 360.0
    ys = 200 - 40 * 4 * t * (1 - t)
    for x, y, tt in zip(xs, ys, t):
        h = int(round(3 + 8 * 4 * tt * (1 - tt)))     # 3 px at the ends, 11 px (0.7 sp) in the middle
        slur[int(round(y)) - h // 2:int(round(y)) + h // 2 + 1, x] = 0
    res = PA.read_runs(slur, SP, [], [], [], raw=slur)
    assert _whole(res, 100, 460, tol=20)
    beam = _canvas()
    for x in range(100, 460):
        y = 200 - int((x - 100) * 0.03)
        beam[y - 5:y + 6, x] = 0                      # 11 px thick everywhere, nearly level
    for x in range(100, 460, 90):
        beam[200 - 40:200 + 15, x:x + 4] = 0          # stems cut it into pieces the linker could join
    assert not PA.read_runs(beam, SP, [], [], [], raw=beam)["runs"]
