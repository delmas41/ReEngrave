"""ROADMAP 2.290 build (plan steps 1, 2, 4): one head identity from the ink, one claim per head on the page ledger. Pure parts only (fast tier);
the real-page controls are `test_page_heads_one_real_cases_2_290.py` (Sean's named marks, their own pixels)."""
from types import SimpleNamespace

import numpy as np
import pytest

from tools.omr.staged import page_heads as PH
from tools.omr.staged import stroke_owner as SO

SP = 20.0


def test_flags_default_off(monkeypatch):
    monkeypatch.delenv(PH.ONE_ENV, raising=False)
    monkeypatch.delenv(PH.LEDGER_ENV, raising=False)
    assert not PH.one_enabled() and not PH.ledger_enabled()
    monkeypatch.setenv(PH.LEDGER_ENV, "1")
    assert not PH.ledger_enabled(), "the claim needs the one identity"
    monkeypatch.setenv(PH.ONE_ENV, "1")
    assert PH.one_enabled() and PH.ledger_enabled()


@pytest.mark.parametrize("args,want", [
    (("vertical", 0.12, 3.5, 0.12, 3.5), False),          # a stem
    (("horizontal", 2.2, 0.15, 0.15, 2.2), False),        # a ledger rung / line residue
    (("horizontal", 2.12, 0.56, 0.56, 2.12), False),      # the phantom doubleWhole's beam piece (Litolff p2 glyph/2/1/4/13/4: 2.12 x 0.56 sp)
    (("horizontal", 1.3, 0.45, 0.45, 1.3), True),         # a filled head's lens the staff line left
    (("curve", 4.0, 0.8, 0.1, 4.0), False),               # an arc piece
    (("curve", 1.2, 0.6, 0.1, 1.2), True),                # a hollow head's outline piece
    (("blob", 1.3, 1.0, 1.0, 1.3), True),
    (("blob", 2.6, 3.2, 1.0, 3.2), True),                 # Litolff fuses heads: the part inside the box counts
])
def test_is_head_ink(args, want):
    assert PH.is_head_ink(*args) is want


def _it(cx, cy, ink=100, tall=False, scope=(0, 0), w=1.3, h=1.0):
    return dict(cx=cx * SP, cy=cy * SP, ink_px=ink, tall=tall, scope=scope,
                box=((cx - w / 2) * SP, (cy - h / 2) * SP, (cx + w / 2) * SP, (cy + h / 2) * SP))


def test_same_head_rules():
    a = _it(10, 10)
    assert PH.same_head(a, _it(10.1, 10.05), 90, SP) is None                    # a twin box on the same head
    assert PH.same_head(a, _it(11.2, 10.5), 60, SP) == "two_ovals"             # a second fused into one blob: the heads either side of the stem
    assert PH.same_head(a, _it(10, 11.0), 60, SP) == "two_ovals"               # a third on one side of a stem, fused
    assert PH.same_head(a, _it(10, 10, tall=True), 100, SP) == "tall_read"
    assert PH.same_head(a, _it(10, 10, ink=0), 0, SP) == "no_head_ink"
    assert PH.same_head(a, _it(10, 10.1), 40, SP) == "share_below"
    assert PH.same_head(a, _it(10, 10.1), 0, SP) == "no_shared_ink"


def test_a_head_sized_stroke_is_one_head_wherever_each_box_was_drawn():
    # Litolff p11 glyph/11/0/3/16/1 + /2 (round 1): one box drawn ~0.7 sp off the head; the ink each CLIPS is off-centre (dy 0.52 sp)
    a = dict(_it(10, 10), anchor=7, anchor_head=True)
    b = dict(_it(10.1, 10.85), anchor=7, anchor_head=True)
    assert PH.same_head(a, b, 80, SP) is None
    # a stroke bigger than a head (fused chord) keeps the oval test
    assert PH.same_head(dict(a, anchor_head=False), dict(b, anchor_head=False), 80, SP) == "two_ovals"
    # two strokes: the oval test
    assert PH.same_head(a, dict(b, anchor=8), 80, SP) == "two_ovals"
    # a third apart on one head-sized stroke: two heads' pieces, never joined
    assert PH.same_head(a, dict(b, cy=11.0 * SP), 80, SP) == "two_ovals"
    # one x, half a step apart: nothing is printed a step apart on one side of a stem -> one head (round 1's same-pitch doubles)
    assert PH.same_head(a, _it(10.02, 10.5), 80, SP) is None


def test_no_ink_boxes_twin_each_other():
    items = [_it(10, 10, ink=0), _it(10.02, 10.01, ink=0), _it(20, 10, ink=0)]
    groups, how, _p = PH.partition(items, lambda i, j: 0, SP, 0.3)
    g = {i: k for k, gg in enumerate(groups) for i in gg}
    assert g[0] == g[1] != g[2]


def test_partition_twins_chords_and_no_ink_boxes():
    items = [_it(10, 10), _it(10.05, 10.02),            # 0, 1: one head boxed twice (two cells)
             _it(11.2, 10.5),                           # 2: its neighbour a second away
             _it(10.02, 10.0, ink=0),                   # 3: a box on no head ink over head 0 (IoU high): joins it, written once
             _it(30, 10, ink=0),                        # 4: a box over no head ink, nothing near: alone
             _it(10, 10, tall=True, h=3.0)]             # 5: a tall box over the chord: joins nothing
    shared = {(0, 1): 95, (0, 2): 20, (1, 2): 20, (0, 5): 100, (1, 5): 100, (2, 5): 100}

    def sh(i, j):
        return shared.get((min(i, j), max(i, j)), 0)
    groups, how, pairs = PH.partition(items, sh, SP, 0.3)
    g_of = {i: k for k, g in enumerate(groups) for i in g}
    assert g_of[0] == g_of[1] == g_of[3]
    assert len({g_of[0], g_of[2], g_of[4], g_of[5]}) == 4
    assert how[3] == "no_head_ink_twin" and how[4] == "no_head_ink" and how[5] == "tall_read" and how[2] == "alone" and how[0] == "ink"


def test_partition_never_crosses_a_system():
    items = [_it(10, 10, scope=(0, 0)), _it(10, 10, scope=(0, 1))]
    groups, _how, _p = PH.partition(items, lambda i, j: 100, SP, 0.3)
    assert len(groups) == 2


def test_choose_claims():
    ovals = {0: {1: 90, 2: 30, 3: 50, 5: 60}, 1: {3: 45, 4: 80}}
    totals = {1: 100, 2: 100, 3: 100, 4: 100, 5: 100}
    ok = {1: True, 2: True, 3: True, 4: True, 5: False}
    claims, cen = PH.choose_claims(ovals, totals, ok)
    assert claims[0] == [1]                         # 2: a sliver only; 3: two heads' ovals hold it (fused, step 5); 5: bigger than a head (fused)
    assert claims[1] == [4]
    assert cen == {"shared_by_two_heads": 1, "not_head_shaped_or_fused": 1}


def test_choose_claims_can_fail_without_the_other_head_rule(monkeypatch):
    # the control: with the other-head cut lifted, the fused stroke 3 IS claimed -- the rule is what keeps it out
    monkeypatch.setattr(PH, "OTHER_HEAD_MAX", 1.01)
    claims, _ = PH.choose_claims({0: {3: 50}, 1: {3: 45}}, {3: 100}, {3: True})
    assert claims[0] == [3]


def _ink(o, kind="blob", w=1.3, h=1.0, area=1.0):
    return SO.Ink(o, kind, (0.0, 0.0, w * SP, h * SP), max(w, h), min(w, h), area, SP, (), "r%d" % o, 0.0, "")


def test_settle_page_head_and_members_are_one_owner():
    inks = [_ink(0)]
    claims = [SO.Claim("glyph/0/0/0/1/2", "head", "noteheadBlack", (0,), (), "g1"),
              SO.Claim("glyph/0/0/1/1/5", "head", "noteheadBlack", (0,), (), "g2"),
              SO.Claim("page_head/r9", "head", "page_head", (0,), (), "r9", area=True, members=("glyph/0/0/0/1/2", "glyph/0/0/1/1/5"))]
    w = SO.own_strokes(inks, claims)[0]
    assert w.state == "decided" and w.family == "head" and w.by == "page_head"
    assert w.owners[0] == "page_head/r9" and set(w.owners) == {"page_head/r9", "glyph/0/0/0/1/2", "glyph/0/0/1/1/5"}
    for c in claims[:2]:
        assert SO.box_verdict(c, {0: w}, {0: inks[0]})["verdict"] == "owns"
    # a box of ANOTHER head on the same stroke keeps the stroke a twin (counted, never hidden)
    claims2 = claims + [SO.Claim("glyph/0/0/1/1/9", "head", "noteheadBlack", (0,), (), "g3")]
    assert SO.own_strokes(inks, claims2)[0].state == "merged"
    # without the page head (the flag OFF), two boxes are a twin exactly as before
    assert SO.own_strokes(inks, claims[:2])[0].state == "merged"


def test_page_head_claim_keeps_the_heads_shape_test():
    inks = [_ink(0, kind="vertical", w=0.12, h=3.5, area=0.4)]
    claims = [SO.Claim("page_head/r9", "head", "page_head", (0,), (), "r9", area=True, members=("glyph/0/0/0/1/2",))]
    w = SO.own_strokes(inks, claims)[0]
    assert w.state == "refused_claims", "a page head never owns a stem by being an area"


def test_page_head_never_takes_a_tier0_claim():
    inks = [_ink(0)]
    claims = [SO.Claim("acc/r1", "accidental_ink", "accidental_ink", (0,), (), "r1", area=True),
              SO.Claim("page_head/r9", "head", "page_head", (0,), (), "r9", area=True, members=("glyph/0/0/0/1/2",))]
    tiers = ((tuple(SO.TIERS[0]) + ("accidental_ink",)),) + tuple(SO.TIERS[1:])
    w = SO.own_strokes(inks, claims, tiers=tiers)[0]
    assert w.family == "accidental_ink"


def test_a_later_box_on_a_page_heads_ink_is_held_by_it():
    """The one consult's measure: a rest box standing on ink the ledger gave a PAGE HEAD is held by `page_head` (head tier, earlier than rests) and
    `page_head` is a final claim; the head's own member box is never held by it; with a per-cell head BOX owner (the flag OFF) the rest is held by `head`,
    which is NOT final (the 2.284 r5 rule: box-against-box is recorded, never a refusal)."""
    from tools.omr.staged.adjudicators import ink_consult as IC
    tiers = tuple(tuple(t) + ((IC.PAGE_HEAD_OWNER,) if "head" in t else ()) for t in SO.TIERS)
    rest = ("glyph/0/0/0/1/7", "rest", [(0, 1.0, 1.0, "decided", IC.PAGE_HEAD_OWNER, ("page_head/r9", "glyph/0/0/0/1/2"))])
    head = ("glyph/0/0/0/1/2", "head", [(0, 1.0, 1.0, "decided", "head", ("page_head/r9", "glyph/0/0/0/1/2"))])
    held = IC.held_by_earlier([rest, head], tiers)
    assert held["glyph/0/0/0/1/7"]["by"] == IC.PAGE_HEAD_OWNER and not held["glyph/0/0/0/1/7"]["owns"]
    assert "glyph/0/0/0/1/2" not in held
    assert IC.PAGE_HEAD_OWNER in IC.FINAL_BOX_CLAIMS and "head" not in IC.FINAL_BOX_CLAIMS
    off = IC.held_by_earlier([("glyph/0/0/0/1/7", "rest", [(0, 1.0, 1.0, "decided", "head", ("glyph/0/0/0/1/2",))])], SO.TIERS)
    assert off["glyph/0/0/0/1/7"]["by"] == "head"


def test_apply_to_page_marks():
    from tools.omr.staged.page_marks import Marks
    marks = Marks(mark_of={"glyph/0/0/0/1/1": 0, "glyph/0/0/1/1/1": 1, "glyph/0/0/0/1/3": 2},
                  members={0: ["glyph/0/0/0/1/1"], 1: ["glyph/0/0/1/1/1"], 2: ["glyph/0/0/0/1/3"]}, pairs={},
                  why={"glyph/0/0/0/1/1": "alone", "glyph/0/0/1/1/1": "alone", "glyph/0/0/0/1/3": "alone"})
    oh = PH.OneHeads()
    oh.group_of_key = {"glyph/0/0/0/1/1": 0, "glyph/0/0/1/1/1": 0}
    m = PH.apply_to_page_marks(marks, oh)
    assert m.mark_of["glyph/0/0/0/1/1"] == m.mark_of["glyph/0/0/1/1/1"] != m.mark_of["glyph/0/0/0/1/3"]
    assert m.why["glyph/0/0/1/1/1"] == "page_head" and m.why["glyph/0/0/0/1/3"] == "alone"


def test_core_on_a_synthetic_frame():
    # two heads a third apart fused into one stroke, a twin box on the upper one, a phantom box on a beam piece
    s = 1.0
    lab = np.zeros((200, 200), np.int32)
    binary = np.full((200, 200), 255, np.uint8)
    lab[40:60, 40:66] = 1                     # head A (26 x 20 px = 1.3 x 1.0 sp)
    lab[80:100, 40:66] = 2                    # head B, a third below
    lab[150:161, 100:142] = 3                 # a beam piece, 2.1 x 0.55 sp
    binary[lab > 0] = 0
    props = [("blob", 1.3, 1.0, 1.0, 1.3), ("blob", 1.3, 1.0, 1.0, 1.3), ("horizontal", 2.1, 0.55, 0.55, 2.1)]
    items = [dict(key="glyph/0/0/0/1/0", cell=(0, 0, 0, 1), gi=0, box=(39.0, 39.0, 67.0, 61.0), cls="noteheadBlack", conf=0.9, scope=(0, 0), sp_head=SP),
             dict(key="glyph/0/0/1/1/0", cell=(0, 0, 1, 1), gi=0, box=(40.0, 40.0, 66.0, 62.0), cls="noteheadBlack", conf=0.8, scope=(0, 0), sp_head=SP),
             dict(key="glyph/0/0/0/1/1", cell=(0, 0, 0, 1), gi=1, box=(39.0, 79.0, 67.0, 101.0), cls="noteheadBlack", conf=0.9, scope=(0, 0), sp_head=SP),
             dict(key="glyph/0/0/0/1/2", cell=(0, 0, 0, 1), gi=2, box=(100.0, 148.0, 142.0, 163.0), cls="noteheadDoubleWholeSquare", conf=0.3,
                  scope=(0, 0), sp_head=SP)]
    oh = PH.core(items, [], lab, props, binary, s, SP)
    g = oh.group_of_key
    assert g["glyph/0/0/0/1/0"] == g["glyph/0/0/1/1/0"] != g["glyph/0/0/0/1/1"] != g["glyph/0/0/0/1/2"]
    assert oh.how[3] == "no_head_ink"
    heads = {h["rep"]: h for h in oh.heads}
    assert "glyph/0/0/0/1/2" not in heads, "a box over no head ink makes no head"
    assert heads["glyph/0/0/0/1/0"]["strokes"] == [0] and heads["glyph/0/0/0/1/1"]["strokes"] == [1]
