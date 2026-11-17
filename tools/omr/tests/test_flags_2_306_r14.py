"""ROADMAP 2.306 r14 -- THREE FLAG RULES, default ON (Sean 2026-11-16 approved landing them alone) -- controls built from REAL judged marks (rule 7).

1. A note whose stem carries a flag is written flagged, never regrouped at EXPORT under a stroke filed across its x (Sean 2026-10-22, page-facts
   "Beam, flag, slash": "if there is a flag it should be treated as a flag"); a beam another note of the voice is joined to still owns a note whose
   stem stands under it (Sean 2026-10-28, "the beam covers the width of where those notes with stems occur"). Fixture `fixtures/flags_2_306_r14.json`
   (cut by `benchmarks/page-ledger-2026-11/2306/r14_cut_fixture.py` on lane-2.306-r14 from a Brahms p0 gather): Sean's hand labels (data/hand-truth/
   pages/imslp317803/0.json, swept cells) put a FLAG on glyph/0/0/1/6/2, /4, /12 (a slur over them was filed as a cell beam stroke) and on
   glyph/0/0/10/2/5, /7, and BEAMS on cell/0/0/0/3. His r14 tiles 1, 3-7, 12 read the flag rule's notes as flagged eighths.
2. A flag hangs from its own stem's tip to the right: a flag wholly left of a stem is the note before's (Sean's r14 tile 2, "quarter note").
3. A stem carries as many flags as hooks hang from its tip; the detector's class name never adds one (Sean's r14 tile 8, "definitely just an 8th
   note, not a 16th note").
"""
import copy
import json
import os

from tools.omr import export as L
from tools.omr.staged import export as E
from tools.omr.staged.adjudicators.rhythm import flag_hangs_right_of, flag_levels_by_hooks

FX = os.path.join(os.path.dirname(__file__), "fixtures", "flags_2_306_r14.json")


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


def test_flagged_notes_under_a_slur_stroke_stay_flagged():
    old, _ = _run("cell/0/0/1/6", rule=False)
    assert {"glyph/0/0/1/6/4", "glyph/0/0/1/6/12"} <= set(old)          # the control: the old grouping beams Sean's flags
    new, stream = _run("cell/0/0/1/6", rule=True)
    for g in ("glyph/0/0/1/6/2", "glyph/0/0/1/6/4", "glyph/0/0/1/6/12"):
        assert g not in new
    assert all(h["beam_levels"] == 1 for ev in stream for h in ev["noteheads"] if h["glyph"] in ("glyph/0/0/1/6/4", "glyph/0/0/1/6/12"))


def test_flagged_notes_in_a_neighbours_beam_box_stay_flagged():
    old, _ = _run("cell/0/0/10/2", rule=False)
    assert {"glyph/0/0/10/2/5", "glyph/0/0/10/2/7"} & set(old)
    new, _ = _run("cell/0/0/10/2", rule=True)
    assert not ({"glyph/0/0/10/2/5", "glyph/0/0/10/2/7"} & set(new))


def test_never_a_real_beam_seans_beamed_bar_is_grouped_as_before():
    old, _ = _run("cell/0/0/0/3", rule=False)
    new, _ = _run("cell/0/0/0/3", rule=True)
    assert old and new == old
    assert {"glyph/0/0/0/3/3", "glyph/0/0/0/3/4", "glyph/0/0/0/3/5"} <= set(new)


def test_value_from_its_own_flag_needs_every_reading_head_to_agree():
    flag = {"flags_attached": 1, "beams_by_stem": 0, "levels_certain": 0}
    beam = {"flags_attached": 0, "beams_by_stem": 1, "levels_certain": 1}
    assert E._value_from_its_own_flag([flag])
    assert not E._value_from_its_own_flag([flag, beam])
    assert not E._value_from_its_own_flag([beam])
    assert not E._value_from_its_own_flag([None, {}])


def test_tile2_the_flag_of_the_note_before_is_not_this_stems():
    # Sean's r14 tile 2 (Brahms p0 glyph/0/0/9/3/5, his label q1011): "quarter note". The detector's flag box glyph/0/0/9/3/37 (flag8thDown)
    # hangs right of the stem of the note before (glyph/0/0/9/3/2, his tile 1: "an eighth note ... it does have a flag"). Page px, 2026-11-16 gather.
    flag = (3268.06, 5127.99, 3297.73 - 3268.06, 5220.23 - 5127.99)
    assert not flag_hangs_right_of((3322.0, 5000.0, 8.0, 234.0), flag)     # never this stem's
    assert flag_hangs_right_of((3254.0, 5000.0, 6.0, 234.0), flag)         # the note before keeps its own flag


def test_hooks_the_class_never_adds_a_flag():
    # Real readings, 2026-11-16 gathers: the detector's class `flag16thUp` / `flag16thDown` (two levels) against the stem tip's own count of ONE
    # hook. Sean's r14 tile 8 (Litolff p10 glyph/10/0/9/0/2): "definitely just an 8th note". Also Litolff p10 glyph/10/1/9/0/2 and Brahms p0
    # glyph/0/0/11/6/14 (our look: one flag each).
    for counted in (1,):
        assert flag_levels_by_hooks(2, counted) == 1


def test_hooks_never_raise_and_no_count_changes_nothing():
    # The boundary: the tip reader saw no hook or could not count (None) -> today's reading, the class's level. Brahms p4 glyph/4/1/13/8/1 is a real
    # case where the tip counted 2 on an EIGHTH (a slur starting at the tip, our look) with no flag box: the rule never raises a level.
    assert flag_levels_by_hooks(2, None) == 2
    assert flag_levels_by_hooks(1, 2) == 1
    assert flag_levels_by_hooks(2, 2) == 2          # a 16th whose tip shows two hooks stays a 16th
    assert flag_levels_by_hooks(2, 0) == 2          # "no hook" is not a count of hooks: never zero flags from here
