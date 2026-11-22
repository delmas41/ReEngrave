"""ROADMAP 2.306 / 2.78 -- ON A STRING STAFF, NOTES PRINTED TOGETHER WITH DIFFERENT LENGTHS ARE WRITTEN SOUNDING TOGETHER, EACH WITH ITS OWN
LENGTH (flag `OMR_STRING_STOPS_OWN_VALUE`, default OFF). STAGED: `staff_family` (which family plays a staff), ADJUDICATE
`stem_value._string_stop_ruling`, EXPORT `_chords_whose_value_would_be_voted` / `_order_string_stops` / `_event_duration_certain`.

Sean 2026-11-21 (page-facts): "Both of those examples are string section parts ... So whereas the rule is definitely true before for brass and
woodwinds, it doesn't work for strings." Controls are REAL record rows (`fixtures/strings_mixed_2_306.json`, cut by
`benchmarks/page-ledger-2026-11/2306/strings_mixed_cut_fixture.py` from saved gathers re-adjudicated on this lane):
  * Brahms 5/1/10/7, Sean's chord (second violins, "two dotted quarters ... a quarter note that's not dotted"), as the 2.306 page stem
    reader joins it (r16 gather, this lane merged with lane-2.306-twovoice): D5 and B4 dotted, G4 undotted, one up stem (its G3 stands on
    its own down stem and is not a member);
  * Brahms 5/1/9/2, the same passage two bars earlier, on today's main (our look at the print: two dotted heads, a plain one below);
  * Beethoven 5 first violins 2/0/7/4, Sean's other chord: on main its heads join no stem; the page stem reader puts the three quarters on
    one stem and the half on another -- never one string stop here (two stems);
  * held, misreads on string staves: 2/0/7/4's two boxes on a sharp (Sean 2026-11-19 "a sharp sign blending into the barline"), r18 tile 3
    6/1/8/11 ("two half notes with a tremolo slash"), 8/1/8/4 (two half notes an octave apart, the lower read black, its ink hollow; our
    look), 4/0/6/0 (a filled and a hollow box on one F5);
  * a woodwind stem whose heads' dots differ (Brahms 19/1/2/2): held.
"""
import collections
import json
import os
import re
from types import SimpleNamespace

import pytest

from tools.omr.staged import export as E
from tools.omr.staged import staff_family as SF
from tools.omr.staged.adjudicators import stem_value as SV

HERE = os.path.dirname(__file__)
FX = os.path.join(HERE, "fixtures", "strings_mixed_2_306.json")


def _fx():
    with open(FX) as f:
        return json.load(f)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv(SF.ENV, "1")


# ── part 1: which family plays a staff ──────────────────────────────────────

def test_a_named_staff_takes_its_family_from_its_own_name():
    assert SF.decide("Violin", None, None, ())["family"] == SF.STRINGS
    assert SF.decide("Flute", None, None, ())["family"] == SF.WOODWIND
    assert SF.decide("Horn", None, None, ())["family"] == SF.BRASS
    assert SF.decide("Timpani", None, None, ())["family"] == SF.PERCUSSION
    assert SF.decide("Harp", None, None, ())["family"] == SF.OTHER


def test_an_unnamed_staff_takes_the_family_of_the_part_it_continues_only_with_its_clef():
    mates = [("staff/1/0/7", "Violin", "treble")]
    got = SF.decide(None, "treble", 7, mates)
    assert got["family"] == SF.STRINGS and got["source"] == SF.SOURCE_SAME_PART
    # never from position alone: no decided slot, a clef that differs or is unread, named staves that disagree, nobody named
    assert SF.decide(None, "treble", None, mates)["family"] == SF.UNKNOWN
    assert SF.decide(None, "bass", 7, mates)["family"] == SF.UNKNOWN
    assert SF.decide(None, None, 7, mates)["family"] == SF.UNKNOWN
    assert SF.decide(None, "treble", 7, mates + [("staff/3/0/7", "Flute", "treble")])["family"] == SF.UNKNOWN
    assert SF.decide(None, "treble", 7, [])["family"] == SF.UNKNOWN


def test_real_records_every_staff_gets_the_family_the_run_gave_it_and_unnamed_ones_need_the_slot():
    """The staff rows of the two re-adjudicated frozen-sample records: Litolff's later pages name only winds, trumpets and timpani in the
    margin, so its string staves are unnamed and take their family from the decided slot their page-1 staff is named on. The control can
    fail: with the slot rows removed, no unnamed staff gets a family."""
    n_unnamed_strings = 0
    for plate, rows in _fx()["staves"].items():
        inst = {k: r["instrument"] for k, r in rows.items()}
        slot = {k: r["slot_index"] for k, r in rows.items()}
        clef = {k: r["clef"] for k, r in rows.items()}
        got = SF.families_from_rows(inst, slot, clef, rows)
        for k, r in rows.items():
            assert got[k]["family"] == r["expect_family"], (plate, k, got[k], r)
        unnamed = [k for k in rows if not SF._name_of(inst[k])]
        n_unnamed_strings += sum(1 for k in unnamed if got[k]["family"] == SF.STRINGS)
        none = SF.families_from_rows(inst, {}, clef, rows)
        assert all(none[k]["family"] == SF.UNKNOWN for k in unnamed)
    assert n_unnamed_strings >= 60


# ── part 2: ADJUDICATE, one stem's value ─────────────────────────────────────

def _members(chord):
    out = []
    for h in chord["heads"]:
        if h["outcome"] not in ("decided", "narrowed"):
            continue            # a refused box (a slash) is joined to the stem but is no member (`_member_of`)
        opts = [tuple(o) for o in h["options"]]
        box = tuple(h["box"])
        out.append(SimpleNamespace(key=h["key"], sub=h["key"], whole_class=h.get("whole_class", False),
                                   decided=h["outcome"] == "decided" and len(opts) == 1, read=bool(opts), options=opts,
                                   box=box, cy=box[1] + box[3] / 2.0,
                                   verdict=SimpleNamespace(detail={"head_ink": h.get("head_ink"), "head_ink_guess": h.get("head_ink_guess")})))
    return out


def _ruling(chord, family, monkeypatch):
    monkeypatch.setattr(SV, "_staff_family", lambda ev, cell: {"family": family, "source": "test"})
    members = _members(chord)
    flush = {h["key"]: h["flush"] for h in chord["heads"]}          # every box joined to the stem, as `adjudicate_stem_value` passes it
    ev = SimpleNamespace(subject=SimpleNamespace(at=lambda kind: None))
    return {m.key: SV._string_stop_ruling(ev, members, flush, m, "stem", 1.0, ()) for m in members}


@pytest.mark.parametrize("name", ["brahms_5_1_10_7", "brahms_5_1_9_2"])
def test_a_string_stop_keeps_each_heads_own_length(name, flag_on, monkeypatch):
    chord = _fx()["chords"][name]
    out = _ruling(chord, SF.STRINGS, monkeypatch)
    lengths = set()
    for h in chord["heads"]:
        r = out[h["key"]]
        assert r is not None and r.reason == SV.STRING_STOP_REASON, (name, h["key"])
        b, lv, d = h["expect_value"]
        assert (r.value["dots"], r.value["beam_levels"]) == (d, lv) and abs(r.value["written"] - SV._written(b, lv, d)) < 1e-9
        assert r.detail["status"][h["key"]] == h["expect_status"]
        lengths.add(r.value["written"])
    assert lengths == {1.0, 1.5}                    # two dotted quarters and a plain quarter, as Sean read his chord
    dotless = [h for h in chord["heads"] if h["expect_value"][2] == 0]
    assert dotless and all(out[h["key"]].detail["status"][h["key"]] == SV.STRING_STOP_DOT_NOT_SEEN for h in dotless)


@pytest.mark.parametrize("name", ["brahms_5_1_10_7", "brahms_5_1_9_2"])
def test_the_same_chords_on_a_wind_brass_other_or_unknown_staff_keep_one_value(name, flag_on, monkeypatch):
    chord = _fx()["chords"][name]
    for fam in (SF.WOODWIND, SF.BRASS, SF.UNKNOWN, SF.OTHER, SF.PERCUSSION):
        assert all(r is None for r in _ruling(chord, fam, monkeypatch).values()), fam


def test_flag_off_nothing_changes(monkeypatch):
    monkeypatch.setenv(SF.ENV, "0")
    assert all(r is None for r in _ruling(_fx()["chords"]["brahms_5_1_10_7"], SF.STRINGS, monkeypatch).values())


@pytest.mark.parametrize("name", ["litolff_2_0_7_4_sharp", "litolff_6_1_8_11", "litolff_8_1_8_4", "litolff_4_0_6_0"])
def test_misreads_on_string_staves_stay_held(name, flag_on, monkeypatch):
    """Each was written mixed by the first build (before the three guards): a sharp's two boxes (one hollow box read as a half, its ink a
    guess, the other's ink unread), tile 3's slash (a refused box on the stem, two boxes whose ink did not say), a half read black whose ink
    is hollow, one head boxed twice at one place."""
    assert all(r is None for r in _ruling(_fx()["chords"][name], SF.STRINGS, monkeypatch).values())


def test_beethovens_chord_is_two_stems_on_the_page_reader_so_never_one_string_stop(flag_on, monkeypatch):
    """The three quarters stand on one stem and agree (each narrowed only in its beams); the half stands on another stem. One stem carries
    one length here, so nothing is a stop -- the chord is the two-stem writer's (2.314), held today."""
    chord = _fx()["chords"]["beethoven_2_0_7_4_quarters"]
    assert len(chord["heads"]) == 3
    assert all(r is None for r in _ruling(chord, SF.STRINGS, monkeypatch).values())


def test_a_woodwind_stem_whose_dots_differ_stays_held_but_would_be_a_stop_on_strings(flag_on, monkeypatch):
    chord = _fx()["chords"]["wind_brahms_19_1_2_2"]
    assert chord["family"] == SF.WOODWIND
    assert all(r is None for r in _ruling(chord, SF.WOODWIND, monkeypatch).values())
    assert all(r is not None for r in _ruling(chord, SF.STRINGS, monkeypatch).values())     # the control can fail: only the family holds it


def test_a_head_whose_fill_was_not_read_is_never_written_mixed(flag_on, monkeypatch):
    chord = json.loads(json.dumps(_fx()["chords"]["brahms_5_1_9_2"]))
    h = chord["heads"][1]
    b, lv, d = h["options"][0]
    h["outcome"], h["options"] = "narrowed", [[b, lv, d], [2.0, lv, d]]
    assert all(r is None for r in _ruling(chord, SF.STRINGS, monkeypatch).values())


# ── part 3: EXPORT, the written bar ──────────────────────────────────────────

def _dets(chord, with_stop=True):
    out = []
    for h in chord["heads"]:
        if h["expect_status"] is None:
            continue
        d = dict(h["det"], category="notehead")
        x0, y0, x1, y1 = d["bbox"]                                 # page px corners -> the exporter's [x, y, w, h]
        d["bbox"] = [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]
        if with_stop:
            d["string_stop"] = {"status": h["expect_status"], "candidates": h.get("candidates"), "family_source": "own_name"}
        out.append(d)
    return out


def _runs(dets):
    cell = E.Cell(0, 0, 0, 0, detections=list(dets))
    return cell, {"r": SimpleNamespace(cells={0: cell})}


@pytest.mark.parametrize("name", ["brahms_5_1_10_7", "brahms_5_1_9_2"])
def test_the_chord_is_written_as_one_chord_each_note_its_own_length_longest_first(name, flag_on):
    chord = _fx()["chords"][name]
    dets = _dets(chord)
    cell, runs = _runs(dets)
    assert E._chords_whose_value_would_be_voted(runs) == []           # nothing held
    evs = [e for e in E._events(cell) if e["kind"] == "chord"]
    assert len(evs) == 1
    ev = evs[0]
    longest = max(h["duration_beats"] for h in dets)
    assert ev["noteheads"][0]["duration_beats"] == longest and ev["duration_beats"] == longest
    assert E._event_duration_certain(ev)                            # the chord ends with its longest (read) note
    lines, units = E._measure_events_xml([ev], 4, collections.Counter())
    xml = "\n".join(lines)
    assert units == int(round(longest * 4))                         # the voice advances by the longest note (MusicXML: the first)
    assert xml.count("<note") == len(dets) and xml.count("<chord/>") == len(dets) - 1
    assert sorted(int(x) for x in re.findall(r"<duration>(\d+)</duration>", xml)) == sorted(int(round(h["duration_beats"] * 4)) for h in dets)
    assert xml.count("<dot/>") == sum(h["dots"] for h in dets)
    n_guess = sum(1 for h in chord["heads"] if h["expect_status"] == SV.STRING_STOP_DOT_NOT_SEEN)
    assert n_guess >= 1 and xml.count(E.STRING_STOP_DOT_RULE) == n_guess   # a dot not seen is GUESSED, blue; the dotted heads READ


def test_without_the_string_stop_finding_or_with_the_flag_off_the_chord_is_held_as_before(monkeypatch):
    chord = _fx()["chords"]["brahms_5_1_9_2"]
    monkeypatch.setenv(SF.ENV, "1")
    _cell, runs = _runs(_dets(chord, with_stop=False))
    assert len(E._chords_whose_value_would_be_voted(runs)) == 3
    monkeypatch.setenv(SF.ENV, "0")
    _cell, runs = _runs(_dets(chord))
    assert len(E._chords_whose_value_would_be_voted(runs)) == 3


def test_a_head_on_another_stem_in_the_group_keeps_the_whole_group_held(flag_on):
    """Brahms 5/1/10/7's G3 has its own down stem (page stem reader). Where the two-stems writer declines the bar (as it did on the r16
    record), the heads group by x and the group stands on two stems -- held as before, never written one after another (r18's withdrawn
    split)."""
    chord = _fx()["chords"]["brahms_5_1_10_7"]
    dets = _dets(chord)
    last = dets[-1]
    g3 = dict(last, glyph="glyph/5/1/10/7/2", pitch="G3", stem_id="obs:other", string_stop=None,
              bbox=[last["bbox"][0], last["bbox"][1] + 150, last["bbox"][2], last["bbox"][3]])
    cell, runs = _runs(dets + [g3])
    cell.two_stems_declined = True          # as in the record: the two-stems writer (2.314) declined the bar, so the heads group by x
    assert len(E._chords_whose_value_would_be_voted(runs)) == 4
