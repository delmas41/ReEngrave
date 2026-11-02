"""ROADMAP 2.250 (`OMR_BIND_END_PITCH`, default OFF): the page-wide arc binder reads the END NOTE's pitch the way the older two-note rule does,
instead of re-deriving it. Every guard has a twin that fails without it (litolff_03 / litolff_06 of the 2.75 review, the overnight
20261031-night right->wrong ties).

  * (a) a head the detector drew in pieces is read at its EXTENT step, never the box centre (`_step_with_extent`);
  * (b) a chord end binds the member at the arc END's height; two members about equally near abstain `chord_end_equidistant`;
  * (c) a stem-tip candidate may name the column, never the member.
"""
import os

import pytest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from .test_arc_bind_2223 import _curve, _h, SP
from .test_staged_arc_kind_head_extent_2026_10_09 import _arc, _box, _cells, _decide


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(AC.ENV_END_PITCH, "1")
    monkeypatch.delenv(AC.ENV_BIND, raising=False)


@pytest.fixture
def off(monkeypatch):
    monkeypatch.delenv(AC.ENV_END_PITCH, raising=False)
    monkeypatch.delenv(AC.ENV_BIND, raising=False)


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(AC.ENV_END_PITCH, raising=False)
    assert not AC.end_pitch_enabled()
    monkeypatch.setenv(AC.ENV_END_PITCH, "1")
    assert AC.end_pitch_enabled()
    monkeypatch.setenv(AC.ENV_END_PITCH, "0")
    assert not AC.end_pitch_enabled()


# ── (b) / (c) the pure end binder ────────────────────────────────────────────────────────────────────────────────────────────────────────

def _dyad_pair():
    # two dyads, steps 5 / 7 (10 px apart); the LOWER tie curves below, its ends at y 142
    return [_h("lo_top", -5, 125), _h("lo_bot", -5, 135), _h("hi_top", 105, 125), _h("hi_bot", 105, 135)]


def test_each_tie_of_a_dyad_binds_its_own_note_by_height():
    heads = _dyad_pair()
    lower = AC.bind_curve(_curve(0, 142, 100, 142, +15), heads, SP, by_height=True)
    assert (lower["left"]["head"], lower["right"]["head"]) == ("lo_bot", "hi_bot")
    upper = AC.bind_curve(_curve(0, 118, 100, 118, -15), heads, SP, by_height=True)
    assert (upper["left"]["head"], upper["right"]["head"]) == ("lo_top", "hi_top")


def test_a_stem_tip_names_the_column_never_the_member():
    # the lower tie's left end at y 140; the dyad's stem-tip candidate stands for the TOP head but sits below the dyad (a tip at 150)
    tip = {"key": "lo_top", "cx": -2, "cy": 150.0, "w": 12.0, "h": 10.0, "tip": True}
    heads = _dyad_pair() + [tip]
    cu = _curve(0, 140, 100, 140, +15)
    off = AC.bind_curve(cu, heads, SP)["left"]
    assert off["head"] == "lo_top" and off.get("via_stem_tip")          # the twin: the OFF binder takes the tip's head (the litolff_03 fault)
    on = AC.bind_curve(cu, heads, SP, by_height=True)["left"]
    assert on["head"] == "lo_bot"                                       # ON: the member standing at the arc end's height


def test_a_lone_stem_tip_column_still_binds_its_head():
    # the arc is drawn to a stem (2.223 m2): the tip alone names the column; with one member the member is the tip's head
    heads = [_h("a", -5, 108), _h("b", 106, 145)]
    tips = AC.stem_tips(heads, [(110, 102, 112, 145)])
    r = AC.bind_curve(_curve(0, 100, 100, 100), heads + tips, SP, by_height=True)["right"]
    assert r["head"] == "b" and r.get("via_stem_tip")


def test_a_chord_end_midway_between_two_members_abstains_with_both_and_the_margin():
    heads = [_h("lo_top", -5, 120), _h("lo_bot", -5, 140), _h("hi", 105, 130)]
    left = AC.bind_curve(_curve(0, 130, 100, 130, 0), heads, SP, by_height=True)["left"]
    assert left.get("unbound") == "chord_end_equidistant"
    assert sorted(left["candidates"]) == ["lo_bot", "lo_top"] and left["margin_spaces"] < 0
    # the twin: the same chord, an end beside one member, binds it
    near = AC.bind_curve(_curve(0, 122, 100, 130, 0), heads, SP, by_height=True)["left"]
    assert near["head"] == "lo_top"


def test_a_real_slur_at_a_chord_keeps_its_outer_note():
    # the kind of a slur ending at a chord does not change: an end above / below the chord is nearest the outer member
    heads = [_h("lo_top", -5, 108), _h("lo_bot", -5, 125), _h("hi_top", 105, 108), _h("hi_bot", 105, 125)]
    for by_height in (False, True):
        above = AC.bind_curve(_curve(0, 100, 100, 100, -15), heads, SP, by_height=by_height)
        assert (above["left"]["head"], above["right"]["head"]) == ("lo_top", "hi_top")
        below = AC.bind_curve(_curve(0, 135, 100, 135, +15), heads, SP, by_height=by_height)
        assert (below["left"]["head"], below["right"]["head"]) == ("lo_bot", "hi_bot")


def test_off_path_untouched_by_the_argument_default():
    heads = [_h("lo_top", -5, 108), _h("lo_bot", -5, 125), _h("hi", 105, 108)]
    flat = AC.bind_curve(_curve(0, 115, 100, 115, 0), heads, SP)
    assert flat["left"].get("unbound") == "chord_end_side_unread"       # OFF: unchanged (the side is the only rule)


# ── (a) the extent step, on a record ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _litolff_06_scene(stop_y0, stop_y1, cls="tie"):
    """test_staged_arc_kind_head_extent's litolff_06 (one half note drawn in three boxes, a tie to the same note across the barline), with the
    page-wide curve (`Q.SYSTEM_ARC`) the binder reads."""
    log = Log()
    _cells(log, 2)
    kept = _box(log, 0, 0, 40.0, 127.3, 138.8)
    up = _box(log, 0, 1, 40.0, 123.5, 132.7)
    low = _box(log, 0, 2, 40.0, 130.3, 138.6)
    _box(log, 0, 3, 120.0, stop_y0, stop_y1)
    arc = _arc(log, 0, 5, 55.0, 115.0, 142.0, 148.0, cls=cls)
    log.observe(arc, Q.SYSTEM_ARC, "two_heads_one_position_adjacent", reader=READERS.CV_SYSTEM_ARC, frame="page", score=None,
                pieces=[arc.to_key()], space_page_px=10.0, x_left_page=55.0, y_left_page=142.0, x_right_page=115.0, y_right_page=142.0,
                trace=[])
    return log, arc, (up, low)


def _binding(v):
    return v.detail["grammar"].get("page_binding") or v.detail.get("page_binding")


def test_off_reads_the_box_centre_and_calls_the_litolff_06_tie_a_slur(off):
    log, arc, dups = _litolff_06_scene(122.1, 136.7)           # stop head: step 5.9 -> 6
    v = _decide(log, arc, dups)
    pb = _binding(v)
    assert pb is not None and pb["start_step"] == 7 and pb["stop_step"] == 6      # the fault: the kept box's centre reads 7
    assert v.value == "slur"


def test_on_reads_the_extent_step_and_litolff_06_is_a_tie(on):
    log, arc, dups = _litolff_06_scene(122.1, 136.7)
    v = _decide(log, arc, dups)
    pb = _binding(v)
    assert pb is not None and (pb["start_step"], pb["stop_step"]) == (6, 6)
    assert pb["start_step_source"] == "geometry_extent" and pb["start_extent"]["members"] == 3
    assert v.value == "tie" and v.reason == "tie"


def test_on_a_stop_head_two_steps_lower_is_still_a_slur(on):
    log, arc, dups = _litolff_06_scene(132.7, 147.3)           # stop head: step 8
    v = _decide(log, arc, dups)
    assert v.value == "slur"
    assert _binding(v)["relation"] == "different"


def test_on_without_refused_pieces_the_kept_box_stands(on):
    log, arc, _dups = _litolff_06_scene(122.1, 136.7)
    v = _decide(log, arc, ())                                  # nothing refused: three heads, no extent
    assert "start_extent" not in _binding(v)


# ── a fused (tall) box: two heads in one box, its centre is neither head's ───────────────────────────────────────────────────────────────

def test_a_tall_member_stands_at_its_nearer_head_sized_end_and_is_flagged():
    # litolff_03's left end: a dyad fused into ONE tall box (h 30 = three head heights, mean head 10) and a piece above it
    tall = dict(_h("fused", -5, 125, h=30.0), tall=True, hh=10.0)
    piece = dict(_h("piece", -5, 118), tall=False, hh=10.0)
    right = _h("r", 105, 135)
    cu = _curve(0, 148, 100, 148, +15)
    off = AC.bind_curve(cu, [tall, piece, right], SP, by_height=True)["left"]
    assert off["head"] == "fused" and off["tall"] is True               # the lower head-sized end (135) is 1.3 sp from the end, the piece 3.0
    centre_only = AC.bind_curve(cu, [dict(tall, tall=False), piece, right], SP, by_height=True)["left"]
    assert centre_only["head"] == "fused" and "tall" not in centre_only          # the twin: without the mark the box is read by its centre


def _tall_scene(end_y, mate=True):
    log = Log()
    _cells(log, 2)
    _box(log, 0, 0, 40.0, 117.0, 147.0)              # a fused box, 3 head heights tall, centre 132 (step 6.4)
    if mate:
        _box(log, 0, 4, 40.0, 117.0, 127.0)          # a second box in its column: the corroboration that it is a fused chord
    _box(log, 0, 3, 120.0, 122.1, 136.7)             # the stop head, centre 129.4 (step 5.9 -> 6)
    for i in range(4):                               # the staff's ordinary heads: the mean head height is a head's, not the fused box's
        _box(log, 1, i, 250.0 + 20 * i, 120.0, 130.0)
    arc = _arc(log, 0, 5, 55.0, 115.0, 150.0, 156.0, cls="tie")
    log.observe(arc, Q.SYSTEM_ARC, "two_heads_one_position_adjacent", reader=READERS.CV_SYSTEM_ARC, frame="page", score=None,
                pieces=[arc.to_key()], space_page_px=10.0, x_left_page=55.0, y_left_page=end_y, x_right_page=115.0, y_right_page=130.0,
                trace=[])
    return _decide(log, arc, ())


def test_a_tall_end_beyond_the_box_is_read_at_the_head_sized_end_not_the_centre(on):
    # the arc stands below the fused box (end 150): the head it joins is the box's LOWER head, centred 140 -> step 8, not the box centre's 6
    pb = _binding(_tall_scene(150.0))
    assert pb["left"]["tall"] is True and pb["start_step_source"] == "geometry_tall_end" and pb["start_step"] == 8
    assert pb["stop_step"] == 6 and pb["relation"] == "different" and pb["kind"] == "slur"


def test_a_lone_tall_box_is_not_known_to_be_two_heads_and_keeps_its_centre_step(on):
    # Sean's round-1 ties (litolff p9-10): a tall box alone in its column (a head with ledger / stem ink) is read as it always was
    pb = _binding(_tall_scene(150.0, mate=False))
    assert "tall" not in pb["left"] and pb["start_step_source"] == "geometry" and pb["start_step"] == 6


def test_a_tall_end_inside_the_box_is_read_as_before_by_its_centre(on):
    # the twin: an end beside the middle of the same box is no fused-dyad end; the box centre (step 6) reads as it always did
    pb = _binding(_tall_scene(132.0))
    assert "tall" not in pb["left"] and pb["start_step_source"] == "geometry" and pb["start_step"] == 6


def test_two_boxes_of_one_head_are_not_a_chord_to_choose_from():
    # members of one chord column are >= a third (1 sp) apart; two boxes 0.3 sp apart are one head drawn twice (2.232's near-tie keep):
    # the end binds as before (the side rule), it does not abstain
    heads = [_h("a", -5, 120), _h("b", -5, 123), _h("r", 105, 120)]
    cu = _curve(0, 100, 100, 100, -15)                      # a cap: the outer note of the column is the top one
    on = AC.bind_curve(cu, heads, SP, by_height=True)["left"]
    assert on["head"] == "a" and not on.get("by_height")
    assert AC.bind_curve(cu, heads, SP)["left"]["head"] == "a"
    # the twin: the same two boxes a third apart ARE a chord, and an end midway between them abstains
    far = [_h("a", -5, 120), _h("b", -5, 140), _h("r", 105, 130)]
    assert AC.bind_curve(_curve(0, 130, 100, 130, 0), far, SP, by_height=True)["left"].get("unbound") == "chord_end_equidistant"
