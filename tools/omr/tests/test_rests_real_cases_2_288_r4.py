"""ROADMAP 2.288 round 4 -- Sean's answered rest tiles replayed on their REAL page strokes and pixels (no synthetic drawing; `real_rest_cases.py`).

Rule 7 / Sean 2026-11-10: round 3's control "a notehead fused to the line stays refused" was a drawing and passed while a real notehead on a line (Brahms p14, tile 4,
"eighth note") was claimed as a whole rest. Here the control IS tile 4: its stroke, the stem beside it and the page pixels it sits on. Every box Sean called a rest must
still stand (or be refused only for a NAMED reason); every box he called a note, stem, flag or natural must be refused.

Fast tier: the fixtures are small `.npz` files of the page (`benchmarks/rests-claim-first-2026-11/real_cases/`), made by `dump_real_cases.py` from a real gather."""
import pytest

from tools.omr.staged import ink_attachment as IA
from tools.omr.staged import page_claim_names as PCN
from tools.omr.tests import real_rest_cases as RC

import json

CASES = {c["id"]: c for c in json.load(open(RC.CASES_JSON))}
IDS = RC.case_ids()

#: a real rest the reader still refuses, and WHY (named, measured): the box is not the rest's ink.
KNOWN_OPEN = {
    # Brahms p14 r3 tile 1, a real whole rest: the detector box covers 47% of the block's own ink (box 0.8 sp wide, block 1.5 sp), under the register's one 0.5 cut.
    # No neighbour touches it (touches []): not 2.290 step 5's merged ink, a short detector box.
    "r3-01": "names_no_stroke",
}
#: a real rest refused for the one merged-ink reason (a note's ink touches it; ROADMAP 2.290 step 5 owns it)
MERGED_INK = ("touches_a_head",)
#: Sean's word is a LETTER ('the CR from crescendo', r1 tile 10): the rest box's own verdict is READ (the shape alone cannot tell), and the word's READ area claim wins the settle in
#: the gather (`gather_page_claim_boxes`, claims in the order they stand): the r3 gather files NO claim on those strokes (checked on the Litolff p2 record).
WON_BY_AN_EARLIER_CLAIM = {"r1-10": "the word's READ area claim"}


def test_the_fixtures_are_there():
    assert len(IDS) >= 20, IDS
    assert set(IDS) <= set(CASES)


@pytest.mark.parametrize("cid", IDS)
def test_the_reader_agrees_with_sean_on_the_real_page(cid):
    case, c = CASES[cid], RC.load(cid)
    v = RC.verdict(c)
    if case["is_rest"]:
        if v["standing"] == "READ":
            assert v["ids"], "a rest that stands claims ink"
        else:
            assert v["why"] in MERGED_INK or KNOWN_OPEN.get(cid) == v["why"], (cid, case["sean"], v["why"])
    elif cid not in WON_BY_AN_EARLIER_CLAIM:
        assert v["standing"] != "READ", (cid, case["sean"], "claimed as a rest", v["ids"])


def test_tile_4_the_notehead_on_a_line_is_not_a_rest():
    """Brahms p14, Sean: 'eighth note'. A filled head centred on its line, first note of a beamed group. Both shared questions refuse it, each alone."""
    c = RC.load("r3-04")
    pm, raw = c["page_map"], c["raw"]
    v = RC.verdict(c)
    assert v["standing"] == "weak" and v["why"] == "hangs_from_a_stem_with_a_head"
    own = v["ids"]
    att = IA.attachment(pm, own)
    assert att["stem_with_head"], "its stem carries the head, and the head is the claimed ink itself (round 2 asked only for a head OUTSIDE the ink)"
    sides = IA.line_sides(pm, own[0], raw)
    assert sides["both_sides"] and not sides["two_lines"]                    # ink on both sides of its line: centred on it
    assert sides["above_sp"] >= IA.SIDE_MIN_SP and sides["below_sp"] >= IA.SIDE_MIN_SP
    # the side rule alone also refuses it, with the stem question switched off
    assert PCN.rest_standing(c["detail"], dict(stem_with_head=[], touches_a_head=[], bare_stroke=False), sides)[1] == "ink_on_both_sides_of_its_line"


@pytest.mark.parametrize("cid", [i for i in ("r3-02", "r3-03", "r3-09", "r1-05") if i in IDS])
def test_a_real_whole_rest_hangs_from_its_line_on_one_side(cid):
    """The mirror: real whole rests (Sean: 'whole rest') hang from a line, ink below it only (above: 0.00-0.12 sp of scan roughness), and still claim."""
    c = RC.load(cid)
    v = RC.verdict(c)
    assert v["standing"] == "READ" and v["ids"], v["why"]
    sides = IA.line_sides(c["page_map"], v["ids"][0], c["raw"])
    assert sides and not sides["both_sides"] and not sides["two_lines"] and sides["below_sp"] > sides["above_sp"]


@pytest.mark.parametrize("cid", [i for i in ("r2-07", "r2-12") if i in IDS])
def test_a_real_head_boxed_as_a_block_rest_is_refused(cid):
    """Sean: 'a quarter note' / 'an eighth note'. A head boxed as restWhole / restHalf: its stem, and its ink either side of / between lines, refuse it."""
    c = RC.load(cid)
    v = RC.verdict(c)
    assert v["standing"] == "weak" and v["attachment"]["stem_with_head"]
    per = [s_ for s_ in (IA.line_sides(c["page_map"], i, c["raw"]) for i in v["ids"]) if s_]
    assert any(s_["both_sides"] or s_["two_lines"] for s_ in per)


def test_a_real_sharp_boxed_as_a_16th_rest_is_refused():
    """Litolff p8, Sean's 2.285 r1 tile 3 'sharp': the detector drew `rest16th` over it and round 3 claimed its strokes. Two long parallel verticals crossed by two bars: no rest holds two."""
    assert "acc-2285r1-03" in IDS, "the real sharp's fixture (dump_real_cases.py, Litolff p8)"
    c = RC.load("acc-2285r1-03")
    v = RC.verdict(c)
    assert c["cls"] == "rest16th" and v["standing"] == "weak" and v["why"] == "two_parallel_verticals", (v["standing"], v["why"])
    (p,) = v["pairs"]
    assert p["overlap"] >= IA.PAIR_OVERLAP_MIN and len(p["bars"]) >= IA.PAIR_BARS_MIN
    assert IA.parallel_verticals(c["page_map"], [p["a"]]) == []          # one vertical alone is not a pair


@pytest.mark.parametrize("cid", [i for i in IDS if CASES[i]["is_rest"]])
def test_no_real_rest_holds_two_long_verticals(cid):
    """What would FALSIFY the rule: a real rest (Sean named it) whose own strokes hold a crossed pair. Replayed on all 25 real rests; the first draft of the rule (no bars, no thickness)
    refused five real Breitkopf quarter / eighth rests on Brahms p14 and was tightened."""
    c = RC.load(cid)
    v = RC.verdict(c)
    assert not v["pairs"], (cid, v["pairs"])


@pytest.mark.parametrize("cid", [i for i in IDS if CASES[i].get("group") == "accidental"])
def test_an_accidental_sean_named_never_gets_a_rest_claim(cid):
    """Every accidental he named (registry 2.285 / 2.282 / 2.288) that a detector rest box meets is refused as a rest."""
    assert RC.verdict(RC.load(cid))["standing"] != "READ"


def test_the_questions_are_not_about_rests():
    """`ink_attachment` is for any reader: the answers do not name a rest."""
    c = RC.load("r3-04")
    own = [i for i, st in enumerate(c["page_map"].strokes) if st.kind == "vertical" and st.touches]
    assert IA.attachment(c["page_map"], own) is not None
    assert IA.line_sides(c["page_map"], 0, None) is None                    # no raster: no answer, never a guess
