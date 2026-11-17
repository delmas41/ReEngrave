"""ROADMAP 2.274 round 4: the page-ink arc reader's fixes for the round-3 misses and fakes. Drawn canvases only (no detector, no record, no library).
Every test has a CONTROL that fails the other way, so the mechanism can fail."""
import numpy as np

from tools.omr.staged import page_arcs as PA

SP = 16.0


def _canvas(h=300, w=700):
    return np.full((h, w), 255, np.uint8)


def _band(c, x0, x1, y_end, rise, thick):
    """A bowed band; `thick(t)` gives its thickness (px) at t in [0, 1]."""
    xs = np.arange(x0, x1 + 1)
    for x in xs:
        t = (x - x0) / float(x1 - x0)
        y = y_end - rise * 4 * t * (1 - t)
        h = max(1, int(round(thick(t))))
        c[int(round(y)) - h // 2:int(round(y)) - h // 2 + h, x] = 0
    return c


def _covers(res, x0, x1, tol=12):
    return any(r["box"][0] <= x0 + tol and r["box"][2] >= x1 - tol for r in res["runs"])


def test_a_long_flat_lens_slur_is_an_arc_but_a_uniform_band_of_the_same_bow_is_not():
    # 20 sp long, bow 3% of its width: thin at both ends, 6 px (0.4 sp) in the middle
    lens = _band(_canvas(), 100, 420, 200, 10, lambda t: 1 + 5 * np.sin(np.pi * t))
    assert _covers(PA.read_runs(lens, SP, [], [], []), 100, 420)
    # CONTROL: the same bow and length at a constant thickness (a line, a hairpin leg, a beam) is refused as straight
    flat = _band(_canvas(), 100, 420, 200, 10, lambda t: 5)
    res = PA.read_runs(flat, SP, [], [], [], keep_rejected=True)
    assert not res["runs"] and res["why"].get("straight", 0) >= 1


def test_the_taper_cut_does_not_pass_a_line_that_bows_less_than_two_percent():
    lens_straight = _band(_canvas(), 100, 420, 200, 4, lambda t: 1 + 5 * np.sin(np.pi * t))      # bow 1.2%: still a line however it tapers
    assert not PA.read_runs(lens_straight, SP, [], [], [])["runs"]


def _raw(h=200, w=400):
    return np.zeros((h, w), bool)


def test_a_run_on_a_beams_raw_ink_with_stems_at_both_ends_is_a_beam_and_a_slur_is_not():
    raw = _raw()
    raw[100:112, 60:300] = True                      # a beam 12 px (0.75 sp) thick
    raw[40:112, 60:66] = True                        # two stems standing on it
    raw[40:112, 294:300] = True
    pts = [(x, 106.0, 4.0) for x in range(70, 291, 4)]
    assert PA._raw_beam_like(dict(pts=pts), raw, SP)
    # CONTROL 1: the same beam with no stems is a beam only for an ink-only run (need_stems False), never for a witnessed one
    nostem = _raw()
    nostem[100:112, 60:300] = True
    assert not PA._raw_beam_like(dict(pts=pts), nostem, SP)
    assert PA._raw_beam_like(dict(pts=pts), nostem, SP, need_stems=False)
    # CONTROL 2: a slur's own raw ink is thin (here 5 px, 0.3 sp): never a beam
    thin = _raw()
    thin[100:105, 60:300] = True
    thin[40:105, 60:66] = True
    thin[40:105, 294:300] = True
    assert not PA._raw_beam_like(dict(pts=[(x, 102.0, 4.0) for x in range(70, 291, 4)]), thin, SP, need_stems=False)


def test_a_wedge_is_not_an_arc_and_a_lens_is():
    wedge = dict(pts=[(float(x), 100.0, float(max(1, 9 - (x - 100) // 12))) for x in range(100, 220)])         # 9 px at one end, a point at the other
    lens = dict(pts=[(float(x), 100.0, float(1 + 6 * np.sin(np.pi * (x - 100) / 120.0))) for x in range(100, 220)])
    assert PA._is_wedge(wedge, SP)
    assert not PA._is_wedge(lens, SP)


def test_a_ring_that_no_detector_mark_overlaps_is_a_glyph_claimed_before_arcs_and_an_open_arc_piece_is_not():
    ink = np.zeros((200, 400), bool)
    yy, xx = np.ogrid[:200, :400]
    r = np.hypot(yy - 60, xx - 80)
    ink |= (r <= 14) & (r >= 9)                      # an "O": a ring, 1.75 sp across
    blank = PA.blank_mask(ink, [], [], SP)
    assert blank[ink].all()
    # CONTROL 1: the same ring is left to the detector's own marks when one overlaps it (a hollow head), and when glyphs are not asked for
    assert not PA.blank_mask(ink, [], [], SP, glyphs=False)[ink].any()
    assert not PA.blank_mask(ink, [("noteheadHalf", [60.0, 40.0, 100.0, 80.0])], [], SP)[ink & ~PA.blank_mask(ink, [("noteheadHalf", [60.0, 40.0, 100.0, 80.0])], [], SP, glyphs=False)].any()
    # CONTROL 2: an arc piece with a hook has no ring and is not claimed
    hook = np.zeros((200, 400), bool)
    hook[100:104, 100:160] = True
    hook[100:124, 100:104] = True
    assert not PA.blank_mask(hook, [], [], SP)[hook].any()


def test_a_box_far_wider_than_its_class_blanks_nothing():
    ink = np.zeros((200, 400), bool)
    ink[100:104, 50:250] = True                       # an arc 12 sp long under a false "accidentalFlat" box 12 sp wide
    wide = PA.blank_mask(ink, [("accidentalFlat", [50.0, 90.0, 250.0, 114.0])], [], SP)
    assert not wide[ink].any()
    # CONTROL: a flat-sized box (1 sp wide) over the same ink does blank it
    narrow = PA.blank_mask(ink, [("accidentalFlat", [100.0, 90.0, 116.0, 114.0])], [], SP)
    assert narrow[100:104, 100:116].all()


def test_a_zig_zag_through_letters_is_not_an_arc_and_a_smooth_bow_is():
    x = np.arange(0, 50)
    smooth = dict(pts=[(float(a), 100.0 - 0.02 * a * (50 - a), 4.0) for a in x])
    assert PA._judge(smooth, SP, np.array([]))[0] == "arc"
    x = np.arange(0, 60)
    tri = 6.0 * (2 * np.abs(((x / 40.0) % 1.0) - 0.5) - 0.5) * 2          # a slow zig-zag: steps of 0.4 sp, smooth in every one-space window
    zig = dict(pts=[(float(a), 100.0 + tri[i], 4.0) for i, a in enumerate(x)])
    assert PA._judge(zig, SP, np.array([]))[0] == "bad_fit"
