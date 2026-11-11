"""ROADMAP 2.288 -- a rest that STANDS READ claims its own ink on the page ledger, and the own-ink accidental reader is refused that ink BY THE LEDGER (`claimed_by:rest`),
not by the private list of detector rest boxes 2.285 round 2 kept (RETIRED at the landing: flag default ON, the list deleted).

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


FREE = dict(stem_with_head=[], touches_a_head=[], bare_stroke=False)


def test_a_rest_stands_READ_only_when_its_ink_stands_free_and_every_cannot_tell_is_weak():
    assert PCN.rest_standing(QUARTER_REST, FREE) == ("READ", "stands_free")
    assert PCN.rest_standing(STEM_WITH_HEAD, FREE) == ("weak", "stroke_into_a_head")
    assert PCN.rest_standing(None, FREE) == ("weak", "no_ink_contact_row")        # rule 8: no measurement is never READ
    assert PCN.rest_standing({}, FREE) == ("weak", "no_ink_contact_row")
    assert PCN.rest_standing(QUARTER_REST, None) == ("weak", "names_no_stroke")    # a box that names no page stroke (a barline's sliver) has nothing to claim
    # round 1's cell-raster rule, kept as the second witness
    assert PCN._contact_standing(STEM)[0] == "weak" and PCN._contact_standing(FLAT_STEM)[0] == "weak"


def test_the_rest_families_are_step_3s_only_with_their_own_flag(monkeypatch):
    assert PCN.box_owner("restQuarter", None) is None and PCN.box_owner("restQuarter", None, True) == "rest"
    assert PCN.box_owner("restWhole", None, True) == "whole_rest"
    assert PCN.box_owner("dynamicForte", None, True) == "dynamic"           # the old family stays the old flag's: the caller filters on `boxes_enabled()`
    monkeypatch.delenv(PCN.ENV_RESTS, raising=False)
    assert PCN.rests_enabled()                                              # default ON (Sean 2026-11-11), the opt-out of OMR_PAGE_TREMOLO
    for off in ("0", "false", "no", "off", " OFF "):
        monkeypatch.setenv(PCN.ENV_RESTS, off)
        assert not PCN.rests_enabled()
    monkeypatch.setenv(PCN.ENV_RESTS, "1")
    assert PCN.rests_enabled()
    # rest claims on do not switch the OTHER step-3 families on (`gather_page_claim_boxes` filters by `boxes_enabled()`)
    monkeypatch.delenv(PCN.ENV_BOXES, raising=False)
    assert not PCN.boxes_enabled()


def test_CONTROL_flat_shaped_ink_is_claimed_with_no_rest_claim_and_refused_by_the_ledger_with_one():
    strokes = flat()
    found, _ = PAI.read_page(strokes, SP, [head_right()], [], [])
    assert len(found) == 1 and found[0]["type"] == "flat"                   # the control: the ink IS an accidental's when no rest holds it
    # the ledger holds both strokes: a READ rest claim on the log (`unit: page_ink`, `page_strokes`), as `gather_page_claim_boxes` files it
    rows = [_Row([0, 1], unit="page_ink", standing="READ", owner="rest", source="page_boxes", page_strokes=[0, 1])]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    owners = PAI.earlier_owners(_Log(rows), None)
    assert owners == {0: "rest", 1: "rest"}
    found, why = PAI.read_page(strokes, SP, [head_right()], [], rects, [], ids, (), owners)
    assert found == [] and why.get("claimed_by:rest") >= 1 and why["claimed"] == 0 and "rest_box" not in why


def test_a_rest_claim_on_other_ink_refuses_nothing_here():
    rows = [_Row([7, 8], unit="page_ink", standing="READ", owner="rest", source="page_boxes", page_strokes=[7, 8])]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    found, _ = PAI.read_page(flat(), SP, [head_right()], [], rects, [], ids, (), PAI.earlier_owners(_Log(rows), None))
    assert len(found) == 1


def test_the_readers_own_rows_are_not_read_back_as_an_earlier_owner():
    rows = [_Row([0, 1], unit="page_ink", standing="READ", owner=PAI.OWNER, page_strokes=[0, 1])]
    assert PAI.earlier_owners(_Log(rows), None) == {}


def test_the_own_ink_accidental_reader_does_not_run_when_rest_claims_are_off(monkeypatch):
    """The dependency that replaced the private rest-box list: with `OMR_PAGE_CLAIM_RESTS` off no rest holds its ink on the ledger, so the reader (which would take a quarter rest's
    stem and curl for a flat, 2.285 r1) is off too, whatever its own flag says."""
    monkeypatch.delenv(PAI.ENV, raising=False)
    monkeypatch.delenv(PCN.ENV_RESTS, raising=False)
    assert PAI.enabled()
    monkeypatch.setenv(PCN.ENV_RESTS, "0")
    assert not PAI.enabled()
    monkeypatch.setenv(PCN.ENV_RESTS, "1")
    monkeypatch.setenv(PAI.ENV, "0")
    assert not PAI.enabled()                                                # and its own opt-out still works with rests on


def test_read_page_has_no_private_rest_list_any_more():
    import inspect
    assert "rests" not in inspect.signature(PAI.read_page).parameters
    assert not hasattr(PAI, "REST_PREFIX")


def test_a_read_rest_owns_its_own_ink_and_not_a_stem_beside_it():
    """`_rest_stroke_fits`: a vertical longer than a rest (a neighbouring stem) is refused by the printed shape; a quarter rest's slanted stroke (reads as a short vertical) stays."""
    def st(kind, x, y, w, h):
        return SimpleNamespace(kind=kind, box=(x, y, w, h), length_sp=max(w, h) / SP, thickness_sp=0.2, area_sp2=0.4, angle_deg=90.0 if kind == "vertical" else 0.0,
                               staff_space_local=SP)
    pm = SimpleNamespace(strokes=[st("vertical", 0, 0, 4, 50), st("vertical", 20, 0, 3, 100)], sp=SP)
    assert PCN._rest_stroke_fits(pm, 0, "rest", "restQuarter")              # 2.5 sp: a rest's slanted stroke
    assert not PCN._rest_stroke_fits(pm, 1, "rest", "restQuarter")          # 5 sp: a stem


# ── round 2: a rest's slanted stroke is not a stem's -- answered from what the ink is ATTACHED to ──────────────────────────────────────────────────────────────────────────────────────
def _stroke(kind, box, length, area=0.1, touches=(), thick=0.2):
    return SimpleNamespace(kind=kind, box=box, length_sp=length, thickness_sp=thick, area_sp2=area, angle_deg=90.0, staff_space_local=20.0, touches=list(touches), joined_to=[])


def _pm(strokes):
    return SimpleNamespace(strokes=strokes, sp=20.0, scale=1.0)


def test_a_flag_hangs_from_a_stem_that_carries_a_head_and_a_free_eighth_rest_does_not():
    # tile 7 (Brahms p19): the claim's own ink is a hook (0), the stem (1) touches it and a head blob (2) stands at the stem's end
    flag = _pm([_stroke("curve", (5, 40, 14, 15), 0.9, touches=[(1, 0.4)]),
                _stroke("vertical", (0, 0, 5, 80), 4.0, touches=[(0, 0.4), (2, 1.3)]),
                _stroke("blob", (0, 0, 24, 28), 1.3, area=0.9, thick=0.9, touches=[(1, 1.3)])])
    got = PCN.rest_attachment(flag, [0])
    assert got["stem_with_head"] == [1] and PCN.rest_standing(QUARTER_REST, got) == ("weak", "hangs_from_a_stem_with_a_head")
    # the control that can fail: an eighth rest -- a curl and its own slanted stroke, touching nothing else
    rest = _pm([_stroke("blob", (0, 0, 20, 30), 1.2, area=0.5, touches=[(1, 0.6)]), _stroke("vertical", (6, 15, 3, 45), 1.7, touches=[(0, 0.6)])])
    free = PCN.rest_attachment(rest, [0, 1])
    assert free == dict(stem_with_head=[], touches_a_head=[], bare_stroke=False)
    # ... and its thin run (a slanted stroke over one space) no longer makes it weak by itself: round 1's `stem_like_stroke` is gone where the page strokes are read
    assert PCN.rest_standing(STEM, free) == ("READ", "stands_free") and PCN._contact_standing(STEM)[0] == "weak"


def test_a_stem_with_no_head_a_bare_stroke_and_a_head_touching_the_rest_are_weak_and_missing_evidence_stays_weak():
    stem_only = _pm([_stroke("vertical", (0, 0, 4, 60), 3.0)])
    assert PCN.rest_attachment(stem_only, [0])["bare_stroke"] is True
    assert PCN.rest_standing(QUARTER_REST, PCN.rest_attachment(stem_only, [0])) == ("weak", "bare_vertical_stroke")
    touching = _pm([_stroke("blob", (0, 0, 20, 30), 1.2, area=0.5, touches=[(1, 0.3)]), _stroke("blob", (22, 20, 26, 20), 1.3, area=0.9, thick=0.9, touches=[(0, 0.3)])])
    assert PCN.rest_attachment(touching, [0])["touches_a_head"] == [1]
    free = PCN.rest_attachment(_pm([_stroke("blob", (0, 0, 20, 30), 1.2, area=0.5)]), [0])
    assert PCN.rest_standing(None, free) == ("weak", "no_ink_contact_row")                      # rule 8: no cell measurement is never READ
    assert PCN.rest_standing(STEM_WITH_HEAD, free) == ("weak", "stroke_into_a_head")             # the second witness (the cell raster) still refuses
    assert PCN.rest_attachment(_pm([]), []) is None
