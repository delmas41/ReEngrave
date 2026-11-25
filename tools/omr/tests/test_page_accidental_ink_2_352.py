"""ROADMAP 2.352 -- a stack of noteheads with a broken stem is not a sharp (STAGED GATHER, `page_accidental_ink.sharp_stacks`, 2.336 reader, ON).

THE RULE, as a musician says it: a sharp is two thin uprights crossed by two slanted bars, so where its uprights stick out past the bars,
paper shows between them; a solid block with one stub on it is noteheads on a broken stem, not a sharp. NEVER: release a real sharp.
(The number stands beside the rule, never in it: `STACK_TIP_GAP_MIN_SP`.)

Every control is the REAL page ink (CLAUDE rule 7), cut from the saved 20261123-night records and the master cell maps (the page map re-cut stroke for
stroke, the detector's boxes and the earlier claims of the page, no gather) into `data_sharp_stack_2_352.npz`:

  * the FALSE side: Litolff page 10, detector box glyph/10/1/9/0/5 -- Sean, 2026-11-25, shown the box: "That is a notehead but the stem ink is broken".
    The reader claimed page strokes 675 + 678 as one sharp; the head box on it was then refused (2.347).
  * the TRUE side: the 11 sharps of 2.347's judged-true set (the manager's crop look, not Sean's words: 11 of the 12 leaves were "plainly a box on a sharp").
    Four are read by `sharp_stacks` (Litolff 12/0/2/1/7, 13/1/10/13/3, Brahms 7/1/5/0/15, 14/0/3/1/5); seven by the pair reader / the family reader, which
    this change does not touch -- they are here so that the whole `read_page` replay is the control, not a single function.

Each region replays to the page's own claim (the fixture checks itself: the members' page ordinals equal the record's).
"""
import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import page_accidental_ink as PAI

DATA = pathlib.Path(__file__).with_name("data_sharp_stack_2_352.npz")
FALSE_NAME = "litolff_p10_10_1_9_0_5_notehead_stem_broken"
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


def read(name, fused=True):
    meta, strokes, masks, heads = region(name)
    found, why = PAI.read_page(strokes, meta["sp"], heads, [tuple(b) for b in meta["boxed"]], [tuple(r) for r in meta["rects"]],
                               [tuple(r) for r in meta["reads"]], meta["held_ids"], [tuple(r) for r in meta["header"]],
                               {int(k): v for k, v in meta["owners"].items()}, fused=fused, masks=masks, scale=meta["scale"])
    return meta, strokes, masks, found, why


def covering(found, box, share=0.5):
    return [c for c in found if PAI.share_inside(box, c["box"]) >= share or PAI.share_inside(c["box"], box) >= share]


def ordinals(strokes, c):
    return sorted(strokes[m].page_ordinal for m in c["members"])


# ── the control: the real page-10 mark ────────────────────────────────────────────────────────────────────────────────

def test_the_real_page_10_mark_is_not_claimed_as_a_sharp():
    # FAILS on main: sharp_stacks claimed page strokes 675 + 678 (area [621, 3466, 645, 3509]) as one sharp, and the head box on it (glyph/10/1/9/0/5,
    # which Sean calls a notehead) was refused downstream
    meta, strokes, masks, found, why = read(FALSE_NAME)
    assert not covering(found, meta["glyph_box"]), [(c["how"], c["box"]) for c in covering(found, meta["glyph_box"])]
    taken = {o for c in found for o in ordinals(strokes, c)}
    assert not ({675, 678} & taken)                         # the ink is left unclaimed, never given to another reading
    assert why.get("fused_stack:no_paper_between_uprights") == 1      # counted, never silent (CLAUDE: a refusal says why)


def test_the_page_10_claim_exists_without_the_rule_so_the_control_can_fail():
    # the fixture really holds the ink that main claimed: with the cut taken off, the same region claims it again
    saved = PAI.STACK_TIP_GAP_MIN_SP
    PAI.STACK_TIP_GAP_MIN_SP = 0.0
    try:
        meta, strokes, masks, found, why = read(FALSE_NAME)
    finally:
        PAI.STACK_TIP_GAP_MIN_SP = saved
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["how"] == "sharp_stack" and ordinals(strokes, got[0]) == [675, 678]


# ── the never: every judged true sharp is still claimed ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", STACK_TRUE + OTHER_TRUE)
def test_every_judged_true_sharp_is_still_claimed(name):
    meta, strokes, masks, found, why = read(name)
    got = covering(found, meta["glyph_box"])
    assert len(got) == 1 and got[0]["type"] == "sharp", (name, [(c["type"], c["box"]) for c in got])
    assert ordinals(strokes, got[0]) == meta["members_page_ordinals"]          # the very ink the page claim took (the fixture checks itself)
    assert got[0].get("how") == meta["claim_how"]


def test_the_page_claim_of_the_true_stacks_never_loses_a_member():
    for name in STACK_TRUE:
        meta, strokes, masks, found, why = read(name)
        assert why.get("fused_stack:no_paper_between_uprights", 0) == 0


# ── both sides of the number (measured on the reader's own mask) ──────────────────────────────────────────────────────

def test_both_sides_of_the_paper_between_the_uprights():
    fals = _gap(FALSE_NAME)
    trues = [_gap(n) for n in STACK_TRUE]
    # printed in the ROADMAP row: the false mark 0.06 sp (one pixel of paper), the four judged true stacks 0.31-0.32 sp (five pixels)
    assert fals < PAI.STACK_TIP_GAP_MIN_SP < min(trues)
    assert min(trues) - PAI.STACK_TIP_GAP_MIN_SP > 0.1 and PAI.STACK_TIP_GAP_MIN_SP - fals > 0.08


def _gap(name):
    meta, strokes, masks, heads = region(name)
    mem = [i for i, s in enumerate(strokes) if s.page_ordinal in meta["members_page_ordinals"]]
    spl = float(strokes[mem[0]].staff_space_local or meta["sp"])
    return PAI.stack_tip_gap(masks, mem, meta["scale"], spl)


def test_a_solid_block_has_no_paper_and_two_thin_uprights_have_some():
    # synthetic, only to say what the measure means (the real controls are above): one block, one stub -> 0; two stubs apart -> their gap
    block = np.zeros((20, 12), bool)
    block[3:, :] = True
    block[0:3, 8:10] = True
    assert PAI.stack_tip_gap([(block, 0, 0)], [0], 1.0, 10.0) == 0.0
    two = block.copy()
    two[0:3, 1:3] = True
    assert PAI.stack_tip_gap([(two, 0, 0)], [0], 1.0, 10.0) == pytest.approx(0.5)


def test_flag_default_unchanged_and_off_switch_still_off():
    # the change is inside the 2.336 reader (`OMR_ACCIDENTAL_FUSED_INK`, default ON); with the reader off nothing is read at all
    meta, strokes, masks, found, why = read(FALSE_NAME, fused=False)
    assert not [c for c in found if c.get("how") == "sharp_stack"]
