"""accidental-not-head lane (flag `OMR_ACCIDENTAL_FUSED_INK`, default OFF; `staged/page_accidental_ink.py`): a sharp, flat or natural is never written
as a note. Two thick-ink shapes the 2.285 reader could not see -- a natural whose bars are lost (two close uprights, staggered the natural's way) and a
sharp filled in to one block (a stack of blobs the stroke map cut as stacked heads) -- and the claim that takes ALL of a twice-seen accidental's ink.

Every control is the REAL page strokes and their ink masks around a mark Sean or the batch-2 print reading named (CLAUDE rule 7), cut from the
gathered pages (`data_accidental_not_head.npz`): Litolff p2 bar 21 (Sean's "three quarter notes with a half note on top": the natural at the barline
was written as an A-flat4 half), Litolff 2/1/3/14 (the natural's right upright taken as a down stem), Sean's tile 6/1/8/11 ("a sharp and a natural
sign ... in the red box"), the triage's cello and violin sharps (Litolff 6/0/8/8, 6/0/6/12), the Brahms 5/0/12/7 sharp (a box on it written as an
E-flat3). Each fails with the rule off. The never side: quarter rests (a stack whose corners read "flat"), a real head beside its accidental.
"""
import json
import os
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import page_accidental_ink as PAI

DATA = pathlib.Path(__file__).with_name("data_accidental_not_head.npz")


def region(name):
    z = np.load(DATA)
    meta = json.loads(str(z["meta"]))[name]
    strokes, masks = [], []
    for n, s in enumerate(meta["strokes"]):
        strokes.append(SimpleNamespace(kind=s["kind"], box=tuple(s["box"]), length_sp=s["length_sp"], area_sp2=s["area_sp2"], fill=s["fill"],
                                       thickness_sp=s["thickness_sp"], hole_share=s["hole_share"], staff_space_local=s["staff_space_local"],
                                       touches=[(int(j), float(c)) for j, c in s["touches"]], joined_to=[(int(j), w) for j, w in s["joined_to"]],
                                       parts=[], page_ordinal=s["page_ordinal"]))
        masks.append((z["%s__mask%d" % (name, n)], s["mask_xy"][0], s["mask_xy"][1]))
    heads = [PAI.Head(b, c, k) for b, c, k in meta["heads"]]
    return meta, strokes, masks, heads


def read(name, fused):
    meta, strokes, masks, heads = region(name)
    found, why = PAI.read_page(strokes, meta["sp"], heads, meta["boxed"], meta["rects"], meta["reads"], meta["held_ids"], meta["header"],
                               {int(k): v for k, v in meta["owners"].items()}, fused=fused, masks=masks, scale=meta["scale"])
    return meta, strokes, heads, found, why


def page_ords(strokes, members):
    return {strokes[m].page_ordinal for m in members}


def covers(found, box, share=0.5):
    """the claims holding at least `share` of a head box (the claim-final consult refuses a box mostly held by an earlier claim)"""
    return [c for c in found if PAI.share_inside(box, c["box"]) >= share]


def test_flag_default_on():
    os.environ.pop(PAI.FUSED_ENV, None)
    assert PAI.fused_enabled() is True                     # Sean 2026-11-23: "Turn it on whenever you can"
    try:
        for off in ("0", "false", "no", "off"):
            os.environ[PAI.FUSED_ENV] = off
            assert PAI.fused_enabled() is False
    finally:
        os.environ.pop(PAI.FUSED_ENV, None)


def test_bar21_natural_at_the_barline_is_a_natural_not_two_heads():
    # Litolff 2/0/7/4/5 (A-flat4 half, written at beat 0) and 2/0/7/4/12 (C5) stand on the natural fused into the barline
    a_flat_box, c5_box = (979, 1478, 996, 1494), (979, 1462, 996, 1475)
    *_, off, _ = read("litolff_p2_bar21_natural_at_barline", False)
    assert not covers(off, a_flat_box) and not covers(off, c5_box)                   # the control fails with the rule off
    meta, strokes, heads, on, why = read("litolff_p2_bar21_natural_at_barline", True)
    nat = [c for c in on if c["type"] == "natural" and c["how"] == "natural_pair"]
    assert len(nat) == 1 and nat[0]["standing"] == "GUESSED" and nat[0]["margin"] is None
    assert covers(on, a_flat_box) == nat and covers(on, c5_box) == nat
    # the note it is BY is the chord to its right (G5 half / B4), never one of the boxes on its own ink
    assert nat[0]["head"][0] >= nat[0]["box"][2] - 1


def test_natural_right_upright_is_not_a_down_stem():
    # Litolff 2/1/3/14: the natural before the B2 half; its right upright (page stroke 4038) was joined to the head as a down stem (a two-voice unison)
    *_, off, _ = read("litolff_p2_2_1_3_14_natural_before_B2", False)
    meta, strokes, heads, on, _ = read("litolff_p2_2_1_3_14_natural_before_B2", True)
    assert not any({4033, 4038} <= page_ords(strokes, c["members"]) for c in off)
    nat = [c for c in on if {4033, 4038} <= page_ords(strokes, c["members"])]
    assert len(nat) == 1 and nat[0]["type"] == "natural"


def test_seans_tile_6_1_8_11_sharp_and_natural_are_claimed():
    # Sean: "two half notes with a tremolo slash ... a sharp and a natural sign ... in the red box"; F5 box 2433,3167 sat on the sharp, the natural below
    sharp_box = (2433, 3167, 2455, 3206)
    *_, off, _ = read("litolff_p6_sean_6_1_8_11_sharp_and_natural", False)
    assert not covers(off, sharp_box)
    *_, on, _ = read("litolff_p6_sean_6_1_8_11_sharp_and_natural", True)
    kinds = sorted(c["type"] for c in on if c.get("how") in ("sharp_stack", "natural_pair", "sharp_pair"))
    assert kinds == ["natural", "sharp"]
    assert [c["type"] for c in covers(on, sharp_box)] == ["sharp"]


@pytest.mark.parametrize("name,box", [("litolff_p6_6_0_8_8_cello_sharp", (1756, 1632, 1775, 1660)),
                                      pytest.param("litolff_p6_6_0_6_12_violin_sharp", (2455, 1286, 2478, 1327), marks=pytest.mark.xfail(
                                          strict=True, reason="OPEN: a dynamicP box (0.41) on the sharp's upper half is an 'earlier read' "
                                                              "(EARLIER_READ_PREFIXES) and holds its strokes; not changed by this lane"))])
def test_triage_sharps_filled_in_are_sharps(name, box):
    # the triage's bars: the cello's sharp written as an E-flat3 quarter, the violin's F-sharp5 as an extra F5
    *_, off, _ = read(name, False)
    assert not covers(off, box)
    *_, on, _ = read(name, True)
    got = covers(on, box)
    assert [c["type"] for c in got] == ["sharp"] and got[0]["how"] == "sharp_stack" and got[0]["standing"] == "GUESSED"


def test_brahms_sharp_claim_takes_all_its_ink():
    # Brahms 5/0/12/7: the sharp WAS claimed, but its bar ends right of its right upright (page strokes 6372, 6373) stayed free, the head box on the
    # sharp owned them and was not refused -- an E-flat3 written on the sharp
    meta, strokes, heads, off, _ = read("brahms_p5_5_0_12_7_sharp_twin", False)
    sh = [c for c in off if c["type"] == "sharp"]
    assert len(sh) == 1 and not ({6372, 6373} & page_ords(strokes, sh[0]["members"]))
    meta, strokes, heads, on, _ = read("brahms_p5_5_0_12_7_sharp_twin", True)
    sh = [c for c in on if c["type"] == "sharp"]
    assert len(sh) == 1 and {6339, 6356, 6372, 6373} <= page_ords(strokes, sh[0]["members"])


def test_never_a_real_head_and_never_a_rest():
    # the never side, on every region: no fused claim takes a real head's blob (a confident head box's, or a solid head), and the quarter rests
    # (stacks whose corners read "flat") are never claimed
    for name in ("litolff_p2_bar21_natural_at_barline", "litolff_p2_2_1_3_14_natural_before_B2", "litolff_p6_sean_6_1_8_11_sharp_and_natural",
                 "litolff_p6_6_0_8_8_cello_sharp", "litolff_p6_6_0_6_12_violin_sharp", "litolff_p6_quarter_rests", "brahms_p5_5_0_12_7_sharp_twin",
                 "litolff_p6_6_1_3_9_stacked_chord_beside_natural", "brahms_p5_5_0_13_7_bass_sharp_bars_broken"):
        meta, strokes, heads, on, why = read(name, True)
        for c in on:
            if c.get("how") not in ("natural_pair", "sharp_pair", "sharp_stack"):
                continue
            h = c["head"]
            assert PAI.share_inside(h, c["box"]) < 0.5, (name, c["box"], h)      # the note it is by stands beside it, not on it
    meta, strokes, heads, on, why = read("litolff_p6_quarter_rests", True)
    assert not [c for c in on if c.get("how") == "sharp_stack"]


def test_a_stack_whose_corners_are_not_a_sharps_is_counted_not_claimed():
    # the same quarter-rest region with every rest's head box moved beside it: the stacks still read "flat"/"unclear" by their corners -> counted
    meta, strokes, masks, heads = region("litolff_p6_quarter_rests")
    stacks = []
    seen = set()
    for i, s in enumerate(strokes):
        if s.joined_to and i not in seen:
            grp, todo = set(), [i]
            while todo:
                j = todo.pop()
                if j not in grp:
                    grp.add(j)
                    todo.extend(k for k, _w in strokes[j].joined_to)
            seen |= grp
            c = PAI.stack_corners(masks, sorted(grp), meta["scale"])
            if c and c["shape"] in ("flat", "unclear", "natural"):
                stacks.append(sorted(grp))
    assert stacks, "the control must contain a stack the corners do not call a sharp"
    for mem in stacks:
        ub = PAI._union_box([PAI._box(strokes[m]) for m in mem])
        fake = PAI.Head((ub[2] + 2, (ub[1] + ub[3]) / 2 - 10, ub[2] + 26, (ub[1] + ub[3]) / 2 + 10), 0.8, "beside")
        n = []
        out = PAI.sharp_stacks(strokes, meta["sp"], [fake], [], set(), [], masks, meta["scale"], n.append)
        assert not [c for c in out if set(c["members"]) == set(mem)]


def test_brahms_bass_sharp_with_broken_bars_is_a_sharp():
    # Brahms 5/0/13/7 (the triage's bass bar 35): the sharp's two level uprights (page strokes 6340, 6357) stand 0.5 sp apart and no bar stroke joins
    # them; the box on the sharp was written as an E-flat3 quarter and the real F-sharp3 lost its sharp
    false_head = (4933, 3612, 4968, 3635)
    *_, off, _ = read("brahms_p5_5_0_13_7_bass_sharp_bars_broken", False)
    assert not covers(off, false_head)
    meta, strokes, heads, on, _ = read("brahms_p5_5_0_13_7_bass_sharp_bars_broken", True)
    got = covers(on, false_head)
    assert [c["type"] for c in got] == ["sharp"] and got[0]["how"] == "sharp_pair" and {6340, 6357} <= page_ords(strokes, got[0]["members"])


def test_never_two_stacked_heads_beside_their_natural():
    # Litolff 6/1/3/9 (m71): a B-flat3 + E-flat4 chord fused into one block beside its natural. Its corners read like a sharp's; its ends are a
    # notehead's round ends, no upright sticks out (the first check of this lane lost these two real notes)
    chord = [(2196, 2416, 2219, 2434), (2195, 2395, 2218, 2416)]
    meta, strokes, masks, heads = region("litolff_p6_6_1_3_9_stacked_chord_beside_natural")
    *_, on, why = read("litolff_p6_6_1_3_9_stacked_chord_beside_natural", True)
    for box in chord:
        assert not [c for c in covers(on, box) if c.get("how") == "sharp_stack"]
    assert why.get("fused_stack:rounded_ends", 0) >= 1          # the never fired here: without it the stack is claimed (the control can fail)
    saved = PAI.STACK_END_MAX_SP
    try:
        PAI.STACK_END_MAX_SP = 9.0
        *_, on2, _ = read("litolff_p6_6_1_3_9_stacked_chord_beside_natural", True)
        assert any(c.get("how") == "sharp_stack" for box in chord for c in covers(on2, box))
    finally:
        PAI.STACK_END_MAX_SP = saved


def test_head_box_on_a_natural_fused_into_the_barline_is_refused_by_the_claims_together():
    # ADJUDICATE half, the page ledger's own numbers on Litolff bar 21 (2/0/7/4/5, the A-flat4 half): the barline holds 0.381 of the box's ink, the
    # natural's claim the rest; neither alone reaches the cut, so the one-claim rule left the box a notehead
    from tools.omr.staged.adjudicators import notehead_precision as NP
    box = SimpleNamespace(id="obs:box", value=["noteheadBlackOnLine", 0, 0, 10, 10])
    entry = {"by": "barline", "share": 0.381, "owns": False, "held_all": 0.95, "shares": {"barline": 0.381, PAI.OWNER: 0.569}}
    ic = SimpleNamespace(entry=entry, verdict_id="vrd:so")
    os.environ[PAI.FUSED_ENV] = "0"
    assert NP._on_an_accidentals_ink(ic, box) is None                               # rule off: the box stays (the control fails)
    os.environ[PAI.FUSED_ENV] = "1"
    try:
        r = NP._on_an_accidentals_ink(ic, box)
        assert r is not None and r.value is True and r.reason == "claimed_by:page_claim"
        # the nevers: a box that owns head ink of its own (a real head touching its accidental), and two claims with no accidental among them
        assert NP._on_an_accidentals_ink(SimpleNamespace(entry={**entry, "owns": True}, verdict_id=""), box) is None
        assert NP._on_an_accidentals_ink(SimpleNamespace(entry={**entry, "shares": {"barline": 0.381, "arc_trace": 0.569}}, verdict_id=""), box) is None
        assert NP._on_an_accidentals_ink(SimpleNamespace(entry={**entry, "held_all": 0.45}, verdict_id=""), box) is None
    finally:
        os.environ.pop(PAI.FUSED_ENV, None)


def test_never_a_notes_own_stem_as_a_naturals_upright():
    # Litolff 6/1/8/10 (m72): the A4 eighth's down stem (page stroke 3212, 1.84 sp) beside a 2.8-sp upright with a bowl (a flat); paired, they read
    # as a natural and the stems check lost the eighth. An accidental's uprights are nearly its full height, so a short one never pairs
    head = (2279, 3215, 2303, 3234)
    meta, strokes, heads, on, _ = read("litolff_p6_6_1_8_10_eighth_stem_beside_flat", True)
    assert not [c for c in on if 3212 in page_ords(strokes, c["members"])]
    assert not covers(on, head)
    saved = PAI.PAIR_STEM_MIN_SP
    try:
        PAI.PAIR_STEM_MIN_SP = 1.0                                 # the control can fail: without the never the stem is taken
        *_, on2, _ = read("litolff_p6_6_1_8_10_eighth_stem_beside_flat", True)
        assert [c for c in on2 if 3212 in page_ords(strokes, c["members"])]
    finally:
        PAI.PAIR_STEM_MIN_SP = saved
