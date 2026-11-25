"""ROADMAP 2.347 -- a head box drawn on an accidental's ink is not a note (STAGED ADJUDICATE `notehead_precision._on_an_accidentals_ink`,
flag `OMR_HEAD_BOX_ON_ACCIDENTAL_INK`, default OFF).

THE RULE, as a musician says it: a sharp the detector boxed as a head is not a note; the real head stands beside it. NEVER: a real head standing beside
its accidental, however much their boxes overlap, stays a note.

CONTROLS FROM REAL ROWS (CLAUDE rule 7): the entries below are the page ledger's own `ink_consult` entries from the 20261123-night record's
`stroke_owner` verdicts. Brahms glyph/6/1/6/0/14 is the sharp boxed as a head and written E5 (95.5% of its ink the accidental's; the one stroke it owned
is a bar end); it fails with the flag off. Brahms glyph/6/1/7/4/9, Litolff glyph/4/1/0/4/5 and 14/1/0/8/4 are real heads whose boxes overlap an
accidental claim by 48% / 41% / 48% of their ink: they must stay. The 19 boxes on a sharp (each cropped and looked at, the real head standing
separately to its right) all hold 50.2%-97.3% accidental ink.
"""
import os
from types import SimpleNamespace

from tools.omr.staged import page_accidental_ink as PAI
from tools.omr.staged.adjudicators import notehead_precision as NP

ENV = NP.HEAD_BOX_ON_ACCIDENTAL_INK_ENV
BOX = SimpleNamespace(id="obs:box", value=["noteheadBlackInSpace", 0, 0, 10, 10])


def _entry(share, owns=True, **kw):
    return {"by": PAI.OWNER, "share": share, "ink": 1.3, "strokes": [53, 55, 57], "owns": owns, "tier": 2, "by_tier": 0, "area": True, "also": [],
            "held_all": share, "shares": {PAI.OWNER: share}, **kw}


SHARP_BOXED_AS_HEAD = _entry(0.955)                      # Brahms glyph/6/1/6/0/14
REAL_HEADS = [_entry(0.478), _entry(0.414), _entry(0.479)]    # Brahms 6/1/7/4/9, Litolff 4/1/0/4/5, Litolff 14/1/0/8/4


def _ask(entry, flag):
    saved = {k: os.environ.get(k) for k in (ENV, PAI.FUSED_ENV)}
    os.environ[PAI.FUSED_ENV] = "1"
    if flag is None:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = flag
    try:
        return NP._on_an_accidentals_ink(SimpleNamespace(entry=entry, verdict_id="vrd:so"), BOX)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_default_off_and_the_control_fails_with_the_flag_off():
    assert NP.head_box_on_accidental_ink_enabled() is False or ENV in os.environ
    assert _ask(SHARP_BOXED_AS_HEAD, None) is None           # old code: the box that owns one stroke survives
    assert _ask(SHARP_BOXED_AS_HEAD, "0") is None


def test_a_sharp_boxed_as_a_head_is_refused_by_the_accidentals_claim():
    r = _ask(SHARP_BOXED_AS_HEAD, "1")
    assert r is not None and r.value is True and r.reason == "claimed_by:page_claim"


def test_never_a_real_head_beside_its_accidental():
    for e in REAL_HEADS:
        assert _ask(e, "1") is None


def test_never_when_the_accidental_alone_does_not_hold_half():
    # the accidental plus a barline hold 0.6 together; neither a head touching a barline nor its accidental is refused for owning a stroke
    e = _entry(0.25, held_all=0.6, shares={PAI.OWNER: 0.25, "barline": 0.35})
    assert _ask(e, "1") is None


def test_never_a_box_that_owns_nothing_changes():
    # the 2.336 rule for a box owning no stroke is unchanged by the flag
    e = _entry(0.569, owns=False, held_all=0.95, shares={"barline": 0.381, PAI.OWNER: 0.569})
    assert _ask(e, "0") is not None and _ask(e, "1") is not None


def test_held_by_earlier_records_what_the_box_owns():
    from tools.omr.staged.adjudicators import ink_consult as IC
    tiers = [["head"], ["accidental"]]
    strokes = [(1, 1.0, 0.9, "decided", "accidental_ink", ["x"]), (2, 1.0, 0.06, "decided", "head", ["b"]), (3, 1.0, 0.04, "decided", "head", ["other"])]
    out = IC.held_by_earlier([("b", "head", strokes)], tiers, area_families=["accidental_ink"])
    assert out["b"]["owns"] is True and abs(out["b"]["owned_ink"] - 0.06) < 1e-9
