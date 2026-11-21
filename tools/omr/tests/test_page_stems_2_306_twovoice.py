"""ROADMAP 2.306, the two-voice piece -- A HEAD WITH A STEM UP AND A STEM DOWN IS TWO VOICES, AND THE PAGE STEM READER CARRIES IT (flag
`OMR_PAGE_STEMS`, default OFF). STAGED GATHER (`page_stems._unison_heads`, the filing in `gather_page_stems`) + ADJUDICATE (`stem_value.
_page_two_voices`, `page_voice_stems`; read by `unison_two.adjudicate_unison_voices` and `rhythm`'s per-voice beam count).

The rule, as a musician says it (page-facts, Sean 2026-10-10: "When one note has stems going up and down it is always 2 voices"): one head, a stem
up and a stem down, each stem's ink touching the head: two voices sharing that note, each taking its value from its OWN stem. Never two voices from
one stem; never where one of the strokes does not touch the head's ink (that stroke is a neighbour's: the touching one is the head's one stem).

Controls are REAL page windows (CLAUDE rule 7), cut from the r15 gathers' page-stem inputs (`fixtures/page_stems_2_306_twovoice.json`,
`benchmarks/page-ledger-2026-11/2306/twovoice_cut_fixture.py`): Litolff 2/67, 6/220, 16/195, 16/517 and Brahms 5/413, 5/353, 5/90, 5/493 (a stem
each way, both touching, by our look at the print -- out/print/2.306-twovoice/); Litolff 6/9 and Brahms 0/268 (one stem; the other stroke is a
neighbour's, our look); Brahms 5/772 (the low G3 of 5/1/10/7: its own down stem beside the chord's up stem -- two heads, never a unison). NOT
Sean's judgement: our look. Each control fails with the page map's contacts removed.
"""
import json
import os
from types import SimpleNamespace

from tools.omr.staged import page_stems as PS

HERE = os.path.dirname(__file__)
FX = os.path.join(HERE, "fixtures", "page_stems_2_306_twovoice.json")


def _windows():
    with open(FX) as f:
        return json.load(f)["windows"]


def _read(w, no_contacts=False):
    heads = [dict(h, box=tuple(h["box"])) for h in w["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in w["verticals"]]
    cross = [dict(c, box=tuple(c["box"])) for c in w["crossers"]]
    strokes = {int(k): dict(v, box=tuple(v["box"]), touches=[] if no_contacts else v["touches"]) for k, v in w["strokes"].items()}
    held = {int(k): v for k, v in w["held"].items()}
    return PS.read(heads, verts, held, crossers=cross, strokes=strokes)


def test_a_head_with_a_stem_each_way_both_touching_is_two_voices_and_both_stems_are_filed():
    n = 0
    for w in _windows():
        if w["expect"] != "unison":
            continue
        res = _read(w)
        r = res["heads"][w["head"]]
        assert r["state"] == "two_voices" and r["how"] == PS.UNISON_HOW, (w["page"], w["head"], r)
        up, dn = r["voices"]["up"]["stroke"], r["voices"]["down"]["stroke"]
        assert up != dn                                              # never two voices from one stem
        assert res["stems"][up]["direction"] == "up" and res["stems"][dn]["direction"] == "down"
        assert w["head"] in res["stems"][up]["heads"] and w["head"] in res["stems"][dn]["heads"]
        n += 1
    assert n == 8


def test_where_one_stroke_does_not_touch_the_head_it_is_one_stem_never_two_voices():
    n = 0
    for w in _windows():
        if not w["expect"].startswith("one:"):
            continue
        r = _read(w)["heads"][w["head"]]
        assert r["state"] == "one" and r["direction"] == w["expect"].split(":")[1], (w["page"], w["head"], r)
        assert r["how"] != PS.UNISON_HOW
        n += 1
    assert n == 5


def test_control_without_the_ink_contacts_no_head_is_filed_as_two_voices():
    for w in _windows():
        if w["expect"] != "unison":
            continue
        r = _read(w, no_contacts=True)["heads"][w["head"]]
        assert r["how"] != PS.UNISON_HOW and r.get("voices") is None, (w["page"], w["head"], r)


def _row(rid, value, **detail):
    return SimpleNamespace(id=rid, value=value, detail=detail)


def test_voice_rows_needs_one_row_per_voice():
    up = _row("p1", "s1", how=PS.UNISON_HOW, voice="up")
    dn = _row("p2", "s2", how=PS.UNISON_HOW, voice="down")
    assert PS.voice_rows([up, dn]) == {"up": up, "down": dn}
    assert PS.voice_rows([up]) is None
    assert PS.voice_rows([_row("p3", "s1", how="engraving_side", direction="up")]) is None


def test_the_unison_ruling_names_each_voices_own_stem_and_never_one_stem_twice():
    from tools.omr.staged.adjudicators import stem_value as SV
    head = (100.0, 100.0, 20.0, 14.0)
    s_up, s_dn = _row("stem:a", [118.0, 60.0, 3.0, 50.0]), _row("stem:b", [99.0, 105.0, 3.0, 50.0])
    stems = [(s_up, SV._xywh(s_up.value)), (s_dn, SV._xywh(s_dn.value))]
    voices = {"up": _row("ps1", "stem:a", how=PS.UNISON_HOW, voice="up", page_stroke=7),
              "down": _row("ps2", "stem:b", how=PS.UNISON_HOW, voice="down", page_stroke=8)}
    r = SV._page_two_voices(head, stems, "box1", voices)
    assert r.reason == "unison_two_voices" and r.value is None and {c.value for c in r.candidates} == {"stem:a", "stem:b"}
    assert r.detail["page_voices"] == {"up": "stem:a", "down": "stem:b"}
    vs = SV.page_voice_stems(r.detail, [s_up, s_dn])
    assert vs == {"up": [s_up], "down": [s_dn]}
    same = {"up": voices["up"], "down": _row("ps2", "stem:a", how=PS.UNISON_HOW, voice="down", page_stroke=7)}
    assert SV._page_two_voices(head, stems, "box1", same) is None           # one stem is never two voices
    gone = {"up": voices["up"], "down": _row("ps2", "stem:zz", how=PS.UNISON_HOW, voice="down")}
    assert SV._page_two_voices(head, stems, "box1", gone) is None           # a row the cell no longer holds: the cell join stands
    assert SV.page_voice_stems({"stem": "stem:a"}, [s_up, s_dn]) is None    # a one-stem ruling names no voices


def test_a_unison_whose_one_voice_stands_in_a_disagreeing_chord_is_held_whole_and_returned_once(monkeypatch):
    """EXPORT `_chords_whose_value_would_be_voted` (2.89): the up voice of a unison head and its second voice are ONE printed head. Litolff
    2/1/3/2/5 on the replayed record: the down voice joined a chord whose values disagree and was held while the up voice was written -- one
    glyph written AND dropped (the balance raised). Both voices are held; the glyph is returned once. Fails with the pairing removed."""
    from tools.omr.staged import export as E
    head = dict(glyph="glyph/2/1/3/2/5", category="notehead", unison_head=True, duration_beats=1.0, duration_type="quarter", dots=0)
    twin = dict(head, unison_head=None, unison_twin=True, duration_beats=2.0, duration_type="half")
    other = dict(glyph="glyph/2/1/3/2/7", category="notehead", duration_beats=1.0, duration_type="quarter", dots=0)
    cell = SimpleNamespace(detections=[head, twin, other])
    runs = {"P1": SimpleNamespace(cells={0: cell})}
    monkeypatch.setattr(E, "_group_chords", lambda dets: [dict(kind="chord", noteheads=[d for d in dets if d is not head])])
    removed = E._chords_whose_value_would_be_voted(runs)
    assert sorted(d["glyph"] for d in removed) == ["glyph/2/1/3/2/5", "glyph/2/1/3/2/7"]
    assert cell.detections == []                    # never one voice written and the other held
