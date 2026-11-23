"""ROADMAP 2.324 r10 -- a C clef names the staff line through the middle of the clef, measured from its top and bottom edges, STAGED
GATHER (`clef_pagewide.c_outside_edges` / `name_c_bar`).

Sean 2026-11-22, shown the two small Litolff C clefs printed off their line (page 4 system 1 staff 3 bar 3; page 11 system 0 staff 2
bar 15; tiles `out/print/2.324-r9/`): "They all look like tenor clefs"; "Needs to be read - never assumed"; "The best bet at
determining what clef it is is measuring the middle of the clef and aligning it with a staff line"; "Mesure from the outside to get
the midddle". So the line is read from the clef's own outer edges -- never from where its ink balances, the instrument, or another
clef on the staff.

`data_clef_c_middle_2_324_r10.npz`: every C clef that passes the bar-and-bowls test on the 16 frozen-sample pages (Litolff and
Breitkopf, 61), cut from the pipeline's own page binary with the lines the page-wide pass hands it; `read_before` is the balance
reading (main before r10), `read_after` this round's. Each cut reproduced its page's two readings when it was made.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import clef_pagewide as CP

DATA = pathlib.Path(__file__).with_name("data_clef_c_middle_2_324_r10.npz")
_Z = np.load(DATA)
META = json.loads(str(_Z["meta"]))
B15 = "c_litolff_p11_s0_st2_b15_body"     # Sean: tenor
B3 = "c_litolff_p4_s1_st3_b3_body"        # Sean: tenor
READ_BEFORE = sorted(k for k, m in META.items() if m["read_before"] is not None)


def _cand(name):
    m = META[name]
    ink = np.unpackbits(_Z[name])[: m["shape"][0] * m["shape"][1]].reshape(m["shape"]).astype(bool)
    got = [c for c in CP.c_bars(ink, m["lines"], m["sp"], m["scan"][0], m["scan"][1]) if c["passed"]]
    assert got, name
    return got[0], m


def _name(name):
    cand, m = _cand(name)
    return CP.name_c_bar(cand, m["lines"])


def test_the_cut_holds_every_c_clef_of_the_frozen_sample():
    assert len(META) == 61 and len(READ_BEFORE) == 59
    assert all(m["reproduces"] for m in META.values())


def test_sean_s_bar_15_clef_is_read_tenor_from_its_outside_middle():
    nm, ln, res = _name(B15)
    assert (nm, ln) == ("tenor", 4) and res < 0.3


def test_control_where_its_ink_balances_cannot_read_it():
    """The reading before r10 (the glyph's balance, snapped) fails on the same mark: it balances half a space off the line."""
    cand, m = _cand(B15)
    nm, _, res = CP.name_c(cand["middle_y"], cand.get("lines_local") or m["lines"])
    assert nm is None and res > 0.35


def test_sean_s_bar_3_clef_stays_unread_its_middle_is_past_the_snap():
    """OPEN (Sean: tenor). Its outside middle stands 0.41 space above the tenor line and 0.60 below the top line -- nearest the tenor
    line but past the header readers' snap (0.35): unread, never another clef."""
    nm, ln, res = _name(B3)
    assert nm is None and 0.35 < res < 0.5


@pytest.mark.parametrize("name", READ_BEFORE)
def test_every_c_clef_read_before_keeps_its_kind(name):
    assert _name(name)[0] == META[name]["read_before"]


def test_control_reaching_past_the_bar_takes_in_other_marks(monkeypatch):
    """Let the clef's piece reach a full space past its bar and a stem, slur or line below joins in: clefs are named wrong or lost --
    the reach can fail."""
    monkeypatch.setattr(CP, "C_OUTSIDE_REACH_SPACES", 1.0)
    changed = [n for n in READ_BEFORE if _name(n)[0] != META[n]["read_before"]]
    assert len(changed) >= 3


@pytest.mark.parametrize("attr,value,lost", [
    ("C_STROKE_PAST_SPACES", 99.0, ["c_litolff_p4_s1_st3_b12_body", "c_litolff_p11_s0_st2_b0_body"]),
    ("C_STROKE_TRIM_SPACES", 0.0, ["c_litolff_p11_s0_st2_b0_body"]),
])
def test_control_a_stroke_touching_the_clef_is_not_the_clef(monkeypatch, attr, value, lost):
    """A stem or barline touching the bowls (Litolff p4 bar 12, p11 bar 0, both read tenor): counted as the clef's ink -- or measured
    from its ragged edge -- it pulls the clef's edge off and the read tenor clef is lost."""
    monkeypatch.setattr(CP, attr, value)
    for n in lost:
        assert _name(n)[0] is None


def test_no_outside_edges_is_unread_never_the_balance():
    cand, m = _cand(B15)
    assert CP.name_c_bar(dict(cand, outside_middle=None), m["lines"])[0] is None
