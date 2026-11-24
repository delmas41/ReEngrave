"""ROADMAP 2.306 r21 -- the two bars r20's full frozen sample found written WRONG AND PLAIN with the page stem reader on. Controls built from the
REAL record rows of those bars (fixture cut from the r20 Brahms ON gather, `fixtures/page_stems_2_306_r21.json`); each fails on r20's code.

1. Brahms 25/1/7/1 (STAGED GATHER, `page_stems.barline_boxes`): a 7x17 px "head" box on the barline -- no head ink of its own, refused at
   ADJUDICATE `claimed_by:barline` -- was given the next bar's natural's upright (page stroke 2093) as an up stem; the bar became two voices
   and the printed G5 -> G5 tie was dropped. A box on a barline with no head of its own takes no stem.
2. Brahms 8/0/1/8 (STAGED ADJUDICATE, `rhythm.arc_through_hook_window`, flag `OMR_HOOK_NOT_ON_AN_ARC`): a slur starting at the Cb5's down stem,
   near its tip, was counted as a hook and the Cb5 written a dotted eighth. The slur's first stretch is never a flag; a slur coming in from
   the stem's other side takes nothing from a real flag (Brahms 25/1/8/3, a printed eighth).
"""
import json
import pathlib

import pytest

from tools.omr.staged import page_stems as PS
from tools.omr.staged.adjudicators import rhythm as RH

FX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "page_stems_2_306_r21.json").read_text())


def _row(subject, quantity):
    return next(r for r in FX["barline"]["rows"] if r["subject"] == subject and r["quantity"] == quantity)


def _barline():
    b = FX["barline"]["page_strokes"]["6715"]
    return dict(box=tuple(b["bbox_page_px"]), slope=b["slope"], intercept=b["intercept"], width_px=b["width_px"])


def _head(hid, subject):
    box = tuple(_row(subject, "glyph_box")["detail"]["bbox_page_px"])
    ink = _row(subject, "mark_group")["detail"]["head_how"] == "alone"
    return dict(id=hid, members=[subject], box=box, sp=28.0, sp_own=False, ink=ink, strokes=[])


def _vertical(o):
    s = FX["barline"]["page_strokes"][str(o)]
    return dict(ord=o, box=tuple(s["bbox_page_px"]), sp=s["staff_space_local_px"])


BAR_BOX, G_SHARP = "glyph/25/1/7/1/10", "glyph/25/1/7/1/0"


def test_the_fixture_is_the_fault_r20_read():
    """The rows say what r20 wrote: the barline box was refused as a note yet carries a page stem (stroke 2093, up)."""
    assert FX["barline"]["refusal"]["reason"] == "claimed_by:barline" and FX["barline"]["refusal"]["value"] is True
    assert _row(BAR_BOX, "mark_group")["detail"]["head_how"] == "no_head_ink"
    assert _row(BAR_BOX, "page_stem")["detail"]["page_stroke"] == 2093


def test_r20s_reading_stems_the_barline_box():
    """The control can fail: the reader as r20 called it (every head) gives the barline box stroke 2093 -- the fault, reproduced from the rows."""
    heads = [_head(1, BAR_BOX), _head(2, G_SHARP)]
    res = PS.read(heads, [_vertical(2093), _vertical(1822)])
    assert res["heads"][1]["stroke"] == 2093 and res["heads"][2]["stroke"] == 1822


def test_a_box_on_a_barline_with_no_head_ink_takes_no_stem():
    heads = [_head(1, BAR_BOX), _head(2, G_SHARP)]
    assert PS.stands_on_a_barline(heads[0]["box"], [_barline()])
    assert PS.barline_boxes(heads, [_barline()]) == {1}
    res = PS.read([h for h in heads if h["id"] not in {1}], [_vertical(2093), _vertical(1822)])
    assert 1 not in res["heads"] and res["heads"][2]["stroke"] == 1822       # the real G#5 beside it keeps its own stem


def test_never_a_head_with_its_own_ink_and_never_a_box_off_the_barline():
    """Both sides of the boundary: the same box WITH head ink of its own is read as before; the real G#5 does not stand on the barline."""
    inked = dict(_head(1, BAR_BOX), ink=True)
    assert PS.barline_boxes([inked], [_barline()]) == set()
    assert not PS.stands_on_a_barline(_head(2, G_SHARP)["box"], [_barline()])
    moved = dict(_head(1, BAR_BOX), box=(1922.0, 6138.75, 1930.0, 6155.955))      # one box-width to the right: off the rule's ink
    assert PS.barline_boxes([moved], [_barline()]) == set()


# ── 2. the hook that is a slur's start ──

def _window_page(tip, glyph):
    g = FX["hook"]["glyph_boxes"][glyph]
    cx, cy, cw, _ch = (float(v) for v in g["value"][1:5])
    px0, py0, px1, _py1 = g["bbox_page_px"]
    up = cw / (px1 - px0)
    ox, oy = px0 - cx / up, py0 - cy / up
    w = FX["hook"][tip]["detail"]["window_canonical"]
    return (ox + w[0] / up, oy + w[1] / up, ox + w[2] / up, oy + w[3] / up)


def _arcs(key):
    return [(a["id"], a["detail"]) for a in FX["hook"][key]]


def test_the_cb5_tip_row_is_the_hook_r20_counted():
    d = FX["hook"]["cb5_tip"]["detail"]
    assert FX["hook"]["cb5_tip"]["value"] is True and d["end"] == "bottom" and d["hooks"] == 1


def test_a_slur_starting_at_the_stem_is_not_a_flag():
    hit = RH.arc_through_hook_window(_window_page("cb5_tip", "glyph/8/0/1/8/4"), _arcs("arcs_p8"))
    assert hit is not None and str(hit["ordinal"]) == "124" and hit["runs_on_sp"] >= RH.ARC_RUNS_ON_SP


def test_never_a_slur_that_comes_in_from_the_other_side():
    """Brahms 25/1/8/3: a printed eighth; a slur from the left ends at its stem and the arc reader ran on down the flag. The flag stands."""
    d = FX["hook"]["eighth_tip"]
    assert d["value"] is True and d["detail"]["hooks"] == 1
    assert RH.arc_through_hook_window(_window_page("eighth_tip", "glyph/25/1/8/3/3"), _arcs("arcs_p25")) is None


def test_never_an_arc_that_stops_beside_the_stem():
    """An arc whose ink starts in the window but does not run on past it reaches no further than a flag does: the hook stands."""
    a_id, a = _arcs("arcs_p8")[[str(x[1]["ordinal"]) for x in _arcs("arcs_p8")].index("124")]
    short = dict(a, points=[p for p in a["points"] if p[0] <= 4055.0])
    assert RH.arc_through_hook_window(_window_page("cb5_tip", "glyph/8/0/1/8/4"), [(a_id, short)]) is None


def test_the_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv(RH.HOOK_NOT_ON_AN_ARC_ENV, raising=False)
    assert not RH.hook_not_on_an_arc_enabled()
    monkeypatch.setenv(RH.HOOK_NOT_ON_AN_ARC_ENV, "1")
    assert RH.hook_not_on_an_arc_enabled()
