"""`OMR_STEM_AT_BAR_EDGE` (ROADMAP 2.155): a run refused at the cell edge whose END stands in a notehead's box is that head's stem.

2.153 tiles 4/14/16 (Litolff, Sean 2026-10-16: "there is no gap"): the last beamed eighth of a bar sits within 0.8 space of the
cell's right edge; its up-stem was a full-length vertical run, refused `RUN_AT_CELL_EDGE` (the barline filter), so the note had no
stem and the 2.153 beam rule narrowed it. Synthetic cells, SPACING 100 canonical px per space (as `test_line_detection_stem_finder`).

Every positive has a control that must stay refused: the barline beside the head (its end is in the head's rows but not its
columns), a head whose rows the run never reaches, no heads at all, and the flag off (the shipped reader).
"""

from __future__ import annotations

import numpy as np

from tools.omr import line_detection as LD
from tools.omr.line_detection import RUN_ACCEPTED, RUN_AT_CELL_EDGE, detect_stems
from tools.omr.types import MeasureCell

LINE_YS = [100, 200, 300, 400, 500]
OFF = LD.STEM_FINDER_STAGED_DEFAULT
ON = LD.STEM_FINDER_STAGED_DEFAULT | {"edge_head"}
W = 900                       # edge margin 80 -> a run past x 820 is "at the edge"
HEAD = (720, 410, 130, 100)   # last head of the bar, right edge 850
LEFT_HEAD = (50, 410, 130, 100)


def _cell(paint) -> MeasureCell:
    img = np.full((900, W), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0,
                       image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, W, 900),
                       staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0)


def _rect(img, x0, y0, x1, y1):
    img[y0:y1, x0:x1] = 0


def _edge_stem(img):
    _rect(img, 840, 120, 848, 470)          # up-stem at the head's right edge, ends inside the head box (410-510)


def _barline(img):
    _rect(img, 892, 100, 900, 500)          # the barline, staff top to bottom, at the very edge


def _xs(out):
    return [(d.x_canonical, d.x_canonical + d.width_canonical) for d in out]


def _at_edge(out):
    return [x for x in _xs(out) if x[1] > W - 80 or x[0] < 80]


def test_off_is_the_shipped_reader_and_refuses_the_edge_stem():
    cand = []
    out = detect_stems(_cell(_edge_stem), stem_finder=OFF, noteheads=[HEAD], candidates_out=cand)
    assert _at_edge(out) == []
    assert [c.outcome for c in cand if c.x == 840] == [RUN_AT_CELL_EDGE]


def test_on_keeps_the_stem_whose_end_stands_in_its_head():
    cand = []
    out = detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=[HEAD], candidates_out=cand)
    assert _at_edge(out) == [(840, 848)]
    assert [c.outcome for c in cand if c.x == 840] == [RUN_ACCEPTED]


def test_control_the_barline_beside_the_head_stays_refused():
    # the barline's bottom end (500) lies in the head's rows, but not in its columns: a head stands clear of a barline
    out = detect_stems(_cell(_barline), stem_finder=ON, noteheads=[HEAD])
    assert out == []


def test_control_both_stem_and_barline_only_the_stem_is_kept():
    out = detect_stems(_cell(lambda i: (_edge_stem(i), _barline(i))), stem_finder=ON, noteheads=[HEAD])
    assert _xs(out) == [(840, 848)]


def test_control_no_heads_supplied_no_rescue():
    assert _at_edge(detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=None)) == []
    assert _at_edge(detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=[])) == []


def test_control_a_head_the_run_never_reaches_is_no_rescue():
    far = (720, 700, 130, 100)              # same columns, rows 700-800; the run ends at 470 (and starts at 120)
    assert _at_edge(detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=[far])) == []


def test_control_a_head_box_cut_by_the_cell_edge_rescues_nothing():
    # Litolff: a sliver box at x=0 (a head our crop cut, or the barline boxed as a head), widened across the barline
    def paint(img):
        _rect(img, 0, 100, 8, 760)          # the barline at the cell's left edge, 6.6 spaces
    cut = (-45, 600, 120, 200)              # its lower end (760) in the box's rows and columns, but the box crosses x=0
    assert detect_stems(_cell(paint), stem_finder=ON, noteheads=[cut]) == []
    inside = (0, 600, 120, 200)             # the same box inside the cell: the rule would take it (the control can fail)
    assert _xs(detect_stems(_cell(paint), stem_finder=ON, noteheads=[inside])) == [(0, 8)]


def test_left_edge_down_stem_ending_in_its_head():
    def paint(img):
        _rect(img, 52, 450, 60, 800)        # down-stem on the head's left, its top end in the head (410-510)
    out = detect_stems(_cell(paint), stem_finder=ON, noteheads=[LEFT_HEAD])
    assert _at_edge(out) == [(52, 60)]
    assert _at_edge(detect_stems(_cell(paint), stem_finder=OFF, noteheads=[LEFT_HEAD])) == []


def test_interior_stems_are_unchanged_by_the_flag():
    def paint(img):
        _rect(img, 400, 120, 408, 470)
    head = (300, 410, 110, 100)
    assert _xs(detect_stems(_cell(paint), stem_finder=OFF, noteheads=[head])) == \
        _xs(detect_stems(_cell(paint), stem_finder=ON, noteheads=[head]))


def test_flag_default_off_and_staged_only(monkeypatch):
    monkeypatch.delenv(LD.STEM_AT_BAR_EDGE_ENV, raising=False)
    monkeypatch.delenv(LD.STEM_FINDER_ENV, raising=False)
    assert not LD.stem_at_bar_edge_enabled()
    assert "edge_head" not in LD.staged_stem_finder()
    for v in ("0", "", "off", "no", "maybe"):
        monkeypatch.setenv(LD.STEM_AT_BAR_EDGE_ENV, v)
        assert "edge_head" not in LD.staged_stem_finder()
    monkeypatch.setenv(LD.STEM_AT_BAR_EDGE_ENV, "1")
    assert LD.staged_stem_finder() == LD.STEM_FINDER_STAGED_DEFAULT | {"edge_head"}
    assert "edge_head" not in LD.stem_finder_repairs()      # LEGACY's default stays empty


# ── 2.155 tighten (Sean 2026-10-16 "Tighten"): tile 9 and tile 4 ─────────────────────────────────────────────────────────

def test_tighten_a_run_through_another_head_is_not_rescued():
    # tile 9: the run ends in its head (bottom) and passes through a second head at its top
    other = (760, 110, 130, 100)            # overlaps the run's columns (840-848) and rows (120-470)
    assert _at_edge(detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=[HEAD, other])) == []
    # control: the same head away from the run's columns -> rescued as before
    beside = (600, 110, 130, 100)
    assert _at_edge(detect_stems(_cell(_edge_stem), stem_finder=ON, noteheads=[HEAD, beside])) == [(840, 848)]


def _beamed(n_interior):
    xs = (360, 600)[:n_interior]

    def paint(img):
        for x in xs + (840,):
            _rect(img, x, 120, x + 8, 470)
        _rect(img, xs[0], 120, 848, 170)    # one beam from the first interior stem to the edge stem
        for x in xs + (840,):
            _rect(img, x - 100, 410, x + 8, 510)
    heads = [(x - 100, 410, 108, 100) for x in xs] + [(740, 410, 108, 100)]
    return _cell(paint), heads


def _beams(out):
    return [(b.x_canonical, b.width_canonical) for b in out["beams"]]


def test_tighten_a_rescued_stem_never_anchors_a_new_beam():
    # tile 4: with only one other stem, the beam stands only if the rescued stem anchors it -> no stroke
    c, heads = _beamed(1)
    out = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, stem_finder=ON)
    assert (840, 8) in [(s.x_canonical, s.width_canonical) for s in out["stems"]]     # the stem itself is still kept
    assert _beams(out) == []
    # control (can fail): the same two stems handed to the beam pass DO anchor that stroke
    assert LD.detect_beams(c, stems=out["stems"], rescue_tall=True) != []


def test_tighten_a_rescued_stem_may_join_a_beam_the_others_make():
    c, heads = _beamed(2)
    on = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, stem_finder=ON)
    off = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, stem_finder=OFF)
    assert _beams(on) == _beams(off) != []


# ── 2.155 (Sean 2026-10-16 "Yes"): a found stem may CONTINUE a beam level, never START one (2.155b tile 13 / 2.155 tile 4) ──

def _stub_beam_pass(monkeypatch, extra):
    """The beam pass returns stroke A from the other stems alone, and A + `extra` when the rescued stem is among the anchors."""
    A = LD.LineDetection(smufl_name="beam", category="structural", x_canonical=360, y_canonical=120,
                         width_canonical=488, height_canonical=50)
    real = LD.detect_beams

    def fake(cell, stems=None, rescue_tall=False):
        real(cell, stems=stems, rescue_tall=rescue_tall)
        return [A] + ([extra] if any(s.x_canonical == 840 for s in stems or ()) else [])
    monkeypatch.setattr(LD, "detect_beams", fake)
    return A


def _piece(y):
    return LD.LineDetection(smufl_name="beam", category="structural", x_canonical=700, y_canonical=y,
                            width_canonical=148, height_canonical=26)


def test_continue_a_rescued_stem_may_extend_the_level_the_others_make(monkeypatch):
    A = _stub_beam_pass(monkeypatch, _piece(174))          # 4 px under A: the same stroke, broken by the scan (tile 13)
    out = LD.detect_lines(_cell(_edge_stem), noteheads=[HEAD], stem_finder=ON)
    assert (840, 848) in _xs(out["stems"])
    # one stroke, one level: A widened over the piece (kept apart, a stem crossing both would read two levels)
    assert [LD._box(b) for b in out["beams"]] == [(360, 120, 488, 80)]


def test_continue_a_rescued_stem_never_starts_a_new_level(monkeypatch):
    A = _stub_beam_pass(monkeypatch, _piece(390))          # 2.2 spaces under A: another level (tile 4)
    out = LD.detect_lines(_cell(_edge_stem), noteheads=[HEAD], stem_finder=ON)
    assert [LD._box(b) for b in out["beams"]] == [LD._box(A)]


def test_continue_off_the_beam_pass_runs_once_as_shipped(monkeypatch):
    calls = []
    real = LD.detect_beams
    monkeypatch.setattr(LD, "detect_beams", lambda cell, stems=None, rescue_tall=False: calls.append(1) or real(
        cell, stems=stems, rescue_tall=rescue_tall))
    LD.detect_lines(_cell(_edge_stem), noteheads=[HEAD], stem_finder=OFF)
    assert calls == [1]
