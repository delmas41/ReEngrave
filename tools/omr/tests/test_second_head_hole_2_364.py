"""ROADMAP 2.364 (flag `OMR_SECOND_HEAD_HOLE`, default OFF): the second head of a hollow third, read by its hole.

Controls built from REAL judged pixels (CLAUDE rule 7): `data/second_head_hole/` holds 87 small crops of the page raster (Litolff and
Brahms, staff lines in) round a written head Sean judged, with the bar's five lines, the written head's box, the CV stems the production
stem call returns on that cell and every head box on the page near it. `manifest.json` names the sheet, the glyph and his words:

  * YES / YES@box -- he read two heads on that stem (halfnote-chords sheets, the hole-rule sheets, his good refused-rescue boxes);
  * NO -- he read a single half, a unison, a bass clef, or "a box around a space in the staff";
  * NO@box -- the refused-rescue boxes he called a staff line, a ledger line, a dynamic, the top of an f, or a sliver of the written head.

Every NO is refused; every YES this reader keeps is listed by name (21 of 41) and its kept ring overlaps his box where he drew one; the
20 known misses are listed with what stops them (left as misses, not chased). Each guard is shown to FAIL on the judged mark it
guards when it is switched off.
"""
import json
import os

import numpy as np
import pytest

from tools.omr.staged import second_head_hole as SHH

DATA = os.path.join(os.path.dirname(__file__), "data", "second_head_hole")
MANIFEST = json.load(open(os.path.join(DATA, "manifest.json")))
BY_NAME = {m["file"][:-4]: m for m in MANIFEST}

#: Sean's real second heads this reader keeps (his words in the manifest)
KEPT_REAL = ("lc03_good_box lc06_good_box lc10_good_box lc16_good_box lc17_good_box lc19_good_box lc21_good_box lita02_lost_head "
             "lita18_lost_head hs04_two_heads hs08_two_heads hs09_two_heads hs10_two_heads hs12_two_heads hs14_two_heads hs15_two_heads "
             "hs20_two_heads v2_02_two_heads v2_04_two_heads v2_09_two_heads v2_12_two_heads").split()
#: his real second heads it does not keep, and what stops them (known misses, ROADMAP 2.364)
KNOWN_MISSES = {
    # the written head shows no closed hole (hatched / opened slit): no evidence the written head is hollow
    "lita03_lost_head": "no own hole", "hs18_two_heads": "no own hole", "hs21_two_heads": "no own hole",
    "v2_07_two_heads": "no own hole", "v2_10_two_heads": "no own hole",
    # the production stem call finds no stem at the written head
    "hs02_two_heads": "no stem", "hs03_two_heads": "no stem",
    # another head box already stands on the second head (refused later in ADJUDICATE: a dynamic letter, a stacked duplicate, a whole)
    "lc12_good_box": "box exists", "v2_03_two_heads": "box exists", "v2_08_two_heads": "box exists", "v2_11_two_heads": "box exists",
    # no hole one space along in the column (hatched slit pieces off the head's centre, a written head between two holes, Brahms)
    "braa05_lost_head": "no hole", "hs11_two_heads": "no hole", "hs22_two_heads": "no hole", "hs23_two_heads": "no hole",
    "v2_01_two_heads": "no hole", "v2_05_two_heads": "no hole", "litb08_lost_head": "no hole", "lc04_good_box": "no hole",
    "lc07_good_box": "no hole",
}


def _run(name):
    m = BY_NAME[name]
    z = np.load(os.path.join(DATA, m["file"]))
    ink = np.unpackbits(z["ink"], axis=1)[:, :int(z["shape"][1])].astype(bool)
    kept, _refused = SHH.second_heads(ink, list(z["lines"]), [list(z["head"])], [list(s) for s in z["stems"]],
                                      [list(s) for s in z["seen"]])
    return m, kept


def _overlaps(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _invented(name):
    m, kept = _run(name)
    if m["expect"] == "NO":
        return bool(kept)
    if m["expect"] == "NO@box":
        return any(_overlaps(k["box"], m["box"]) for k in kept)
    raise AssertionError(name)


NOS = sorted(n for n, m in BY_NAME.items() if m["expect"] in ("NO", "NO@box"))


def test_the_judged_set_is_whole():
    yes = {n for n, m in BY_NAME.items() if m["expect"].startswith("YES")}
    assert yes == set(KEPT_REAL) | set(KNOWN_MISSES)
    assert len(NOS) == 46


@pytest.mark.parametrize("name", NOS)
def test_no_head_invented_where_sean_read_none(name):
    assert not _invented(name), BY_NAME[name]["his_words"]


@pytest.mark.parametrize("name", KEPT_REAL)
def test_his_real_second_head_is_kept(name):
    m, kept = _run(name)
    assert kept, m["his_words"]
    if m["expect"] == "YES@box":
        assert any(_overlaps(k["box"], m["box"]) for k in kept)
    # the ring stops half-way to the written head: it never takes the written head's own hole
    for k in kept:
        assert abs(k["dy_sp"]) >= SHH.THIRD_SP[0] and abs(k["dx_sp"]) <= SHH.COLUMN_SP


def _fails_without(monkeypatch, attr, value, names):
    for n in names:
        assert not _invented(n)
    monkeypatch.setattr(SHH, attr, value)
    return [n for n in names if _invented(n)]


def test_boxed_staff_space_guard_can_fail(monkeypatch):
    # Sean first sheet tile 19, "a box around a space in the staff": paper filling its box between two lines and two strokes
    assert _fails_without(monkeypatch, "BOXED_FILL", 1.1, ["hs19_not_a_head"]) == ["hs19_not_a_head"]


def test_column_rule_can_fail(monkeypatch):
    # Brahms sheet A tile 18, a single half with tremolo slashes: the paper between the slashes and the stem, off the head's column
    assert _fails_without(monkeypatch, "COLUMN_SP", 2.0, ["braa18_single"]) == ["braa18_single"]


def test_one_space_floor_can_fail(monkeypatch):
    # pieces of a single head's own hatched slit stand ~0.7 along and across from the piece the head is placed by
    names = ["braa03_single", "hs17_single_half_note", "lita15_single"]
    assert _fails_without(monkeypatch, "THIRD_SP", (0.3, 1.45), names) == names


def test_one_space_ceiling_can_fail(monkeypatch):
    names = ["lita09_single", "hs01_unison_half_note"]
    assert _fails_without(monkeypatch, "THIRD_SP", (0.75, 2.5), names) == names


def test_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv(SHH.ENV, raising=False)
    assert SHH.enabled() is False
    monkeypatch.setenv(SHH.ENV, "1")
    assert SHH.enabled() is True


def test_flag_off_gather_never_calls_the_reader():
    # the one call site is gated by the flag (OFF: the record and the file are unchanged)
    import inspect
    from tools.omr.staged import gather as G
    src = inspect.getsource(G)
    assert src.count("gather_second_head_hole(log, cells, local, detections") == 1
    i = src.index("gather_second_head_hole(log, cells, local, detections, progress=progress, pws=pws)")
    assert "if _SHH.enabled():" in src[i - 200:i]


def test_written_blue_under_its_own_reason():
    from tools.omr.staged import export as E

    class Rec:
        def verdict(self, q, sub):
            from tools.omr.staged.record import Q
            if q == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
                return {"outcome": "narrowed", "reason": "second_head_hole"}
            return None

    g = E.claim_guess_of(Rec(), "glyph/0/0/0/0/0")
    assert g is not None and g["rule"] == "second_head_hole" and len(g["candidates"]) == 2
