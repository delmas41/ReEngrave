"""ROADMAP 2.354 -- a read note is never dropped without a mark (STAGED EXPORT, `OMR_LATE_INK_DROP_MARKED`, default OFF).

The rule as a musician says it: the box says where to look; the ink says whether a head is there. A note read with its value and pitch
that EXPORT then refuses on a late look at its ink is MARKED where it stood (2.333's "unread note" spot), never dropped in silence.
Never: write the head, invent anything, touch a written note, or mark a box whose ink a written note or rest already holds.

WHY A MARK AND NOT A SILENT "NOT A NOTE" (step 0, 20261123-night records): the five late tests -- `relocation_not_a_head_by_ink`
(`Q.HEAD_INK` not one head), `relocation_on_another_mark` (box centre inside another mark's box), and the whole-rest verdict's
`ink_is_a_whole_rest` / `ink_straddles_a_stem` / `ink_not_head_shaped` -- are not proof. On the 625 heads Sean vouched for (judged
tiles, his Brahms p0 hand labels, the 2.306-r24 heads) "HEAD_INK not one head" holds on 86 and "centre inside another mark's box" on 14.

Every case is the record's own rows for the boxes around the mark (fixture `data/late_ink_drop_2_354.json`, cut by lane 2.354's
`mkfix.py` from the 20261123-night record with the branch exporter's own fates, flag off). What the four marked boxes ARE is our look at
the crops (three are not notes, one a whole rest written nowhere): the flag marks a place to look, it never says what is there. Each
marked case FAILS with the flag off (nothing filed). The never side holds Sean's judged marks: three real heads under a wrong claim, the
broken-stem head, his four non-heads that are written today, a black head, a hollow head on a line and a head on ledger lines.
"""
import json
import pathlib
import re

import pytest

from tools.omr.staged import export as E
from tools.omr.staged.record import Q

FIX = json.loads((pathlib.Path(__file__).parent / "data" / "late_ink_drop_2_354.json").read_text())
CK = re.compile(r"glyph/(\d+)/(\d+)/(\d+)/(\d+)/\d+$")


class _Rec:
    """The record reads `_file_dropped_heads` makes, over the fixture's real rows (a head is a box the detector classed a notehead:
    the record files `Q.NOTEHEAD_CLASS` for exactly those)."""

    def __init__(self, rows):
        self.rows = {r["subject"]: r for r in rows}

    def obs_of(self, q):
        assert q == Q.GLYPH_BOX
        return [{"subject": r["subject"], "value": r["value"], "detail": {"bbox_page_px": r["bbox_page_px"]}} for r in self.rows.values()]

    def obs(self, q, sub):
        r = self.rows.get(sub)
        if r is None:
            return []
        if q == Q.NOTEHEAD_CLASS:
            return [1] if str(r["cls"]).startswith("notehead") else []
        if q == Q.REST:
            return [1] if str(r["cls"]).startswith("rest") else []
        return []

    def verdict(self, q, sub):
        r = self.rows.get(sub) or {}
        return {Q.DURATION: r.get("duration"), Q.PITCH: r.get("pitch")}.get(q)


class _Run:
    def __init__(self):
        self.cells = {}


def _file(name, monkeypatch, on):
    monkeypatch.delenv(E.DROPPED_HEAD_MARKS_ENV, raising=False)          # 2.333's default: spot
    monkeypatch.delenv(E.INSIDE_VIEW_DROP_MARKED_ENV, raising=False)
    if on:
        monkeypatch.setenv(E.LATE_INK_DROP_MARKED_ENV, "1")
    else:
        monkeypatch.delenv(E.LATE_INK_DROP_MARKED_ENV, raising=False)
    case = FIX[name]
    runs = {}
    for r in case["boxes"]:
        pg, sy, st, c = (int(x) for x in CK.match(r["subject"]).groups())
        runs.setdefault(E._staff_key(pg, sy, st), _Run()).cells.setdefault(c, E.Cell(pg, sy, st, c))
    counts = E._file_dropped_heads(_Rec(case["boxes"]), runs, {r["subject"]: r["fate"] for r in case["boxes"] if r["fate"]})
    filed = [d for run in runs.values() for cell in run.cells.values() for d in cell.dropped_heads]
    return case, filed, counts


MARKED = ["brahms_clef_tail", "brahms_flag", "brahms_tremolo", "litolff_whole_rest"]
NEVER_WRITTEN = ["sean_broken_stem_head", "sean_head_under_clef_claim", "sean_head_under_barline_claim",
                 "sean_head_under_whole_rest_claim", "sean_not_head_tremolo", "sean_not_head_sharp_b", "sean_not_head_sharp_l",
                 "sean_not_head_clef_ring", "hand_black_head", "judged_hollow_on_line", "judged_ledger_head"]


def test_off_by_default(monkeypatch):
    monkeypatch.delenv(E.LATE_INK_DROP_MARKED_ENV, raising=False)
    assert not E.late_ink_drop_marked_enabled()
    for r in ("relocation_not_a_head_by_ink", "relocation_on_another_mark"):
        assert not E._dropped_head_may_be_a_note(r)


@pytest.mark.parametrize("name", MARKED)
def test_a_read_note_refused_late_is_marked_where_it_stood(name, monkeypatch):
    case, filed, _ = _file(name, monkeypatch, on=True)
    me = [d for d in filed if d["sub"] == case["target"]]
    assert me, "%s: the read note %s was dropped with no mark" % (name, case["target"])
    assert me[0]["reason"] in E._LATE_INK_REFUSALS


@pytest.mark.parametrize("name", MARKED)
def test_off_the_late_drop_is_silent(name, monkeypatch):
    # the control fails on the base: the same note, flag off, is filed nowhere
    case, filed, _ = _file(name, monkeypatch, on=False)
    assert not [d for d in filed if d["sub"] == case["target"]]


@pytest.mark.parametrize("name", MARKED)
def test_the_control_holds_a_read_note(name):
    case = FIX[name]
    t = next(r for r in case["boxes"] if r["subject"] == case["target"])
    assert t["fate"] in E._LATE_INK_REFUSALS
    assert t["duration"]["outcome"] == "decided" and isinstance(t["duration"]["value"], dict)
    assert t["pitch"]["outcome"] == "decided"


@pytest.mark.parametrize("name", NEVER_WRITTEN)
def test_never_touches_a_written_note(name, monkeypatch):
    case, filed_on, _ = _file(name, monkeypatch, on=True)
    t = next(r for r in case["boxes"] if r["subject"] == case["target"])
    assert t["fate"] in ("written", "written_relocated"), "%s: the control must hold a written note" % name
    assert not [d for d in filed_on if d["sub"] == case["target"]]
    _c, filed_off, _ = _file(name, monkeypatch, on=False)
    # the flag adds marks only for late-ink refusals, nowhere else in the bar
    extra = {d["sub"] for d in filed_on} - {d["sub"] for d in filed_off}
    assert all(next(r for r in case["boxes"] if r["subject"] == s)["fate"] in E._LATE_INK_REFUSALS for s in extra)


def test_never_a_box_whose_ink_a_written_note_holds(monkeypatch):
    case, filed, counts = _file("never_written_note_on_its_ink", monkeypatch, on=True)
    assert next(r for r in case["boxes"] if r["subject"] == case["target"])["fate"] in E._LATE_INK_REFUSALS
    assert not [d for d in filed if d["sub"] == case["target"]]
    assert counts.get("a_written_note_on_its_ink", 0) >= 1


def test_never_a_box_whose_value_was_not_read(monkeypatch):
    case, filed, counts = _file("never_value_not_read", monkeypatch, on=True)
    assert next(r for r in case["boxes"] if r["subject"] == case["target"])["fate"] in E._LATE_INK_REFUSALS
    assert not [d for d in filed if d["sub"] == case["target"]]
    assert counts.get("late_ink_not_a_read_note", 0) >= 1


def test_the_refusals_stay_refusals_and_the_bar_is_not_a_gap():
    # the flag marks the spot only; the two relocation refusals stay out of the bar's unread gap, nothing is written
    for r in ("relocation_not_a_head_by_ink", "relocation_on_another_mark"):
        assert r in E._NOT_A_GAP_REASONS
    for r in E._LATE_INK_REFUSALS:
        assert r in E._DROPPED_HEAD_REASON_WORDS
        assert "not a note" not in E._DROPPED_HEAD_REASON_WORDS[r]


def test_other_refusals_do_not_move(monkeypatch):
    monkeypatch.setenv(E.LATE_INK_DROP_MARKED_ENV, "1")
    monkeypatch.delenv(E.INSIDE_VIEW_DROP_MARKED_ENV, raising=False)
    for r in ("mark_group_duplicate", "not_a_notehead:claimed_by:word", "not_a_notehead:too_narrow", "not_a_notehead:clipped_fragment",
              "relocation_inside_owner_view"):
        assert not E._dropped_head_may_be_a_note(r), r
