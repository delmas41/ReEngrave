"""ROADMAP 2.284 r5 -- the ONE consult (`adjudicators/ink_consult.py`, flag `OMR_PAGE_LEDGER_OWNS`). Pure tests of the measure and the wiring check."""
from __future__ import annotations

import pathlib

from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.adjudicators import ink_consult as IC


def test_flag_follows_the_page_ledger(monkeypatch):
    monkeypatch.delenv("OMR_PAGE_LEDGER_OWNS", raising=False)
    assert not IC.enabled()
    monkeypatch.setenv("OMR_PAGE_LEDGER_OWNS", "1")
    assert IC.enabled()


def test_tiers_areas_first_consumers_last():
    assert IC.tier_of("barline", SO.TIERS) == 0
    assert IC.tier_of("tremolo", SO.TIERS, ["tremolo"]) == 0          # a layer a later lane files is an area claim: tier 0
    assert IC.tier_of("head", SO.TIERS) < IC.tier_of("dynamic", SO.TIERS) < IC.tier_of("flag", SO.TIERS)


def test_a_dynamic_on_a_heads_ink_is_held_by_an_earlier_claim():
    # a `dynamicP` box whose own ink is 80% a head's decided blob, 20% unclaimed: held 0.8 by `head`, owns nothing
    boxes = [("gP", "dynamic", [(0, 1.0, 8.0, "decided", "head", ("gH",)), (1, 1.0, 2.0, "unclaimed", None, ())])]
    held = IC.held_by_earlier(boxes, SO.TIERS)
    assert held["gP"]["by"] == "head" and held["gP"]["share"] == 0.8 and not held["gP"]["owns"] and not held["gP"]["area"]
    assert IC.refusal_kind("head", False) == "earlier_mark"


def test_a_later_claim_never_holds_an_earlier_box():
    # a head box standing on a dynamic's ink: the dynamic is a LATER tier, so it holds nothing of the head (CLAUDE section 3: a later reader marks, never takes)
    boxes = [("gH", "head", [(0, 1.0, 8.0, "decided", "dynamic", ("gP",))])]
    assert IC.held_by_earlier(boxes, SO.TIERS) == {}


def test_a_box_that_owns_its_own_stroke_says_so():
    boxes = [("gF", "flag", [(0, 1.0, 6.0, "decided", "barline", ("area",)), (1, 1.0, 4.0, "decided", "flag", ("gF",))])]
    held = IC.held_by_earlier(boxes, SO.TIERS, ["barline"])
    assert held["gF"]["by"] == "barline" and held["gF"]["owns"] and held["gF"]["area"]
    assert IC.refusal_kind("barline", True) == "barline" and IC.refusal_kind("clef", True) == "page_claim"


def test_contested_ink_is_no_witness():
    boxes = [("gT", "text", [(0, 1.0, 9.0, "contested", "head", ("gH", "gX"))])]
    assert IC.held_by_earlier(boxes, SO.TIERS) == {}


def test_every_box_family_is_on_the_one_consult_and_the_check_can_fail(tmp_path):
    assert IC.unconsulted() == [] and IC.not_on_the_one_consult() == []
    # rule 7: a tree whose dynamic decider consults nothing is FOUND
    here = pathlib.Path(IC.__file__).resolve().parent.parent
    root = tmp_path / "staged"
    (root / "adjudicators").mkdir(parents=True)
    for rel, _fn in set(IC.FAMILY_DECIDERS.values()):
        src = (here / rel).read_text()
        if rel.endswith("family_precision.py"):
            i = src.index("def adjudicate_dynamic_is_not_a_dynamic(")
            j = src.index("@decision", i)
            body = src[i:j].replace('ink = _ink_consult_refusal(ev, "dynamic", detail)', "ink = None")
            src = src[:i] + body + src[j:]
        (root / rel).write_text(src)
    bad = IC.unconsulted(root)
    assert [b["family"] for b in bad] == ["dynamic"] and IC.not_on_the_one_consult(root) == ["dynamic"]
