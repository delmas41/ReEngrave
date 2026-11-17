"""ROADMAP 2.306 r14 (flag `OMR_PAGE_STEMS`, default OFF) -- controls built from REAL judged marks (CLAUDE rule 7).

1. A note whose stem carries a flag is written flagged, never beamed (Sean 2026-10-22, page-facts "Beam, flag, slash": "if there is a flag it
   should be treated as a flag"). Fixture `fixtures/page_stems_2_306_r14_flags.json`: the beam-grouping input EXPORT builds on Brahms p0 (cut by
   `benchmarks/page-ledger-2026-11/2306/r14_cut_fixture.py` from a gather of today's branch). Sean's hand labels (data/hand-truth/pages/
   imslp317803/0.json, swept cells) put a FLAG on q264 / q266 / q272 (glyph/0/0/1/6/2, /4, /12: a slur over them was filed as a cell beam
   stroke) and q1178 / q1180 (glyph/0/0/10/2/5, /7), and BEAMS on q67-q75 (cell/0/0/0/3). The old grouping beams the flagged ones (the
   control fails there first); the rule keeps them flagged and groups the beamed bar exactly as before (the never).
2. An accidental's strokes end where the accidental ends: a vertical running out of the detector's accidental box is a stem, never held by it.
"""
import copy
import json
import os
from types import SimpleNamespace

from tools.omr import export as L
from tools.omr.staged import export as E
from tools.omr.staged import page_stems as PS

FX = os.path.join(os.path.dirname(__file__), "fixtures", "page_stems_2_306_r14_flags.json")


def _cell(key):
    with open(FX) as f:
        return json.load(f)[key][0]


def _beamed(stream):
    return {h["glyph"]: ev.get("beam_states") for ev in stream for h in ev["noteheads"] if ev.get("beam_states")}


def _run(key, rule):
    c = copy.deepcopy(_cell(key))
    stream = c["events"]
    if rule:
        details = [[h["duration_detail"] for h in ev["noteheads"]] for ev in stream]
        flagged = E.flagged_outside_a_joined_beam(stream, c["dets"], details)
        E.beam_stream_keeping_flags(stream, c["dets"], flagged)
    else:
        L.annotate_beams(stream, c["dets"])
    return _beamed(stream), stream


def test_r14_flagged_notes_under_a_slur_stroke_stay_flagged():
    old, _ = _run("cell/0/0/1/6", rule=False)
    assert {"glyph/0/0/1/6/4", "glyph/0/0/1/6/12"} <= set(old)          # the control: the old grouping beams Sean's flags
    new, stream = _run("cell/0/0/1/6", rule=True)
    for g in ("glyph/0/0/1/6/2", "glyph/0/0/1/6/4", "glyph/0/0/1/6/12"):
        assert g not in new
    # the level is given back: the note is still written as an eighth (with its flag)
    assert all(h["beam_levels"] == 1 for ev in stream for h in ev["noteheads"] if h["glyph"] in ("glyph/0/0/1/6/4", "glyph/0/0/1/6/12"))


def test_r14_flagged_notes_in_a_neighbours_beam_box_stay_flagged():
    old, _ = _run("cell/0/0/10/2", rule=False)
    assert {"glyph/0/0/10/2/5", "glyph/0/0/10/2/7"} & set(old)
    new, _ = _run("cell/0/0/10/2", rule=True)
    assert not ({"glyph/0/0/10/2/5", "glyph/0/0/10/2/7"} & set(new))


def test_r14_never_a_real_beam_seans_beamed_bar_is_grouped_as_before():
    old, _ = _run("cell/0/0/0/3", rule=False)
    new, _ = _run("cell/0/0/0/3", rule=True)
    assert old and new == old
    assert {"glyph/0/0/0/3/3", "glyph/0/0/0/3/4", "glyph/0/0/0/3/5"} <= set(new)


def test_r14_value_from_its_own_flag_needs_every_reading_head_to_agree():
    flag = {"flags_attached": 1, "beams_by_stem": 0, "levels_certain": 0}
    beam = {"flags_attached": 0, "beams_by_stem": 1, "levels_certain": 1}
    assert E._value_from_its_own_flag([flag])
    assert not E._value_from_its_own_flag([flag, beam])       # one head with a beam joined: the stem is beamed
    assert not E._value_from_its_own_flag([beam])
    assert not E._value_from_its_own_flag([None, {}])           # no reading: nothing changes


def test_r14_a_stem_running_out_of_the_accidental_box_is_not_held():
    # REAL marks, Brahms p0 (gather of 2026-11-16, page map stroke 1371; NOT judged by Sean -- the cell s0-st12-m1 is not swept; our look: an
    # eighth whose down stem and flag the detector boxed as `accidentalFlat` 0.35, glyph/0/0/12/1/13). The stem runs out of the box at both ends.
    acc = (2333.76, 6417.28, 2374.08, 6513.92)
    stem = SimpleNamespace(kind="vertical", box=(2334.0, 6394.0, 6.0, 136.0))
    assert PS.stem_runs_out_of_the_accidental(stem, acc, 32.0)
    # the never: a vertical lying inside the box (a flat's own upright) stays the accidental's; a curve is never freed
    assert not PS.stem_runs_out_of_the_accidental(SimpleNamespace(kind="vertical", box=(2336.0, 6420.0, 6.0, 90.0)), acc, 32.0)
    assert not PS.stem_runs_out_of_the_accidental(SimpleNamespace(kind="curve", box=(2334.0, 6394.0, 30.0, 136.0)), acc, 32.0)
