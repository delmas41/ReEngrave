"""ROADMAP 2.352 round 2 -- a sharp stands just before its own note, in its own bar (STAGED GATHER, `page_accidental_ink`, 2.336 reader, ON).

THE RULE, as a musician says it: a sharp stands just before its own note, in its own bar. NEVER: a note taken from across a barline; never a sharp released that
stands before its note in its bar; never "cannot tell" turned into another answer (declined ink is simply left unclaimed).
(Sean 2026-11-25, "Always same bar": the convention decides the barline ground; the two numbers beside it -- `STACK_HEAD_GAP_MAX_SP`, `STACK_W_MIN_FRAC` -- only narrow.)

Every control is REAL page ink (CLAUDE rule 7), cut from the saved 20261123-night records and the master cell maps (page map re-cut stroke for stroke, the detector's boxes,
the earlier claims, the page map's barlines; no gather) into `data_sharp_stack_2_352.npz`. Sean's four judged marks (2026-11-25):
  * Litolff p10 [621,3466,645,3509]  "a notehead but the stem ink is broken"       -> must NOT be claimed (its note is across a barline)
  * Litolff p10 [1564,2933,1580,2986] "a quarter note rest"                         -> must NOT be claimed (its "note" is 3.5 sp away)
  * Litolff p10 [2081,421,2089,461]   "part of an f ... part of a sforzando"        -> must NOT be claimed (half a sharp's width)
  * Litolff p12 [1249,744,1265,797]   "a sharp"                                     -> must be claimed (round 1's "paper between the uprights" cut released it)
and the 11 sharps of 2.347's judged-true set (the manager's crop look): four read by `sharp_stacks`, seven by the pair / family readers.
Each region replays to the page's own claim (the members' page ordinals equal the record's).
"""
import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import page_accidental_ink as PAI

DATA = pathlib.Path(__file__).with_name("data_sharp_stack_2_352.npz")
NOTEHEAD = "litolff_p10_10_1_9_0_5_notehead_stem_broken"
REST = "litolff_p10_quarter_rest_sean"
SF = "litolff_p10_sforzando_part_sean"
SEAN_SHARP = "litolff_p12_sharp_sean"
MUST_GO = [NOTEHEAD, REST, SF]
STACK_TRUE = ["litolff_p12_12_0_2_1_7_sharp", "litolff_p13_13_1_10_13_3_sharp", "brahms_p7_7_1_5_0_15_sharp", "brahms_p14_14_0_3_1_5_sharp"]
OTHER_TRUE = ["brahms_p11_11_1_1_7_9_sharp", "brahms_p11_11_1_9_8_14_sharp", "brahms_p13_13_0_0_8_17_sharp", "brahms_p14_14_1_2_3_9_sharp",
              "brahms_p15_15_0_2_2_2_sharp", "brahms_p15_15_0_7_0_10_sharp", "brahms_p16_16_0_11_2_17_sharp"]


def region(name):
    z = np.load(DATA)
    meta = json.loads(str(z["meta"]))[name]
    strokes, masks = [], []
    for n, s in enumerate(meta["strokes"]):
        strokes.append(SimpleNamespace(kind=s["kind"], box=tuple(s["box"]), length_sp=s["length_sp"], area_sp2=s["area_sp2"], fill=s["fill"],
                                       angle_deg=s["angle_deg"], thickness_sp=s["thickness_sp"], thickness_spread_sp=s["thickness_spread_sp"],
                                       hole_share=s["hole_share"], staff_space_local=s["staff_space_local"],
                                       touches=[(int(j), float(c)) for j, c in s["touches"]], joined_to=[(int(j), w) for j, w in s["joined_to"]],
                                       parts=[], page_ordinal=s["page_ordinal"]))
        masks.append((z["%s__mask%d" % (name, n)].astype(bool), s["mask_xy"][0], s["mask_xy"][1]))
    heads = [PAI.Head(tuple(b), c, k) for b, c, k in meta["heads"]]
    return meta, strokes, masks, heads


def read(name, fused=True, barlines=True):
    meta, strokes, masks, heads = region(name)
    found, why = PAI.read_page(strokes, meta["sp"], heads, [tuple(b) for b in meta["boxed"]], [tuple(r) for r in meta["rects"]],
                               [tuple(r) for r in meta["reads"]], meta["held_ids"], [tuple(r) for r in meta["header"]],
                               {int(k): v for k, v in meta["owners"].items()}, fused=fused, masks=masks, scale=meta["scale"],
                               barlines=meta["barlines"] if barlines else ())
    return meta, strokes, masks, found, why


def covering(found, box, share=0.5):
    return [c for c in found if PAI.share_inside(box, c["box"]) >= share or PAI.share_inside(c["box"], box) >= share]


def ordinals(strokes, c):
    return sorted(strokes[m].page_ordinal for m in c["members"])


# ── Sean's judged marks: each is wrong on main, right here ───────────────────────────────────────────────────────────────

def test_the_notehead_with_a_broken_stem_is_not_a_sharp_because_its_note_is_across_a_barline():
    meta, strokes, masks, found, why = read(NOTEHEAD)
    assert not covering(found, meta["glyph_box"])
    assert why.get("fused_stack:note_across_barline") == 1       # counted in words, never silent
    assert not ({675, 678} & {o for c in found for o in ordinals(strokes, c)})     # the ink is left unclaimed, never given to another reading


def test_the_notehead_is_claimed_without_the_barline_ground_so_the_control_can_fail():
    # main's behaviour (no barlines given): the same real ink is claimed as a sharp by the note across the barline
    meta, strokes, masks, found, why = read(NOTEHEAD, barlines=False)
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["how"] == "sharp_stack" and ordinals(strokes, got[0]) == [675, 678]


def test_the_quarter_rest_is_not_a_sharp_its_note_is_not_just_after_it():
    meta, strokes, masks, found, why = read(REST)
    assert not covering(found, meta["glyph_box"])
    assert why.get("fused_stack:no_note_beside", 0) >= 1
    assert not [c for c in found if c["type"] != "sharp" and covering([c], meta["glyph_box"])]      # never turned into another answer


def test_the_quarter_rest_is_claimed_when_the_nearness_ground_is_widened():
    saved = PAI.STACK_HEAD_GAP_MAX_SP
    PAI.STACK_HEAD_GAP_MAX_SP = 9.0
    try:
        meta, strokes, masks, found, why = read(REST)
    finally:
        PAI.STACK_HEAD_GAP_MAX_SP = saved
    assert len(covering(found, meta["glyph_box"])) == 1


def test_part_of_a_sforzando_is_not_a_sharp_it_is_half_a_sharps_width():
    meta, strokes, masks, found, why = read(SF)
    assert not covering(found, meta["glyph_box"])
    assert why.get("fused_stack:too_narrow", 0) >= 1


def test_part_of_a_sforzando_is_claimed_when_the_width_ground_is_off():
    saved = PAI.STACK_W_MIN_FRAC
    PAI.STACK_W_MIN_FRAC = 0.0
    try:
        meta, strokes, masks, found, why = read(SF)
    finally:
        PAI.STACK_W_MIN_FRAC = saved
    assert len(covering(found, meta["glyph_box"])) == 1


def test_seans_sharp_on_page_12_is_still_claimed():
    # round 1's cut ("paper between the uprights") released this real sharp; round 2 must not
    meta, strokes, masks, found, why = read(SEAN_SHARP)
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["type"] == "sharp" and got[0]["how"] == "sharp_stack"


# ── the never: every judged true sharp is still claimed, same ink as the page's own claim ─────────────────────────────────

@pytest.mark.parametrize("name", STACK_TRUE + OTHER_TRUE)
def test_every_judged_true_sharp_is_still_claimed(name):
    meta, strokes, masks, found, why = read(name)
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["type"] == "sharp", (name, [(c["type"], c["box"]) for c in got])
    assert ordinals(strokes, got[0]) == meta["members_page_ordinals"]
    assert got[0].get("how") == meta["claim_how"]


@pytest.mark.parametrize("name", STACK_TRUE + OTHER_TRUE + [SEAN_SHARP])
def test_no_judged_true_sharp_has_a_barline_between_it_and_its_note(name):
    # both sides of the convention ground, measured by the barline's ink: the page map's barline columns, none between a true sharp and the head it is by
    meta, strokes, masks, found, why = read(name)
    c = covering(found, meta["glyph_box"])[0]
    y = (c["box"][1] + c["box"][3]) / 2.0
    assert not PAI.barline_between(c["box"][2], c["head"][0], y, meta["barlines"])


def test_the_barline_between_the_notehead_and_its_note_is_in_the_page_maps_barlines():
    meta, strokes, masks, found, why = read(NOTEHEAD, barlines=False)
    c = covering(found, meta["glyph_box"])[0]
    y = (c["box"][1] + c["box"][3]) / 2.0
    assert PAI.barline_between(c["box"][2], c["head"][0], y, meta["barlines"])


# ── round 3: nearness by INK, and two hollow heads are not a sharp ─────────────────────────────────────────────────────────

HEADS_MID_BAR = "litolff_p13_two_half_heads_sean"     # Sean 2026-11-25: "two half note heads, a third apart" (main: a sharp, stroke reader, margin 0.07)
HEAD_MERGED = "litolff_p12_sharp_head_merged"         # a real sharp whose head the stroke map merged into the sharp's bars (head box 1269, ink merged back to 1254)


def ink_gap(name, c, meta, strokes, masks, heads):
    members = c["members"]
    edges = PAI.ink_x_edges(masks, meta["scale"], members)
    spl = float(strokes[members[0]].staff_space_local or meta["sp"])
    left = PAI.head_ink_left(strokes, masks, meta["scale"], PAI.Head(tuple(c["head"]), c["head_conf"], c["head_key"]), members)
    return None if (edges is None or left is None) else (left - edges[1]) / spl


def test_two_hollow_heads_a_third_apart_are_not_a_sharp_mid_bar():
    # barlines withheld: main's reader without the round-2 barline ground, i.e. the same ink with its note in its own bar (the mid-bar case)
    meta, strokes, masks, found, why = read(HEADS_MID_BAR, barlines=False)
    assert not covering(found, meta["glyph_box"])
    assert why.get("hollow_heads") == 1                  # counted in words, never silent
    assert not [c for c in found if covering([c], meta["glyph_box"])]          # never turned into another answer


def test_the_two_hollow_heads_are_also_left_where_their_note_is_across_a_barline():
    # round 2's own ground, on the same real mark (its note lies across the barline there)
    meta, strokes, masks, found, why = read(HEADS_MID_BAR)
    assert not covering(found, meta["glyph_box"]) and why.get("note_across_barline") == 1


def test_the_two_hollow_heads_are_claimed_as_a_sharp_without_the_ground_so_the_control_can_fail():
    saved = PAI.HOLLOW_HEADS_CELLS_MIN
    PAI.HOLLOW_HEADS_CELLS_MIN = 99
    try:
        meta, strokes, masks, found, why = read(HEADS_MID_BAR, barlines=False)
    finally:
        PAI.HOLLOW_HEADS_CELLS_MIN = saved
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["type"] == "sharp" and got[0].get("how") is None and got[0]["why"] == "stems_level"


def test_the_hollow_heads_show_three_cells_of_paper_where_no_judged_sharp_shows_more_than_one():
    saved = PAI.HOLLOW_HEADS_CELLS_MIN
    PAI.HOLLOW_HEADS_CELLS_MIN = 99
    try:
        meta, strokes, masks, found, why = read(HEADS_MID_BAR, barlines=False)
    finally:
        PAI.HOLLOW_HEADS_CELLS_MIN = saved
    c = covering(found, meta["glyph_box"])[0]
    assert PAI.paper_cells(strokes, masks, c["members"], c["box"], meta["scale"]) >= PAI.HOLLOW_HEADS_CELLS_MIN
    for name in STACK_TRUE + OTHER_TRUE + [SEAN_SHARP]:                  # the other side, every judged sharp
        m, s, mk, f, w = read(name)
        got = covering(f, m["glyph_box"])[0]
        assert PAI.paper_cells(s, mk, got["members"], got["box"], m["scale"]) <= 1, name
        assert not w.get("hollow_heads"), name


@pytest.mark.parametrize("name,lo,hi", [("litolff_p12_sharp_sean", -0.1, 0.3), ("litolff_p12_12_0_2_1_7_sharp", -0.3, 0.2), ("brahms_p7_7_1_5_0_15_sharp", 0.1, 0.5)])
def test_the_judged_sharps_stand_this_far_from_their_note_by_ink(name, lo, hi):
    # measured by the ink edges (Sean 2026-11-18: join and separate by ink): the p12 sharp's box edge said -0.2; its ink touches its note's stem (0.06)
    meta, strokes, masks, found, why = read(name)
    c = covering(found, meta["glyph_box"])[0]
    assert lo <= ink_gap(name, c, meta, strokes, masks, None) <= hi


def test_the_quarter_rests_note_is_far_by_ink_too():
    saved = PAI.STACK_HEAD_GAP_MAX_SP
    PAI.STACK_HEAD_GAP_MAX_SP = 9.0
    try:
        meta, strokes, masks, found, why = read(REST)
    finally:
        PAI.STACK_HEAD_GAP_MAX_SP = saved
    c = covering(found, meta["glyph_box"])[0]
    assert ink_gap(REST, c, meta, strokes, masks, None) > PAI.STACK_HEAD_GAP_MAX_SP + 0.5     # room below the cut, measured on Sean's rest


def test_a_head_the_stroke_map_merged_into_its_sharp_is_still_the_note_beside_it():
    # real Litolff p12 [1253,1685,1269,1733]: a sharp the map merged with its head (one stroke from x 1254); the head's ink counts from its own box, so the note stays beside
    meta, strokes, masks, found, why = read(HEAD_MERGED)
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0].get("how") == "sharp_stack"
    assert -0.1 <= ink_gap(HEAD_MERGED, got[0], meta, strokes, masks, None) <= 0.4


def test_head_ink_left_is_clipped_to_the_heads_own_box():
    mk = np.ones((6, 40), bool)
    strokes = [SimpleNamespace(box=(100, 0, 40, 6), kind="blob")]
    head = PAI.Head((120, 0, 140, 6), 0.9, "h")
    assert PAI.head_ink_left(strokes, [(mk, 100, 0)], 1.0, head) == 120.0          # the merged piece left of the head is the sharp's
    assert PAI.head_ink_left(strokes, [(mk, 100, 0)], 1.0, PAI.Head((300, 0, 320, 6), 0.9, "h")) is None     # no ink in the box: no note beside


def test_barline_ground_unit():
    bar = [{"box": (100, 0, 106, 400), "slope": 0.0, "intercept": 103.0}]
    assert PAI.barline_between(90, 120, 200, bar)
    assert not PAI.barline_between(90, 99, 200, bar)          # the note stands before the barline: its own bar
    assert not PAI.barline_between(90, 120, 500, bar)         # another system's height
    head = PAI.Head((120, 190, 140, 210), 0.9, "h")
    assert PAI.head_beside([80, 170, 95, 215], 200, [head], 16.0, bar) is None
    assert PAI.head_beside([80, 170, 95, 215], 200, [head], 16.0, ()) is head


def test_flag_default_unchanged_and_off_switch_still_off():
    meta, strokes, masks, found, why = read(NOTEHEAD, fused=False)
    assert not [c for c in found if c.get("how") == "sharp_stack"]
