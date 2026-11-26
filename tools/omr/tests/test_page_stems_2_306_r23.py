"""ROADMAP 2.306 r23 -- the retire step (STAGED GATHER + ADJUDICATE, inside `OMR_PAGE_STEMS`, default OFF). Controls are REAL page windows cut
from the reader's exact inputs pickled during a gather of the r23 tree (`benchmarks/page-ledger-2026-11/2306/r23_cut_window.py`), each shown
failing with the rule off (CLAUDE rule 7).

(1) A HEAD TOUCHES ONE OF ITS TWO STROKES, AND THE OTHER IS ANOTHER HEAD'S STEM. A stroke up at the head's right and a stroke down at its left;
the head's ink touches only one. Where the page already stands another head on the untouched stroke -- read the other way (a neighbour's stem
standing at this head's other edge), or the same way from a head beyond this one (two voices in one column: the upper head takes the up stem,
the lower the down stem, Sean 2026-11-14) -- the stroke the head touches is its stem. Never where the untouched stroke holds no other head (it may
be this head's own second voice whose contact the map missed); never where both strokes touch the head (two voices, or a stroke holding another
head: left as before).

(3) A COPY OF A HEAD FILED WITH ANOTHER STAFF says so (`Q.PAGE_STEM` abstention `on_another_staff`), and the old cell join no longer answers for
it (`page_stem_on_another_staff`).
"""
import json
import os
from types import SimpleNamespace

import pytest

from tools.omr.staged import page_stems as PS
from tools.omr.staged.adjudicators import stem_value as SV

HERE = os.path.dirname(__file__)
WIN = os.path.join(HERE, "fixtures", "page_stems_2_306_r23.json")


def _window(name):
    w = json.load(open(WIN))[name]
    heads = [dict(h, box=tuple(h["box"])) for h in w["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in w["verticals"]]
    cross = [dict(c, box=tuple(c["box"])) for c in w["crossers"]]
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in w["strokes"].items()}
    held = {int(k): v for k, v in w["held"].items()}
    return w, heads, verts, held, cross, strokes


def _read(name):
    w, heads, verts, held, cross, strokes = _window(name)
    return w, PS.read(heads, verts, held, crossers=cross, strokes=strokes)["heads"]


def _rule_off(monkeypatch):
    monkeypatch.setattr(PS, "_untouched_is_anothers_stem", lambda *a, **k: False)


TOUCHED = ["opp_up_litolff_2_0_7_16_8", "opp_up_litolff_2_1_8_10_9", "opp_down_litolff_9_0_1_1_10", "opp_down_litolff_4_1_2_13_12",
           "same_down_brahms_0_0_11_2_4", "same_up_brahms_0_0_11_3_10", "opp_down_brahms_0_0_12_4_0"]


@pytest.mark.parametrize("name", TOUCHED)
def test_the_stroke_the_head_touches_is_its_stem_when_the_other_is_anothers(name):
    """Our look at full size (crops `out/print/2.306-r23/`): Litolff 2/0/7/16/8 an eighth whose up stem runs to the beam; the stroke at its left
    is the lower neighbour's up stem. 9/0/1/1/10 a chord's down stem; the stroke at its right is the next chord's down stem. Brahms 0/0/11/2/4
    the lower and 0/0/11/3/10 the upper of two voices a step apart -- the upper head's up stem, the lower's down stem; 0/0/12/4/0 a down stem,
    the stroke at its right the next note's down stem. Each was left `two_voices` /
    `one_touches` and the old cell join answered in its place."""
    w, r = _read(name)
    got = r[w["head"]]
    assert got["state"] == "one" and got["how"] == PS.OTHER_STEM_HOW and got["direction"] == w["expect"], got


@pytest.mark.parametrize("name", TOUCHED)
def test_rule_off_the_head_is_left_unresolved_as_r22_left_it(name, monkeypatch):
    """The control can fail: without the rule each head is the r22 reading (`two_voices`, `one_touches`)."""
    _rule_off(monkeypatch)
    w, r = _read(name)
    got = r[w["head"]]
    # r24: rule 1 (another head's stem) still never fires here; Litolff 10/1/10/11/1 is now read by r24's touched-stroke rule (its untouched
    # stroke is shorter than a stem: `test_page_stems_2_306_r24.py`), the Brahms head stays unresolved
    assert got["how"] != PS.OTHER_STEM_HOW, got
    if "brahms" in name:
        assert got["state"] == "two_voices" and got.get("why") == "one_touches", got


@pytest.mark.parametrize("name", ["never_unheld_litolff_10_1_10_11_1", "never_unheld_brahms_8_0_3_1_10"])
def test_never_when_the_untouched_stroke_holds_no_other_head(name):
    """Litolff 10/1/10/11/1 (an eighth on the bottom line, up stem to the beam): the stroke at its left is a short piece below the staff that no
    head stands on. Brahms 8/0/3/1/10 (a half note under a quarter, two voices; our look: its own stem is DOWN at its left, which the map read
    as not touching it): the untouched stroke holds no head. Not anyone's stem on the page, so nothing says it is not this head's: left
    unresolved (the Brahms one shows why -- deciding the touched stroke there would have been wrong)."""
    w, r = _read(name)
    got = r[w["head"]]
    # r24: rule 1 (another head's stem) still never fires here; Litolff 10/1/10/11/1 is now read by r24's touched-stroke rule (its untouched
    # stroke is shorter than a stem: `test_page_stems_2_306_r24.py`), the Brahms head stays unresolved
    assert got["how"] != PS.OTHER_STEM_HOW, got
    if "brahms" in name:
        assert got["state"] == "two_voices" and got.get("why") == "one_touches", got


def test_never_when_the_other_head_on_the_stroke_is_this_note_seen_again():
    """Litolff 8/1/1/15/3 (found on the r23 full sample, our look at 3x): three eighths beamed above on up stems AND below on down stems --
    the third head is shared by two voices. Its up stem is held by a stem-end box filed from the staff above, standing on this head's own
    oval (the same ink). That box is this note again, not another head: left unresolved (the first build gave the head only its down stem and
    the upper voice lost its eighth). The control can fail: without the head-ink comparison the rule takes the down stem."""
    w, heads, verts, held, cross, strokes = _window("never_same_note_litolff_8_1_1_15_3")
    res = PS.read(heads, verts, held, crossers=cross, strokes=strokes)
    got = res["heads"][w["head"]]
    assert got["state"] == "two_voices" and got.get("why") == "one_touches", got
    up = next(c for c in got["candidates"] if c["direction"] == "up")
    stems = {int(o): dict(s, directions=set(s["directions"])) for o, s in res["stems"].items()}
    h = next(x for x in heads if x["id"] == w["head"])
    hink = PS.head_ink(heads, strokes, held)
    assert not PS._untouched_is_anothers_stem(h, int(up["stroke"]), "up", stems, heads, hink)
    assert PS._untouched_is_anothers_stem(h, int(up["stroke"]), "up", stems, heads)


def test_never_when_both_strokes_touch_the_head():
    """Litolff 4/1/5/6/2: both strokes touch the head's ink and the up stroke also holds another head -- left `stroke_holds_another_head` as
    before. The control can fail the other way: the up stroke IS another head's stem (`_untouched_is_anothers_stem` says so), so only the
    head's ink touching both keeps the rule from choosing."""
    w, heads, verts, held, cross, strokes = _window("both_touch_litolff_4_1_5_6_2")
    res = PS.read(heads, verts, held, crossers=cross, strokes=strokes)
    got = res["heads"][w["head"]]
    assert got["state"] == "two_voices" and got.get("why") == "stroke_holds_another_head", got
    up = next(c for c in got["candidates"] if c["direction"] == "up")
    stems = {int(o): dict(s, directions=set(s["directions"])) for o, s in res["stems"].items()}
    h = next(x for x in heads if x["id"] == w["head"])
    assert PS._untouched_is_anothers_stem(h, int(up["stroke"]), "up", stems, heads)


def test_same_way_only_from_a_head_beyond_this_one():
    """A stroke read the same way by another head is that head's stem only where that head stands beyond this one in the stem's direction; a
    head on it below this one (for an up stem) means the stroke passes this head on its way: never taken as another's."""
    h = dict(id="h", box=(0.0, 100.0, 20.0, 116.0))
    above = dict(id="a", box=(0.0, 90.0, 20.0, 106.0))
    below = dict(id="b", box=(0.0, 110.0, 20.0, 126.0))
    heads = [h, above, below]
    assert PS._untouched_is_anothers_stem(h, 1, "up", {1: dict(heads=["a"], directions={"up"})}, heads)
    assert not PS._untouched_is_anothers_stem(h, 1, "up", {1: dict(heads=["b"], directions={"up"})}, heads)
    assert not PS._untouched_is_anothers_stem(h, 1, "up", {1: dict(heads=["a", "b"], directions={"up"})}, heads)
    assert PS._untouched_is_anothers_stem(h, 1, "up", {1: dict(heads=["b"], directions={"down"})}, heads)
    assert not PS._untouched_is_anothers_stem(h, 1, "up", {1: dict(heads=["h"], directions={"up"})}, heads)
    assert not PS._untouched_is_anothers_stem(h, 2, "up", {1: dict(heads=["a"], directions={"up"})}, heads)


# ── (4) the stroke that ends at another head is that head's stem ─────────────────────────────────────────────────────────────────────────

ENDS = ["ends_down_litolff_4_1_8_5_5", "ends_down_litolff_4_1_2_4_9", "ends_up_litolff_2_1_8_10_16", "ends_up_litolff_9_0_3_1_16"]


@pytest.mark.parametrize("name", ENDS)
def test_the_stroke_ending_at_another_head_is_that_heads_stem(name):
    """Both strokes touch the head (Litolff merges), one ends at ANOTHER head that reads it as its own stem pointing away from itself. Our
    look at full size: 4/1/8/5/5 the upper note's down stem runs past this head's right edge to the beam, this head's own stem is down at its
    left; 2/1/8/10/16 and 9/0/3/1/16 the middle head of chords on up stems, the stroke at its left is the lower neighbour's up stem. Each was
    left `two_voices` / `ends_at_another_head` (the stroke a stem's length, so the r19 outline rule stood aside)."""
    w, r = _read(name)
    got = r[w["head"]]
    assert got["state"] == "one" and got["how"] == PS.OTHER_STEM_HOW and got["direction"] == w["expect"], got


@pytest.mark.parametrize("name", ENDS)
def test_ends_rule_off_left_as_r22_left_it(name, monkeypatch):
    monkeypatch.setattr(PS, "_is_the_stem_of_the_head_it_ends_at", lambda *a, **k: False)
    w, r = _read(name)
    got = r[w["head"]]
    assert got["state"] == "two_voices" and got.get("why") == "ends_at_another_head", got


def test_never_when_the_head_it_ends_at_has_no_head_ink_of_its_own():
    """Litolff 4/1/7/4/18: the stroke ends at a box the head identity found no oval in (`ink` False) -- possibly a box at a stem's tip, not a
    note (Brahms 5/1/5/0's staccato dot): left unresolved. The control can fail: with the box given an oval, the rule takes it."""
    w, heads, verts, held, cross, strokes = _window("ends_never_no_oval_litolff_4_1_7_4_18")
    got = PS.read(heads, verts, held, crossers=cross, strokes=strokes)["heads"][w["head"]]
    # r24: Sean 2026-11-25 (tile 5) -- the head here is an "ff", not a notehead; it must stay unresolved (r24: `stroke_read_other_way`)
    assert got["state"] == "two_voices" and got["how"] == "two_voices", got
    inked = [dict(h, ink=True) for h in heads]
    got = PS.read(inked, verts, held, crossers=cross, strokes=strokes)["heads"][w["head"]]
    assert got["how"] == PS.OTHER_STEM_HOW, got


# ── (3) a copy of a head filed with another staff ────────────────────────────────────────────────────────────────────────────────────────


class _Ev:
    def __init__(self, refusals):
        self._ref = refusals

    def refusals(self, q):
        return self._ref


def test_a_copy_on_another_staff_is_not_joined_by_the_old_cell_join(monkeypatch):
    monkeypatch.setenv(PS.ENV, "1")
    ab = SimpleNamespace(detail=dict(how=PS.COPY_HOW, note=PS.COPY_HOW, own_staff="staff/2/0/3"))
    r = SV._page_stem_abstained(_Ev([ab]), "obs:1")
    assert r is not None and r.reason == "page_stem_on_another_staff"
    monkeypatch.setenv(PS.ENV, "0")
    assert SV._page_stem_abstained(_Ev([ab]), "obs:1") is None
