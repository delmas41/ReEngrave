"""ROADMAP 2.306 batch-2 r2 -- the page stem reader (`OMR_PAGE_STEMS`, STAGED GATHER), faults read against the print on the batch-2 measure.

Controls are REAL page-map strokes and head claims from the batch-2 ON gathers (`fixtures/batch2_r2_page_stems.json`, cut by the lane from
`out/lane-report/batch-2/work/<plate>.on.gathered.record.json`); each fails with its rule switched off.

* Litolff 2/1/0/13 (fault 4): the flute's two half notes C6 and E6 on one down stem. The C6 read three strokes -- its stem down at the left and two
  uprights at the right that are the E6 ring's right side (their top ends stop at the E6) -- so it read `two_candidates`, joined no stem and its value
  was dropped. Rule: a stroke whose far end stops at another head is that head's outline, never this head's stem (`drop_outlines`).
* Brahms 5/1/10/7 (fault 1, Sean's chord: "two dotted quarters, and at the bottom there is a quarter note that's not dotted"): a fourth box (read G4)
  drawn over the bare stem below the B4. The only ink centred in it is a sliver one stem wide, which the contact pass took as the box's own head
  ink and so joined the box to the chord's stem. Rule: a piece no wider than a stem is stem ink, never a head's own (`stem_thin`). (A wider rule
  -- a box whose only ink is another head's oval reaches no stem -- was built and WITHDRAWN: it refused Sean's r10 tile 8, a real chord head.)
"""
import json
import os

import pytest

from tools.omr.staged import page_stems as PS

FX = os.path.join(os.path.dirname(__file__), "fixtures", "batch2_r2_page_stems.json")


def _fx(name):
    with open(FX) as f:
        d = json.load(f)[name]
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in d["strokes"].items()}
    heads = [dict(h, box=tuple(h["box"])) for h in d["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in d["verts"]]
    cross = [dict(c, box=tuple(c["box"])) for c in d["cross"]]
    held = {int(k): v for k, v in d["held"].items()}
    return heads, verts, cross, held, strokes


def _read(name):
    heads, verts, cross, held, strokes = _fx(name)
    return heads, PS.read(heads, verts, held, crossers=cross, strokes=strokes)


def _by_member(heads, res, key):
    h = next(h for h in heads if key in h["members"])
    return res["heads"][h["id"]]


def test_the_flutes_c6_takes_its_own_down_stem_not_the_upper_rings_side():
    heads, res = _read("litolff_2_1_0_13")
    r = _by_member(heads, res, "glyph/2/1/0/13/3")
    assert r["state"] == "one" and r["direction"] == "down"
    assert r["stroke"] == _by_member(heads, res, "glyph/2/1/0/13/5")["stroke"]     # the E6's stem: one chord on one stem


def test_control_without_the_outline_rule_the_c6_reads_two_candidates(monkeypatch):
    monkeypatch.setattr(PS, "drop_outlines", lambda h, cs, heads, vbox: cs)
    heads, res = _read("litolff_2_1_0_13")
    r = _by_member(heads, res, "glyph/2/1/0/13/3")
    assert r["state"] == "two" and r["how"] == "two_candidates"


def test_drop_outlines_only_narrows():
    heads, verts, cross, held, strokes = _fx("litolff_2_1_0_13")
    vb = {int(v["ord"]): v for v in verts}
    c6 = next(h for h in heads if "glyph/2/1/0/13/3" in h["members"])
    every_one_an_outline = [dict(stroke=o, direction="up") for o in (3875, 3904)]
    assert PS.drop_outlines(c6, every_one_an_outline, heads, vb) == every_one_an_outline


def test_a_sliver_one_stem_wide_is_stem_ink_never_a_heads():
    heads, verts, cross, held, strokes = _fx("brahms_5_1_10_7")
    box18 = next(h for h in heads if "glyph/5/1/10/7/18" in h["members"])
    assert PS.stem_thin(strokes[5600], box18)            # 3 px wide under the B4: the stem between the B4 and its ledger lines
    assert not PS.stem_thin(strokes[5528], box18)        # the B4's own oval


def test_the_chords_own_heads_still_stand_on_the_stem():
    heads, res = _read("brahms_5_1_10_7")
    assert _by_member(heads, res, "glyph/5/1/10/7/8")["state"] == "one"
    assert _by_member(heads, res, "glyph/5/1/10/7/10")["state"] == "one"
    assert _by_member(heads, res, "glyph/5/1/10/7/18")["state"] == "none"


# ── fault 5: Brahms 5/0/11/3 (second violins?), the bar's last eighth: stem down at the left, flag at its foot -- the detector boxed the note
#    `accidentalFlat` (glyph/5/0/11/3/29), the box held the note's own stem (page stroke 3648), the eighth joined no stem and the bar lost its
#    last two notes. Page px from the batch-2 ON gather of Brahms p5 (glyph boxes and the 2.290 head claims as filed).
EIGHTH_AS_FLAT_BOX = (3036.0, 3084.0, 3072.0, 3192.0)          # glyph/5/0/11/3/29, accidentalFlat
EIGHTH_HEAD_OVAL_PIECE = (3047.0, 3079.0, 3067.0, 3113.0)      # page stroke 3667, claimed by the head claim of glyph/5/0/11/3/13
REAL_FLAT_BOX = (2742.0, 3030.0, 2772.0, 3105.0)               # glyph/5/0/11/3/0, the flat before the bar's G-flat
QUARTER_HEAD_PIECE = (2623.0, 3091.0, 2654.0, 3128.0)          # page stroke 2975, the bar's first head (E-flat4)


def test_an_accidental_box_over_a_heads_own_oval_holds_nothing():
    heads = [EIGHTH_HEAD_OVAL_PIECE, QUARTER_HEAD_PIECE]
    assert PS.box_holds_a_head(EIGHTH_AS_FLAT_BOX, heads)


def test_control_a_real_flat_beside_its_head_still_holds_its_strokes():
    assert not PS.box_holds_a_head(REAL_FLAT_BOX, [EIGHTH_HEAD_OVAL_PIECE, QUARTER_HEAD_PIECE])
    assert not PS.box_holds_a_head(EIGHTH_AS_FLAT_BOX, [])      # the control can fail: without the head claim the box holds as before
