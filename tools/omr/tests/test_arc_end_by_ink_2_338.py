"""ROADMAP 2.338: an arc belongs to the note its ink reaches (`OMR_ARC_END_BY_INK`, default OFF). STAGED ADJUDICATE. Controls built from REAL recorded rows:
the binder inputs `ownership._page_binding` handed `page_arc_bind.closest_binder` on the 20261122-night lane-report slices (main a1c3fd5b0, re-adjudicated,
reproducing the overnight's page-arc verdicts exactly), copied unchanged into `data/arc_end_by_ink_2_338.json` -- never a drawing.

  YES  Sean's 2.305 r8 tile 10 (Brahms p0 run 76, "correct", a complete real arc): the left end stands over the chord's top head, which the reader refused
       (`tremolo_slash_crosses_stem`); the read member below it is 2.02 spaces from the end's height by box centre -> OFF refuses (2.017 vs 2.0), ON binds
       the chord (its read member).
  YES  six slurs ending at a STEM (Brahms p0 runs 15, 38, 41, 43, 60, 75; crop-looked: each ends at the stem of the note it is bound to) -> OFF refuses
       `end_far_beyond_head`, ON binds the same note.
  YES  chord-member / two-notes cases settled by ink (`CHORD_TIES`): exactly one note's ink reached -> that note.
  SAME every end the OFF binder bound (written runs of Brahms p0) is bound exactly as before with the flag ON.
  NEVER ends at a barline the tracker stopped at (Litolff p2 runs 6, 10; p10 run 23) and an end at another staff's stem (Litolff p16 run 61) stay
       unbound ON.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from tools.omr.staged import page_arc_bind as PB

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "arc_end_by_ink_2_338.json").read_text())
CASES = {c["label"]: c for c in DATA}


def _bind(case, on, monkeypatch):
    monkeypatch.setenv(PB.ENV_END_BY_INK, "1" if on else "0")
    monkeypatch.setenv(PB.ENV_WRITE, "1")
    usable = {h["key"]: h["usable"] for h in case["heads"]}
    heads = [{k: v for k, v in h.items() if k != "usable"} for h in case["heads"]]
    others = {k: [tuple(p) for p in v] for k, v in (case["others"] or {}).items()}
    binder = PB.closest_binder(others, {})
    return binder(heads, case["sp"], lambda k: usable.get(k, False), case["end_pitch"], None, case["d"], case["unread"])


def _labels(prefix):
    return sorted(k for k in CASES if k.startswith(prefix))


@pytest.mark.parametrize("label", ["run76:left"])
def test_seans_run_76_binds_the_chord(label, monkeypatch):
    case = CASES[label]
    side = label.split(":")[1]
    off = _bind(case, False, monkeypatch)
    assert off[side].get("unbound") == "end_far_beyond_head"          # the control fails before the change
    on = _bind(case, True, monkeypatch)
    assert on[side].get("head") == "glyph/0/0/1/6/3" and on[side].get("by_ink") and on[side].get("reached") == "unread_member"
    assert on[side].get("reached_member") == "glyph/0/0/1/6/1"


@pytest.mark.parametrize("label", _labels("stem:"))
def test_slur_ending_at_a_stem_binds_that_note(label, monkeypatch):
    case = CASES[label]
    side = label.split(":")[-1]
    off = _bind(case, False, monkeypatch)
    assert off[side].get("unbound") == "end_far_beyond_head"
    on = _bind(case, True, monkeypatch)
    assert on[side].get("head") == case["want"] and on[side].get("reached") == "stem"


@pytest.mark.parametrize("label", _labels("chord:"))
def test_one_note_reached_settles_the_end(label, monkeypatch):
    case = CASES[label]
    side = label.split(":")[-1]
    off = _bind(case, False, monkeypatch)
    assert off[side].get("unbound") in ("two_columns_at_end", "end_far_beyond_head", "unread_ink_at_end")
    on = _bind(case, True, monkeypatch)
    assert on[side].get("head") == case["want"] and on[side].get("by_ink")


@pytest.mark.parametrize("label", _labels("same:"))
def test_a_bound_end_is_never_moved(label, monkeypatch):
    case = CASES[label]
    off, on = _bind(case, False, monkeypatch), _bind(case, True, monkeypatch)
    for side in ("left", "right"):
        assert off[side] == case["recorded"][side]                     # the rows reproduce the recorded binding
        assert on[side] == off[side]


@pytest.mark.parametrize("label", _labels("never:"))
def test_end_over_blank_paper_or_beside_another_staff_stays_unbound(label, monkeypatch):
    case = CASES[label]
    side = label.split(":")[-1]
    on = _bind(case, True, monkeypatch)
    assert on[side].get("head") is None and on[side].get("unbound")


def test_ink_reach_measures_the_stem_not_the_box_centre(monkeypatch):
    case = CASES["stem:0:38:right"]
    d = case["d"]
    r = PB.ink_reach(case["want"], case["heads"], PB._end_points(d, "right"), case["sp"])
    assert r[1] == "stem" and r[0] <= PB.INK_REACH_SPACES
