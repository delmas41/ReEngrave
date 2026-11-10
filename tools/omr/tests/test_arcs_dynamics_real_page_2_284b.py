"""ROADMAP 2.284b -- the two new claims on REAL pages (flag `OMR_PAGE_LEDGER_OWNS`). Slow: reads the lane's fresh gathers (Litolff p2 arcs, p10 dynamics)
kept machine-local in `library/_shared-records/2.284b/` (Litolff p2 and p10; the lane report's work records, copied), and re-runs the stroke owner on their GATHER rows.

Each test also runs on the OFF arm's gather, where it must FAIL (the control that can fail, CLAUDE rule 7)."""
from __future__ import annotations

import pathlib

import pytest

pytestmark = pytest.mark.slow

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECS = LIB / "_shared-records" / "2.284b"


def _rec(name: str) -> pathlib.Path:
    p = RECS / name
    if not p.exists():
        pytest.skip("lane gather not on this machine: %s" % p)
    return p


def _rows(name: str, page: int):
    from tools.omr.staged import claim_readout as CR
    return CR.read_rows(CR.cut_record(_rec(name)), [page])


def _arc_held(rows, flag: str):
    from tools.omr.staged import claim_readout as CR
    out = {}
    for _ck, d in CR.owner_verdicts(rows, {"OMR_PAGE_LEDGER_OWNS": flag}).items():
        for key, e in ((d.get("claim_final") or {}).get("held") or {}).items():
            if e.get("by") in ("arc_trace", "arc") and "/" in key and e["share"] >= 0.5:
                out[key] = e["share"]
    return out


def test_no_mark_box_is_held_by_an_arc_and_the_arc_keeps_its_own_ink():
    on = _rows("2284b-litolff.on.gathered.record.json", 2)
    assert _arc_held(on, "1") == {}
    arcs = [o for o in on["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") == "arc"
            and (o.get("detail") or {}).get("unit") == "ink"]
    own = sum(int(((o["detail"].get("pixels") or {}).get("own_px") or 0)) for o in arcs)
    assert arcs and own > 0
    # the control that can fail: the OFF gather (no pixel rule) still holds mark boxes by an arc (r4: 3 on this page)
    off = _rows("2284b-litolff.off.gathered.record.json", 2)
    assert len(_arc_held(off, "1")) >= 1


def test_dynamic_letters_inside_the_staff_claim_their_ink_page_wide():
    on = _rows("2284b-litolff.on.gathered.record.json", 10)

    def inside(rows):
        return [o for o in rows["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") == "word"
                and (o.get("detail") or {}).get("source") == "dynamic_letters" and (o.get("detail") or {}).get("inside_staff")
                and (o.get("detail") or {}).get("standing", "READ") == "READ"]
    got = inside(on)
    assert len(got) >= 3, len(got)
    # and no claim took a note mark it overlaps: every claimed rectangle is clear of the spared note boxes it lists
    for o in got:
        a = o["value"]
        for b in o["detail"].get("marks_left_out") or ():
            assert not (a[0] >= b[0] and a[2] <= b[2] and a[1] >= b[1] and a[3] <= b[3])
    # the control that can fail: the OFF gather files none
    assert inside(_rows("2284b-litolff.off.gathered.record.json", 10)) == []


# ---- r2 (Sean 2026-11-10): a printed dynamic is one mark; a ledger box on the arc's own ink is the arc's ----------------------------------------

def _claims(name: str, page: int):
    rows = _rows(name, page)
    return [o for o in rows["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("source") == "dynamic_letters"
            and (o.get("detail") or {}).get("inside_staff")]


def test_in_staff_ff_is_claimed_as_one_word_not_letter_by_letter():
    on = _claims("2284b-r2-litolff.on.gathered.record.json", 10)
    ff = [o for o in on if o["detail"].get("text") == "ff"]
    assert len(ff) >= 3
    # Sean's tile 4 (p10 box 1736,2571 - 1786,2614): one claim holds both letters
    assert any(o["value"][0] <= 1740 and o["value"][2] >= 1782 and o["value"][1] <= 2575 for o in ff)
    # the control that can fail: the r6 gather claimed that ink as two lone f
    old = _claims("2284b-litolff.on.gathered.record.json", 10)
    assert [o for o in old if o["detail"].get("text") == "ff"] == []


def test_the_ledger_box_on_the_arcs_own_ink_is_no_crossing():
    def lines_and_cross(name):
        rows = _rows(name, 4)
        lb, cr = [], []
        for o in rows["observations"]:
            d = o.get("detail") or {}
            if o["quantity"] == "claimed_area" and d.get("owner") == "arc":
                lb += [c[1] for c in d.get("line_boxes") or []]
                cr += [c[3] for c in d.get("crossings") or []]
        return lb, cr
    lb, cr = lines_and_cross("2284b-r2-litolff.on.gathered.record.json")
    assert "glyph/4/0/7/1/10" in lb and "glyph/4/0/7/1/10" not in cr
    _lb, cr_old = lines_and_cross("2284b-litolff.on.gathered.record.json")
    assert "glyph/4/0/7/1/10" in cr_old                # r6: kept as a crossing
