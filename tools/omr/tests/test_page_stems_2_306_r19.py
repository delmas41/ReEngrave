"""ROADMAP 2.306 r19 -- making the page stem reader fit to switch on (STAGED; `OMR_PAGE_STEMS`, `OMR_STACK_TWO_HEADS`,
`OMR_STRING_STOPS_OWN_VALUE`, all default OFF). Controls are REAL marks, cut from gathers of the batch-4 pages, each shown failing with its rule
off (CLAUDE rule 7).

(c) A DOT BELONGS TO THE HEAD IT IS PRINTED BESIDE, ON A STRING STAFF (Sean 2026-11-21, page-facts; his r18 tile 1 = Brahms 5/1/10/7, "two dotted
quarters, and at the bottom there is a quarter note that's not dotted"). Batch 4, Brahms 5/1/9/7 (second violins, bar 43): Bb5 and D5 dotted, the
low D4 has no dot; the string-stop reading stood aside (the D5 is boxed twice, once as a whole-class box) and the one-value rule handed the top
head's dot to the D4, written PLAIN. Now the stem admits both lengths and is held (rule 8); never on a wind, brass or unknown staff, never for a
box at a dotted head's own place.
"""
import json
import os
from types import SimpleNamespace

import pytest

from tools.omr.staged import staff_family as SF
from tools.omr.staged.adjudicators import stem_value as SV

HERE = os.path.dirname(__file__)
DOTS = os.path.join(HERE, "fixtures", "page_stems_2_306_r19_string_dots.json")
SEAN = os.path.join(HERE, "fixtures", "strings_mixed_2_306.json")


def _members(heads):
    out = []
    for h in heads:
        if h["outcome"] not in ("decided", "narrowed"):
            continue
        opts = [tuple(o) for o in h["options"]]
        box = tuple(h["box"])
        out.append(SimpleNamespace(key=h["key"], sub=h["key"], whole_class=h.get("whole_class", False),
                                   decided=h["outcome"] == "decided" and len(opts) == 1, read=bool(opts), options=opts,
                                   box=box, cy=box[1] + box[3] / 2.0))
    return out


def _stays(heads, family, monkeypatch):
    monkeypatch.setattr(SV, "_staff_family", lambda ev, cell: {"family": family, "source": "test"})
    ev = SimpleNamespace(subject=SimpleNamespace(at=lambda kind: None))
    ms = _members(heads)
    return SV._string_dot_stays_its_own(ev, ms, ms)


@pytest.fixture
def strings_on(monkeypatch):
    monkeypatch.setenv(SF.ENV, "1")


def test_c_the_low_d4_with_no_dot_keeps_its_own_length_on_a_string_stem(strings_on, monkeypatch):
    heads = json.load(open(DOTS))["c_brahms_5_1_9_7"]["heads"]
    assert _stays(heads, SF.STRINGS, monkeypatch)


def test_seans_own_chord_the_same(strings_on, monkeypatch):
    heads = json.load(open(SEAN))["chords"]["brahms_5_1_10_7"]["heads"]
    assert _stays(heads, SF.STRINGS, monkeypatch)


def test_never_on_a_wind_brass_or_unknown_staff_nor_with_the_flag_off(monkeypatch):
    heads = json.load(open(DOTS))["c_brahms_5_1_9_7"]["heads"]
    monkeypatch.setenv(SF.ENV, "1")
    for fam in (SF.WOODWIND, SF.BRASS, SF.UNKNOWN, SF.OTHER):
        assert not _stays(heads, fam, monkeypatch), fam
    monkeypatch.setenv(SF.ENV, "0")
    assert not _stays(heads, SF.STRINGS, monkeypatch)


def test_never_for_a_box_at_a_dotted_heads_own_place(strings_on, monkeypatch):
    """One head read twice: the undotted box stands where the dotted head stands. The control can fail: moved to the D4's place it is caught."""
    heads = json.loads(json.dumps(json.load(open(DOTS))["c_brahms_5_1_9_7"]["heads"]))
    dotted = next(h for h in heads if h["options"] == [[1.0, 0, 1]])
    keep = [dotted] + [dict(h, box=list(dotted["box"])) for h in heads if h is not dotted and h["outcome"] == "decided"]
    assert not _stays(keep, SF.STRINGS, monkeypatch)
    low = next(h for h in heads if h["key"].endswith("/7"))
    assert _stays([dotted, low], SF.STRINGS, monkeypatch)
