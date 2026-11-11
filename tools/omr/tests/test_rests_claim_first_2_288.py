"""ROADMAP 2.288 -- a rest that STANDS READ claims its own ink on the page ledger, and the own-ink accidental reader is refused that ink BY THE LEDGER (`claimed_by:rest`),
not by the private list of detector rest boxes 2.285 round 2 kept (`page_accidental_ink.read_page(rests=...)`, which flag-ON no longer fills).

The two 2.285 round-1 false claims (Brahms p14 near (3068,2731) and (3986,547): correct quarter rests read as flats) are the flat-shaped ink below; each refusal has a CONTROL twin
that is claimed when no rest stands there.
"""
from types import SimpleNamespace

from tools.omr.staged import page_accidental_ink as PAI
from tools.omr.staged import page_claim_names as PCN
from tools.omr.staged import record as R

from .test_page_accidental_ink_consult_2_285 import SP, _Log, _Row, flat, head_right

CELL = R.cell(0, 0, 0, 0)

# the measured spellings (`rest_ink.py`): a quarter rest's thin run 0.40-0.70 sp, a stem's 1.45-2.98; a head's blob 0.87-1.48, a rest's 0.22-0.70
QUARTER_REST = {"thin_run_sp": 0.55, "blob_sp": 0.4, "head_ink_sp2": 0.0}
STEM = {"thin_run_sp": 2.4, "blob_sp": 0.0, "head_ink_sp2": 0.0}
STEM_WITH_HEAD = {"thin_run_sp": 2.4, "blob_sp": 1.2, "head_ink_sp2": 0.8}
FLAT_STEM = {"thin_run_sp": 1.8, "blob_sp": 0.5, "head_ink_sp2": 0.0}


def test_a_rest_stands_READ_only_when_its_ink_stands_free_and_every_cannot_tell_is_weak():
    assert PCN.rest_standing(QUARTER_REST) == ("READ", "stands_free")
    assert PCN.rest_standing(STEM)[0] == "weak"                  # the control that can fail: a long thin stroke is a stem, a flat's or a sharp's vertical
    assert PCN.rest_standing(FLAT_STEM)[0] == "weak"
    assert PCN.rest_standing(STEM_WITH_HEAD) == ("weak", "stroke_into_a_head")
    assert PCN.rest_standing(None) == ("weak", "no_ink_contact_row")        # rule 8: no measurement is never READ
    assert PCN.rest_standing({}) == ("weak", "no_ink_contact_row")


def test_the_rest_families_are_step_3s_only_with_their_own_flag(monkeypatch):
    assert PCN.box_owner("restQuarter", None) is None and PCN.box_owner("restQuarter", None, True) == "rest"
    assert PCN.box_owner("restWhole", None, True) == "whole_rest"
    assert PCN.box_owner("dynamicForte", None, True) == "dynamic"           # the old family stays the old flag's: the caller filters on `boxes_enabled()`
    monkeypatch.delenv(PCN.ENV_RESTS, raising=False)
    assert not PCN.rests_enabled()
    monkeypatch.setenv(PCN.ENV_RESTS, "yes")
    assert PCN.rests_enabled()
    monkeypatch.setenv(PCN.ENV_RESTS, "")
    assert not PCN.rests_enabled()


def test_CONTROL_flat_shaped_ink_is_claimed_with_no_rest_claim_and_refused_by_the_ledger_with_one():
    strokes = flat()
    found, _ = PAI.read_page(strokes, SP, [head_right()], [], [])
    assert len(found) == 1 and found[0]["type"] == "flat"                   # the control: the ink IS an accidental's when no rest holds it
    # the ledger holds both strokes: a READ rest claim on the log (`unit: page_ink`, `page_strokes`), as `gather_page_claim_boxes` files it
    rows = [_Row([0, 1], unit="page_ink", standing="READ", owner="rest", source="page_boxes", page_strokes=[0, 1])]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    owners = PAI.earlier_owners(_Log(rows), None)
    assert owners == {0: "rest", 1: "rest"}
    found, why = PAI.read_page(strokes, SP, [head_right()], [], rects, [], ids, (), (), owners)
    assert found == [] and why.get("claimed_by:rest") >= 1 and why["claimed"] == 0 and "rest_box" not in why


def test_a_rest_claim_on_other_ink_refuses_nothing_here():
    rows = [_Row([7, 8], unit="page_ink", standing="READ", owner="rest", source="page_boxes", page_strokes=[7, 8])]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    found, _ = PAI.read_page(flat(), SP, [head_right()], [], rects, [], ids, (), (), PAI.earlier_owners(_Log(rows), None))
    assert len(found) == 1


def test_the_readers_own_rows_are_not_read_back_as_an_earlier_owner():
    rows = [_Row([0, 1], unit="page_ink", standing="READ", owner=PAI.OWNER, page_strokes=[0, 1])]
    assert PAI.earlier_owners(_Log(rows), None) == {}


def test_flag_OFF_still_consults_the_private_rest_list_so_OFF_is_the_main_behaviour():
    found, why = PAI.read_page(flat(), SP, [head_right()], [], [], rests=[(95.0, 95.0, 125.0, 160.0)])
    assert found == [] and why.get("rest_box") == 1


def test_a_read_rest_owns_its_own_ink_and_not_a_stem_beside_it():
    """`_rest_stroke_fits`: a vertical longer than a rest (a neighbouring stem) is refused by the printed shape; a quarter rest's slanted stroke (reads as a short vertical) stays."""
    def st(kind, x, y, w, h):
        return SimpleNamespace(kind=kind, box=(x, y, w, h), length_sp=max(w, h) / SP, thickness_sp=0.2, area_sp2=0.4, angle_deg=90.0 if kind == "vertical" else 0.0,
                               staff_space_local=SP)
    pm = SimpleNamespace(strokes=[st("vertical", 0, 0, 4, 50), st("vertical", 20, 0, 3, 100)], sp=SP)
    assert PCN._rest_stroke_fits(pm, 0, "rest", "restQuarter")              # 2.5 sp: a rest's slanted stroke
    assert not PCN._rest_stroke_fits(pm, 1, "rest", "restQuarter")          # 5 sp: a stem
