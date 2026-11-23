"""ROADMAP 2.333 -- a dropped head must not hide (flag OMR_DROPPED_HEAD_MARKS, OFF). STAGED EXPORT.

Controls built from the REAL re-adjudicated frozen-sample records (2026-11-21 gathers, re-adjudicated on lane-2.333):
`data/dropped_head_2_333.json` holds, per named bar, every detector box of that bar and of its neighbourhood on the page (the
neighbouring staves' twins) with the exporter's own fate for each. Each marking control FAILS with the flag off (nothing filed).
  * Litolff viola p6 (6/1/9/11): the upper head dropped (no stem joined -> value narrowed), the half alone fills the bar.
  * Sean's Beethoven 5 first violins bar 21 (Litolff 2/0/7/4): the string chord, every member `chord_value_undecided`.
  * Brahms cello p4 (4/1/12/8): the F2 eighth dropped (`flag_ink_unread` -> narrowed); the chord written a quarter cancels it.
  * Brahms p12 (12/0/6/6): a head refused `owned_by_another_staff`, nothing written on its ink on either staff.
Never side: a plain bar whose only unwritten boxes are slivers (Litolff 6/1/10/1, a stem/beam junction boxed too narrow), and a
box refused `owned_by_another_staff` whose twin IS written on the owning staff (Litolff 6/0/4/10).
"""
import json
import pathlib
import re

import pytest

from tools.omr.staged import export as E
from tools.omr.staged.record import Q

FIX = json.loads((pathlib.Path(__file__).parent / "data" / "dropped_head_2_333.json").read_text())
CK = re.compile(r"glyph/(\d+)/(\d+)/(\d+)/(\d+)/\d+$")


class _Rec:
    """The two record reads `_file_dropped_heads` makes, over the fixture's real rows. A box is a head when the detector
    classed it a notehead (the record files `Q.NOTEHEAD_CLASS` for exactly those)."""

    def __init__(self, rows):
        self.rows = rows
        self.__dict__["_x"] = None

    def obs_of(self, q):
        assert q == Q.GLYPH_BOX
        return [{"subject": r["subject"], "value": r["value"], "detail": {"bbox_page_px": r["bbox_page_px"]}} for r in self.rows]

    def obs(self, q, sub):
        r = next((r for r in self.rows if r["subject"] == sub), None)
        if r is None:
            return []
        if q == Q.NOTEHEAD_CLASS:
            return [1] if r["cls"].startswith("notehead") else []
        if q == Q.REST:
            return [1] if r["cls"].startswith("rest") else []
        return []


class _Run:
    def __init__(self):
        self.cells = {}


def _file(name, monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv(E.DROPPED_HEAD_MARKS_ENV, raising=False)
    else:
        monkeypatch.setenv(E.DROPPED_HEAD_MARKS_ENV, mode)
    case = FIX[name]
    runs = {}
    for r in case["boxes"]:
        m = CK.match(r["subject"])
        pg, sy, st, c = (int(x) for x in m.groups())
        run = runs.setdefault(E._staff_key(pg, sy, st), _Run())
        run.cells.setdefault(c, E.Cell(pg, sy, st, c))
    counts = E._file_dropped_heads(_Rec(case["boxes"]), runs, {k: v for k, v in case["fates"].items() if v})
    pg, sy, st, c = case["cell"]
    return runs[E._staff_key(pg, sy, st)].cells[c].dropped_heads, counts


MARKED = ["litolff_viola", "beethoven_vln1_bar21", "brahms_cello_f2", "brahms_owned_nothing_written"]


@pytest.mark.parametrize("name", MARKED)
def test_a_dropped_head_that_may_be_a_note_is_filed_on_its_bar(name, monkeypatch):
    got, _ = _file(name, monkeypatch, "bar")
    assert got, "%s: no dropped head filed" % name
    for d in got:
        assert d["reason"] not in E._DROPPED_HEAD_SCRAPS


@pytest.mark.parametrize("name", MARKED)
def test_flag_off_files_nothing(name, monkeypatch):
    got, counts = _file(name, monkeypatch, None)
    assert got == [] and counts == {}


def test_never_a_bar_whose_only_unwritten_boxes_are_slivers(monkeypatch):
    got, _ = _file("litolff_only_scraps", monkeypatch, "bar")
    assert got == []
    case = FIX["litolff_only_scraps"]
    pre = "glyph/%d/%d/%d/%d/" % tuple(case["cell"])
    fates = {v for k, v in case["fates"].items() if k.startswith(pre) and v not in ("written", None)}
    assert "not_a_notehead:too_narrow" in fates       # the control holds what it guards against


def test_never_a_copy_whose_twin_is_written_on_the_owning_staff(monkeypatch):
    got, counts = _file("litolff_owned_written_twin", monkeypatch, "bar")
    assert all(d["reason"] != "owned_by_another_staff" for d in got)
    assert counts.get("a_written_note_on_its_ink", 0) >= 1


def test_the_bar_words_name_the_dropped_head():
    w = E._dropped_head_words([{"reason": "duration_narrowed"}, {"reason": "chord_value_undecided"}, {"reason": "duration_abstained"}])
    assert w == "a note not written: value not read, chord value not read"


def test_the_spot_is_red_words_at_the_heads_onset_and_nothing_else():
    head = {"x": 300.0, "w": 30.0}
    stream = [{"kind": "chord", "x_position": 100.0, "duration_beats": 1.0, "noteheads": [{"duration_beats": 1.0}]},
              {"kind": "chord", "x_position": 200.0, "duration_beats": 1.0, "noteheads": [{"duration_beats": 1.0}]},
              {"kind": "chord", "x_position": 300.0, "duration_beats": 1.0, "noteheads": [{"duration_beats": 1.0}]}]
    units = E._dropped_head_onset(head, [stream], 4)
    assert units == sum(E._event_units(e, 4) for e in stream[:2])
    xml = E._dropped_head_spot_xml(units)
    assert E.UNREAD_BAR_MARK_COLOR in xml and E.DROPPED_HEAD_SPOT_WORD in xml
    assert "<note" not in xml and "<rest" not in xml and "<forward" not in xml


def test_mode_is_an_allow_list(monkeypatch):
    for v, want in (("bar", "bar"), ("spot", "spot"), ("1", "off"), ("on", "off"), ("", "off")):
        monkeypatch.setenv(E.DROPPED_HEAD_MARKS_ENV, v)
        assert E.dropped_head_marks_mode() == want
