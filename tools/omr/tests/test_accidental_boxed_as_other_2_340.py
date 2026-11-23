"""ROADMAP 2.340 (flag `OMR_ACCIDENTAL_BOXED_AS_OTHER`, default OFF; STAGED GATHER, `page_claim_names.rest_standing` / `rest_box_verdict`): an accidental the
detector boxed as a rest is still an accidental. THE RULE: a sharp or natural stands just left of the note it alters, at that note's height; whatever the
detector called it, that ink is the note's accidental and never a rest -- the rest box files no claim and the existing 2.285 / 2.336 accidental reader, which
runs next, reads and claims it. THE NEVER: a rest that stands alone, a rest whose ink the reader does not call a sharp or natural, a flat.

Every control is a REAL Litolff page region (`data_accidental_boxed_as_other.npz`, cut from a gather of pages 2, 8, 9 at the moment before the rest claims:
the page strokes and their masks, the detector's boxes, the earlier claims): the sharps the overnight 20261122 wrote as 16th rests (Litolff 2/0/1/3, 2/0/2/3,
8/0/8/16, 9/1/2/6), Sean's judged rest tiles on these pages (2.288 rounds 1-3: quarter, eighth and whole rests), a real 16th rest, and a quarter rest whose ink
the reader reads as a filled sharp (Litolff 9/1/0/0)."""
import json
import os
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import page_accidental_ink as PAI
from tools.omr.staged import page_claim_names as PCN
from tools.omr.tests.real_rest_cases import CropRaw

DATA = pathlib.Path(__file__).with_name("data_accidental_boxed_as_other.npz")
META = json.loads(str(np.load(DATA)["meta"]))
ACCIDENTALS = [k for k, v in META.items() if v["side"] == "accidental"]
RESTS = [k for k, v in META.items() if v["side"] == "rest"]


def region(name):
    z = np.load(DATA)
    m = META[name]
    strokes, masks = [], []
    for n, s in enumerate(m["strokes"]):
        st = SimpleNamespace(**{k: v for k, v in s.items() if k not in ("mask_xy", "box", "touches", "joined_to")})
        st.box = tuple(s["box"])
        st.touches = [(int(j), float(c)) for j, c in s["touches"]]
        st.joined_to = [(int(j), w) for j, w in s["joined_to"]]
        st.parts = []
        strokes.append(st)
        masks.append((z["%s__m%d" % (name, n)], s["mask_xy"][0], s["mask_xy"][1]))
    pm = SimpleNamespace(strokes=strokes, masks=masks, scale=m["scale"], sp=m["sp"], barlines=[])
    heads = [PAI.Head(b, c, k) for b, c, k in m["heads"]]
    raw = CropRaw(z["%s__raw" % name], m["raw_origin"], m["page_shape"])
    return m, pm, heads, raw


def verdict(name, with_accidentals):
    m, pm, heads, raw = region(name)
    accs = []
    if with_accidentals:
        found, _ = PAI.read_page(pm.strokes, pm.sp, heads, m["boxed"], m["rects"], m["reads"], m["ids"], m["header"],
                                 {int(k): v for k, v in m["owners"].items()}, fused=True, masks=pm.masks, scale=pm.scale)
        accs = [c for c in found if c["type"] in PCN.ACC_KINDS]
    index = PCN.StrokeIndex(*PCN._boxes_of(pm))
    r = m["rest"]
    return PCN.rest_box_verdict(pm, index, raw, r["pb"], r["cls"], r["owner"], r["detail"], accs, heads)


def test_flag_default_off():
    os.environ.pop(PCN.ENV_ACCIDENTAL_BOXED_AS_OTHER, None)
    assert PCN.accidental_boxed_as_other_enabled() is False
    os.environ[PCN.ENV_ACCIDENTAL_BOXED_AS_OTHER] = "1"
    try:
        assert PCN.accidental_boxed_as_other_enabled() is True
    finally:
        os.environ.pop(PCN.ENV_ACCIDENTAL_BOXED_AS_OTHER, None)


def test_the_fixture_holds_both_sides():
    assert len(ACCIDENTALS) >= 4 and len(RESTS) >= 9


@pytest.mark.parametrize("name", ACCIDENTALS)
def test_a_sharp_boxed_as_a_rest_files_no_rest_claim(name):
    on = verdict(name, True)
    assert on["standing"] == "weak" and on["why"] == "a_sharp_before_its_note", (name, on["why"])
    acc = on["accidental"]
    assert acc["share"] >= PCN.ACC_INK_SHARE_MIN and acc["dy_sp"] <= PCN.ACC_HEAD_DY_MAX_SP and acc["gap_sp"] <= PCN.ACC_HEAD_GAP_MAX_SP


@pytest.mark.parametrize("name", ["p2_2_0_1_3_sharp_as_16th_rest", "p2_2_0_2_3_sharp_as_16th_rest"])
def test_the_control_fails_without_the_rule(name):
    # the two Litolff p2 sharps stand as READ 16th rests without the accidental reading (the overnight wrote them as rests; 2.288's two-uprights guard
    # misses a sharp the thick ink filled in)
    off = verdict(name, False)
    assert off["standing"] == "READ" and off["why"] == "stands_free"


@pytest.mark.parametrize("name", RESTS)
def test_never_a_real_rest(name):
    off, on = verdict(name, False), verdict(name, True)
    assert (on["standing"], on["why"]) == (off["standing"], off["why"]), (name, META[name]["sean"], off["why"], on["why"])
    assert on["accidental"] is None


def test_never_a_rest_whose_note_is_not_just_right_of_it():
    # Litolff 9/1/0/0: a quarter rest whose filled ink the reader reads as a sharp; the only "head" to its right is a barline sliver 3.5 spaces away.
    # The gap test is what keeps it a rest: widen it and the rule takes the rest (the control can fail).
    name = "p9_9_1_0_0_quarter_rest"
    assert verdict(name, True)["standing"] == "READ"
    saved = PCN.ACC_HEAD_GAP_MAX_SP
    try:
        PCN.ACC_HEAD_GAP_MAX_SP = 9.0
        assert verdict(name, True)["why"] == "a_sharp_before_its_note"
    finally:
        PCN.ACC_HEAD_GAP_MAX_SP = saved


def test_never_a_flat():
    assert "flat" not in PCN.ACC_KINDS
