"""ROADMAP 2.365 -- a beam's ink is not held by another mark's claim (flag `OMR_BEAM_INK_NOT_HELD`, default OFF). STAGED ADJUDICATE.

Controls from REAL judged pixels (CLAUDE rule 7): the GATHER rows of the cells that hold the 14 claimed strokes of the 20261127-night records
(`data/beam_ink_2_365.json.gz`, cut by the lane; the staves above and below are kept, since a padded cell sees them), re-run through the stroke
owner (`claim_readout.owner_verdicts`) and the one beam count (`beam_strokes.beam_count`) with the flag OFF and ON.

Sean's answers (`out/print/tip-ink/answers_24.json`, 2026-11-27; and the 9 judged earlier on `out/print/step0-notes/`, all real eighths):
  * "a beam": tiles 3-8, 11, 14, 17, 20-22 and the judged eighths on the same strokes -> ON the beam is free and the count reads ONE beam;
    OFF it is held and the count is narrowed `claimed_ink_at_tip` (each control fails against the old behaviour).
  * "a staff line" (1, 10, 18), "a D from diminished" (2, 12), "an F from SF" (13), "a hairpin" (15, 16) -> ON exactly as OFF.
  * "the corner of a beam ... too small" (9, 23) -> ON as OFF (a sliver one stem ends on stays held).
  * tiles 19 and 24 ("a beam") lie under a hairpin TRACE: kept held ON (the stroke map sums a column's ink, so a hairpin's two arms read as one
    thick stroke and the record cannot tell them from a beam; a GATHER fact, not built). Asserted, so the gap is visible.
"""
from __future__ import annotations

import functools
import gzip
import json
import pathlib

DATA = pathlib.Path(__file__).parent / "data" / "beam_ink_2_365.json.gz"
FLAG = "OMR_BEAM_INK_NOT_HELD"

#: (plate, page, system, staff, cell, stroke ordinal): the beam strokes Sean called a beam (tiles / earlier judged eighths) and the claimant OFF
BEAMS = {
    ("litolff", 2, 0, 0, 1, 0): "accidental",      # tiles 5, 6, 7 -- an accidental box's attached stroke
    ("litolff", 2, 1, 5, 13, 15): "head",          # judged eighths; the 2.318 r4 case "Litolff p2 13/1, the beam of a stem claimed as a head"
    ("litolff", 5, 0, 4, 2, 6): "word",            # tiles 3, 17, 20, 22 -- the OCR word "Lh" over the beam
    ("litolff", 6, 0, 1, 10, 7): "accidental",     # tiles 11, 21
    ("brahms", 1, 0, 0, 4, 51): "arc_trace",       # tiles 4, 8, 14
    ("brahms", 25, 0, 9, 0, 22): "head",           # judged eighth
}
#: the notes on those beams (glyph keys) -> ON the count reads one beam
BEAM_NOTES = {
    "litolff": ["glyph/2/0/0/1/0", "glyph/2/0/0/1/1", "glyph/2/0/0/1/3", "glyph/2/0/0/1/4", "glyph/2/0/0/1/15", "glyph/2/1/5/13/0", "glyph/2/1/5/13/1",
                "glyph/2/1/5/13/2", "glyph/2/1/5/13/4", "glyph/5/0/4/2/1", "glyph/5/0/4/2/2", "glyph/5/0/4/2/3", "glyph/5/0/4/2/4", "glyph/5/0/4/2/5",
                "glyph/5/0/4/2/6", "glyph/6/0/1/10/0", "glyph/6/0/1/10/3", "glyph/6/0/1/10/5"],
    "brahms": ["glyph/1/0/0/4/9", "glyph/1/0/0/4/11", "glyph/1/0/0/4/13", "glyph/1/0/0/4/33", "glyph/25/0/9/0/6"],
}
#: strokes that must stay exactly as today: Sean's right refusals, the corners, and the beam under a hairpin trace
STAY = {
    ("litolff", 12, 0, 2, 6, 3): "staff line (tiles 1, 10, 18)",
    ("brahms", 6, 1, 1, 8, 13): "the d of dim. (tiles 2, 12)",
    ("litolff", 14, 1, 8, 10, 23): "the f of sf (tile 13)",
    ("brahms", 13, 1, 2, 4, 8): "hairpin (tile 15)",
    ("brahms", 6, 0, 3, 7, 27): "hairpin (tile 16)",
    ("litolff", 8, 1, 1, 0, 27): "corner of a beam (tile 9; 2.318 r6 case p8 1/1/0)",
    ("litolff", 13, 1, 8, 8, 21): "corner of a beam (tile 23)",
    ("litolff", 13, 1, 10, 0, 56): "beam under a hairpin trace (tiles 19, 24): not released, a GATHER fact",
}
STAY_NOTES = {
    "litolff": ["glyph/8/1/1/0/2", "glyph/8/1/1/0/10", "glyph/12/0/2/6/0", "glyph/12/0/2/6/1", "glyph/12/0/2/6/2", "glyph/12/0/2/6/4",
                "glyph/13/1/8/8/2", "glyph/13/1/8/8/14", "glyph/13/1/10/0/3", "glyph/13/1/10/0/4", "glyph/13/1/10/0/5", "glyph/14/1/8/10/3"],
    "brahms": ["glyph/6/0/3/7/7", "glyph/6/1/1/8/0", "glyph/6/1/1/8/5", "glyph/13/1/2/4/1", "glyph/13/1/2/4/6"],
}
#: the stem side the record read for each note where it read ONE stem (20261127-night `one_beam_count` witness); two stems: None, as the count reads it
_UP = {"glyph/2/1/5/13/0", "glyph/2/1/5/13/1", "glyph/2/1/5/13/4", "glyph/6/0/1/10/0", "glyph/6/0/1/10/3", "glyph/6/0/1/10/5", "glyph/1/0/0/4/9",
       "glyph/1/0/0/4/11"}
_TWO = {"glyph/2/1/5/13/2", "glyph/1/0/0/4/13", "glyph/1/0/0/4/33"}
SIDE = {g: (None if g in _TWO else "up" if g in _UP else "down") for gs in (BEAM_NOTES, STAY_NOTES) for p in gs for g in gs[p]}


@functools.lru_cache(maxsize=1)
def _rows():
    return json.load(gzip.open(DATA, "rt"))


@functools.lru_cache(maxsize=4)
def _owner(plate: str, flag: str):
    from tools.omr.staged import claim_readout as CR
    return CR.owner_verdicts(_rows()[plate], {FLAG: flag})


def _state(plate, key, flag):
    e = ((_owner(plate, flag).get(tuple(key[:4])) or {}).get("strokes") or {}).get(str(key[4]))
    return (e[0], e[1]) if e else ("unclaimed", None)


def _views(plate, ck, detail):
    from tools.omr.staged import beam_strokes as BS
    from tools.omr.staged.record import STROKE_GLYPH_BASE
    st = (detail or {}).get("strokes") or {}
    out = []
    for o in _rows()[plate]["observations"]:
        if o["quantity"] != "stroke" or not o["subject"].startswith("glyph/%d/%d/%d/%d/" % ck):
            continue
        od = int(o["subject"].split("/")[5]) - STROKE_GLYPH_BASE
        d = o["detail"]
        e = st.get(str(od))
        kind, fam = str(o["value"]), ""
        if e and e[0] in ("decided", "merged"):
            kind, fam = "owned", e[1]
        elif e and e[0] == "contested":
            kind = "contested"
        out.append(BS.StrokeView(cut="", family=fam, ordinal=od, kind=kind, box=tuple(float(v) for v in d["stroke_box"][:4]),
                                 length=float(d.get("length_spaces") or 0), thickness=float(d.get("thickness_spaces") or 0),
                                 sagitta=d.get("sagitta_spaces"), angle=float(d.get("angle_deg") or 0),
                                 touches=tuple((int(a), float(b)) for a, b in (d.get("touches") or ())),
                                 space_px=float(d.get("staff_space_local_px") or 0), row_id=o["id"],
                                 profile=tuple(int(v) for v in (d.get("profile_sixteenths") or ())),
                                 ends=tuple(float(v) for v in (d.get("ends") or ())[:4]),
                                 end_steps=tuple(float(v) for v in (d.get("end_steps_from_top") or ())[:2]),
                                 tip_columns=tuple(d.get("tip_columns") or ())))
    return out


def _count(plate, glyph, flag):
    from tools.omr.staged import beam_strokes as BS
    ck = tuple(int(x) for x in glyph.split("/")[1:5])
    box = next(o["value"] for o in _rows()[plate]["observations"] if o["quantity"] == "glyph_box" and o["subject"] == glyph)
    v = _views(plate, ck, _owner(plate, flag).get(ck))
    got = BS.beam_count(v, BS.roles(v, face_join=True, trough=True, one_count=True), box[1:5], SIDE.get(glyph))
    return got["state"], got["certain"], sorted({c for s in got["stems"] for c in s.get("causes", [])})


def test_sean_s_beams_are_held_off_and_free_on():
    for key, claimant in BEAMS.items():
        plate = key[0]
        off, on = _state(plate, key[1:], "0"), _state(plate, key[1:], "1")
        assert off[0] in ("decided", "merged") and off[1] == claimant, (key, off)          # the old behaviour: held (the control fails here)
        assert on[0] not in ("decided", "merged", "contested"), (key, on)


def test_notes_on_sean_s_beams_count_one_beam_on_and_are_narrowed_off():
    for plate, glyphs in BEAM_NOTES.items():
        for g in glyphs:
            assert _count(plate, g, "0") == ("narrowed", 0, ["claimed_ink_at_tip"]), g
            assert _count(plate, g, "1") == ("read", 1, []), g


def test_right_refusals_corners_and_the_hairpin_trace_stay_as_today():
    for key, what in STAY.items():
        plate = key[0]
        off, on = _state(plate, key[1:], "0"), _state(plate, key[1:], "1")
        assert off[0] in ("decided", "merged"), (what, off)
        assert on == off, (what, off, on)
    for plate, glyphs in STAY_NOTES.items():
        for g in glyphs:
            assert _count(plate, g, "1") == _count(plate, g, "0") == ("narrowed", 0, ["claimed_ink_at_tip"]), g


def test_off_is_the_record_s_own_verdict():
    """OFF re-run equals the stroke owner verdict the 20261127-night record holds for every stroke above (the fixture is the record's rows)."""
    for key in list(BEAMS) + list(STAY):
        plate = key[0]
        assert _state(plate, key[1:], "0")[0] in ("decided", "merged")


def test_beam_rule_is_structural():
    """`beam_joins_stem_ends` on hand-made ink: two stems ending under a thick bar is a beam; a stem crossing it, one stem, a thin bar, a bar
    touching two barlines are not."""
    from tools.omr.staged import stroke_owner as SO
    sp = 100.0
    bar = SO.Ink(0, "horizontal", (0, 0, 400, 60), 4.0, 0.6, 2.4, sp, ((1, 1.0), (2, 1.0)))
    st1 = SO.Ink(1, "vertical", (10, 0, 10, 350), 3.5, 0.1, 0.35, sp, ((0, 1.0),))
    st2 = SO.Ink(2, "vertical", (380, 0, 10, 350), 3.5, 0.1, 0.35, sp, ((0, 1.0),))
    by = {0: bar, 1: st1, 2: st2}
    assert SO.beam_joins_stem_ends(bar, by)
    crossing = SO.Ink(2, "vertical", (380, -200, 10, 550), 5.5, 0.1, 0.55, sp, ((0, 1.0),))
    assert not SO.beam_joins_stem_ends(bar, {0: bar, 1: st1, 2: crossing})
    thin = SO.Ink(0, "horizontal", (0, 0, 400, 40), 4.0, 0.4, 1.6, sp, ((1, 1.0), (2, 1.0)))
    assert not SO.beam_joins_stem_ends(thin, {0: thin, 1: st1, 2: st2})
    rule1 = SO.Ink(3, "vertical", (0, -600, 10, 1200), 12.0, 0.1, 1.2, sp, ((0, 1.0),))
    rule2 = SO.Ink(4, "vertical", (395, -600, 10, 1200), 12.0, 0.1, 1.2, sp, ((0, 1.0),))
    ruled = SO.Ink(0, "horizontal", (0, 0, 400, 60), 4.0, 0.6, 2.4, sp, ((1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0)))
    assert not SO.beam_joins_stem_ends(ruled, {0: ruled, 1: st1, 2: st2, 3: rule1, 4: rule2})
