"""lane-stem-end-head -- the head at an orphan stem's end READ from the page ink (flag OMR_STEM_END_HEAD_INK, default ON)."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from tools.omr.staged import stem_end_heads as SEH
from tools.omr.staged.gather import head_interior_white, notehead_ink_under

SP = 16.0


def page(lines=(100, 116, 132, 148, 164)):
    img = np.full((320, 400), 255, np.uint8)
    for y in lines:
        img[y:y + 2, 20:380] = 0
    return img


def black_head(img, cx, cy):
    cv2.ellipse(img, (cx, cy), (10, 7), -20, 0, 360, 0, -1)


def stem(img, x, y0, y1):
    img[y0:y1, x:x + 2] = 0


def read(img, stem_page, end):
    return SEH.ink_head_at_end(img, stem_page, end, SP, [], head_interior_white, notehead_ink_under)


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(SEH.STEM_END_HEAD_INK_ENV, raising=False)
    assert SEH.ink_enabled() is True
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv(SEH.STEM_END_HEAD_INK_ENV, v)
        assert SEH.ink_enabled() is False


def test_black_head_left_of_an_up_stem_is_read():
    img = page()
    black_head(img, 150, 140)
    stem(img, 159, 80, 140)
    got = read(img, (160.0, 80.0, 140.0), "bottom")
    assert got["head"], got
    assert got["value"] == "filled"
    tx0, ty0, tx1, ty1 = got["trimmed"]
    assert tx0 < 150 < tx1 and ty0 < 140 < ty1


def test_nothing_at_the_other_end_and_wrong_side_is_not_a_head():
    img = page()
    black_head(img, 150, 140)
    stem(img, 159, 80, 140)
    assert not read(img, (160.0, 80.0, 140.0), "top")["head"]
    img2 = page()
    black_head(img2, 172, 140)                      # the blot is RIGHT of an up-stem: not its head
    stem(img2, 159, 80, 140)
    assert not read(img2, (160.0, 80.0, 140.0), "bottom")["head"]


def test_a_beam_end_is_not_one_head():
    """2.210: a beam end at the tip is ink, but not ONE head"""
    img = page(lines=())
    img[134:142, 100:200] = 0                       # a beam, 0.5 sp thick, running past the head's width both ways
    stem(img, 159, 80, 142)
    got = read(img, (160.0, 80.0, 142.0), "bottom")
    assert not got["head"]


def test_a_bare_stem_tip_is_no_head():
    img = page()
    stem(img, 159, 80, 140)
    assert not read(img, (160.0, 80.0, 140.0), "bottom")["head"]


def test_combine():
    ink = {"head": True, "trimmed": [140, 133, 161, 147]}
    assert SEH.combine([141, 134, 160, 146], ink)[0] == "agree"
    assert SEH.combine([241, 134, 260, 146], ink)[0] == "abstain"
    assert SEH.combine([141, 134, 160, 146], {"head": False, "why": "not_one_head:too_wide"}) == (
        "abstain", "rerun_only_ink_reads:not_one_head:too_wide")
    assert SEH.combine(None, ink)[0] == "ink_only"
    assert SEH.combine(None, {"head": False, "why": "no_head_ink"})[0] == "none"


def test_ink_head_class():
    assert SEH.ink_head_class("filled", 100.0, 100.0, 50.0) == "noteheadBlackOnLine"
    assert SEH.ink_head_class("hollow", 150.0, 100.0, 50.0) == "noteheadHalfInSpace"


# --- round 2 (Sean's tiles 2026-10-29: a bar number, key flats, a flag) ---------------------------------------------------------------

def test_a_flat_bowl_on_the_far_side_of_its_stem_is_not_a_head():
    """Tile 8: a flat's stem stands at the bowl's LEFT; read as an up-stem the 'head' runs on past the stem: the stem is inside the ink."""
    img = page(lines=())
    stem(img, 150, 80, 146)                                    # the flat's stem
    cv2.ellipse(img, (147, 140), (10, 6), -20, 0, 360, 0, 2)   # its bowl, running on past the stem (Litolff p4 tile 8: 0.50 sp)
    got = read(img, (151.0, 80.0, 146.0), "bottom")
    assert not got["head"], got
    assert got["why"] == "stem_inside_the_ink" and got["far_side_sp"] > SEH.CROSS_SPACES


def test_far_side_reach_is_filed_on_a_real_head():
    img = page()
    black_head(img, 150, 140)
    stem(img, 159, 80, 140)
    got = read(img, (160.0, 80.0, 140.0), "bottom")
    assert got["head"] and got["far_side_sp"] is not None and got["far_side_sp"] <= SEH.CROSS_SPACES


class _Row:
    def __init__(self, value, **detail):
        self.value, self.detail, self.id = value, detail, "obs:x"


def test_claims_holding_any_owner_area_and_ink():
    box = [100.0, 100.0, 120.0, 112.0]
    key = "glyph/4/0/6/0/12"
    named = _Row([90, 90, 140, 130], owner="key_signature", unit="area", boxes_inside={key: {"named": True, "ink_share_inside": 1.0}})
    assert SEH.claims_holding([named], key, box, None, 0)[0][1]["owner"] == "key_signature"
    # an owner the register never measured the box for (a word claim, a barline column): the box's own area share
    word = _Row([95, 95, 125, 115], owner="word", unit="area")
    assert SEH.claims_holding([word], key, box, None, 0)[0][1]["how"] == "box_share"
    beside = _Row([118, 95, 140, 115], owner="barline", unit="area")
    assert SEH.claims_holding([beside], key, box, None, 0) == []
    arc = _Row([[0, 3], [0, 4], [1, 9]], owner="arc", unit="ink")
    assert SEH.claims_holding([arc], key, box, [3, 4, 7], 0)[0][1]["owner"] == "arc"
    assert SEH.claims_holding([arc], key, box, [3, 4, 7], 1) == []
    clef_ink = _Row([3, 4], owner="clef", unit="ink", cell=0)
    assert SEH.claims_holding([clef_ink], key, box, [3, 4], 0)
    assert SEH.claims_holding([clef_ink], key, box, [3, 4], 2) == []


def test_stroke_claim_and_ink_only():
    assert SEH.stroke_claim(("refused", [(3, "decided", "arc_trace", "")])) == "arc_trace"
    assert SEH.stroke_claim(("refused", [(3, "decided", "accidental", "")])) is None   # in-bar accidentals come after heads: no claim
    assert SEH.stroke_claim(("owns", [])) is None
    assert SEH.is_ink_only({"source": "stem_end_head", "ink_verdict": "ink_only"})
    assert not SEH.is_ink_only({"source": "stem_end_head", "ink_verdict": "agree"})


# --- round 3 (Sean 2026-10-29, r2 tile 7: "too rectangular to capture the full bite whose ink overlaps the staff lines") ---------------

def test_trim_head_files_the_head_with_its_rim_on_the_lines():
    """A black head in a space, its rim fused into both lines: the line-only trim strips the line rows; `rim_trimmed` keeps them."""
    from tools.omr.staged import head_ink
    img = np.full((320, 400), 255, np.uint8)
    for y in (100, 116, 132, 148, 164):
        img[y:y + 3, 20:380] = 0
    cv2.ellipse(img, (150, 125), (10, 9), -20, 0, 360, 0, -1)    # spans the rows of the lines at 116 and 132
    t = head_ink.trim_head(img, (138.0, 115.0, 162.0, 135.0), SP)
    assert t["trimmed"] is not None and t["rim_trimmed"] is not None
    assert t["rim_trimmed"][1] < t["trimmed"][1] and t["rim_trimmed"][3] > t["trimmed"][3]
    assert t["rim_extent_sp"][1] > t["extent_sp"][1]


def test_rim_head_sized():
    assert SEH._rim_head_sized({"rim_extent_sp": [1.33, 1.0]})
    assert not SEH._rim_head_sized({"rim_extent_sp": [1.33, 0.4]})
    assert not SEH._rim_head_sized({"rim_extent_sp": [0.3, 1.0]})
    assert not SEH._rim_head_sized({})


def test_fill_from_slit_is_read_head_inks_cut():
    from tools.omr.staged import head_ink
    assert head_ink.fill_from_slit(None) == (None, None, "readers_split")
    assert head_ink.fill_from_slit(0.0)[0] == "filled"
    assert head_ink.fill_from_slit(0.5)[0] == "hollow"
    assert head_ink.fill_from_slit(0.1)[0] is None


def test_too_small_is_not_a_disagreement():
    """A re-run box whose own head-ink read is 'too_small' is the line-only trim of a head in a space, not 'not a head'."""
    from tools.omr.staged.adjudicators import notehead_precision as NP
    assert "too_small" not in NP.STEM_END_NOT_A_HEAD
    assert {"no_head_ink", "too_wide", "too_tall", "holds_another_marks_ink"} == set(NP.STEM_END_NOT_A_HEAD)
