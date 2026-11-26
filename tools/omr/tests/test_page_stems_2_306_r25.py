"""ROADMAP 2.306 r25 (round 9) -- the page stem reader, STAGED GATHER, inside `OMR_PAGE_STEMS` (default OFF). Sean 2026-11-25 on the 36 tiles of
the heads the old cell join still decided: "Aside from tile 5 that is boxing an ff the rest are all easily seen as noteheads with stems"
(`out/print/2.306-r24-old-join/answers.json`). Which stem each head is on is OUR look at the print.

Controls are REAL page windows cut from the reader's exact inputs pickled during a gather (`benchmarks/page-ledger-2026-11/2306/r23_cut_window.py`);
each is shown failing with its switch off (CLAUDE rule 7).

(item 2) THE RINGS' SIDE IS TOLD BY THE PARTNER'S INK, NOT ITS BOX (`_rings_side_by_ink`). Two half notes a third apart on one up stem; the upper
    head's left stroke runs down the rings' common side into the lower ring, where a tie leaving the lower ring fuses onto it, 0.26 / 0.03 spaces
    past the lower head's BOX. Its ink joins the partner's head ink and it is shorter than a stem: the rings' side, so the shared stroke is the
    head's stem. Never where the stroke is a stem's length; never by the box.
"""
import json
import os

import pytest

from tools.omr.staged import page_stems as PS

HERE = os.path.dirname(__file__)
WIN = os.path.join(HERE, "fixtures", "page_stems_2_306_r25.json")


def _read(name):
    w = json.load(open(WIN))[name]
    heads = [dict(h, box=tuple(h["box"])) for h in w["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in w["verticals"]]
    cross = [dict(c, box=tuple(c["box"])) for c in w["crossers"]]
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in w["strokes"].items()}
    held = {int(k): v for k, v in w["held"].items()}
    return w, PS.read(heads, verts, held, crossers=cross, strokes=strokes)["heads"][w["head"]]


PARTNER = ["partner_ink_up_litolff_2_1_2_12_3", "partner_ink_up_litolff_9_0_2_10_5"]


@pytest.mark.parametrize("name", PARTNER)
def test_the_rings_side_joins_the_partners_ink(name):
    """Litolff 2/1/2/12/3 and 9/0/2/10/5 (tiles 18 and 23): A4 half notes, the upper of two a third apart on one up stem."""
    w, got = _read(name)
    assert got["state"] == "one" and got["how"] == PS.CHORD_HOW and got["direction"] == w["expect"], got


@pytest.mark.parametrize("name", PARTNER)
def test_partner_ink_off_the_head_is_left_to_the_old_join(name, monkeypatch):
    """r24's reading: the rings' side runs past the partner's box, so 'one stem passes the head' and the old join answers."""
    monkeypatch.setattr(PS, "R25_PARTNER_INK", False)
    w, got = _read(name)
    assert got["state"] == "two_voices" and got.get("why") == "one_stem_passes_the_head", got


def test_the_rings_side_is_never_a_stems_length(monkeypatch):
    """The never side, on the same real window: were the rings' side a stem's length it could be a second voice's stem passing its partner's
    ring (touching it) -- the rule must not take it. The stroke's measured reach is the only thing changed (the rule reads nothing else of it)."""
    w, _got = _read(PARTNER[0])
    h = next(h for h in w["heads"] if h["id"] == w["head"])
    cy = (h["box"][1] + h["box"][3]) / 2.0
    assert PS._rings_side_by_ink(h, 3663, "down", {"reach": PS.STEM_MIN_SP}, [dict(id=455, box=(2221, 2458, 2242, 2474))], lambda k, o: True) is False
    assert PS._rings_side_by_ink(h, 3663, "down", {"reach": 2.19}, [dict(id=455, box=(2221, 2458, 2242, 2474))], lambda k, o: True) is True
    assert PS._rings_side_by_ink(h, 3663, "down", {"reach": 2.19}, [dict(id=455, box=(2221, 2458, 2242, 2474))], lambda k, o: False) is False
    assert cy < (2458 + 2474) / 2.0
