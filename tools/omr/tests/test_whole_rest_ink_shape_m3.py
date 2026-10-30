"""ROADMAP 2.230 m3 (flag `OMR_WHOLE_REST_HANGS`): a restWhole is judged by its OWN INK (the stroke owner's block test), never by where it
stands in the staff (a displaced rest in a multi-voice bar is real). Contested with an arc -> NARROWED (blue); only a shape that can
never be a block (vertical, curve) is refused; a blob or horizontal piece a little tall stays (real rests fused with a line stub)."""
from types import SimpleNamespace

from tools.omr.staged.adjudicators import family_precision as FP

KEY = "glyph/1/0/0/0/5"


def _ev(boxes, strokes):
    v = SimpleNamespace(detail={"boxes": boxes, "strokes": strokes})
    subj = SimpleNamespace(at=lambda kind: "cell", to_key=lambda: KEY)
    return SimpleNamespace(subject=subj, verdict=lambda q, subject=None: v)


def _stroke(why, fam="arc"):
    return ["contested", None, [], "", [[KEY, "whole_rest", "restWhole", "clear", why, "cover"],
                                       ["glyph/1/0/0/0/4", fam, "tie", "clear", "thin_line", "cover"]]]


def _row():
    return SimpleNamespace(id="row1")


def test_contested_with_an_arc_is_narrowed_not_refused():
    ev = _ev({KEY: ["contested", [[21, "contested", None, "whole_rest_block"]]]},
             {"21": _stroke("whole_rest_block:kind=horizontal len=1.65")})
    r = FP._whole_rest_ink_not_a_block_refusal(ev, _row(), {})
    assert r is not None and r.reason == "claim_narrowed:arc"


def test_a_vertical_is_refused():
    st = ["refused_claims", None, [], "shape", [[KEY, "whole_rest", "restWhole", "no", "not_a_whole_rest_block:kind=vertical len=0.9", "cover"]]]
    ev = _ev({KEY: ["refused", [[3, "refused_claims", None, "not_a_whole_rest_block"]]]}, {"3": st})
    r = FP._whole_rest_ink_not_a_block_refusal(ev, _row(), {})
    assert r is not None and r.reason == "whole_rest_ink_not_a_block"


def test_a_slightly_tall_blob_stays():
    st = ["refused_claims", None, [], "shape", [[KEY, "whole_rest", "restWhole", "no", "not_a_whole_rest_block:kind=blob h=1.04", "cover"]]]
    ev = _ev({KEY: ["refused", [[3, "refused_claims", None, "not_a_whole_rest_block"]]]}, {"3": st})
    assert FP._whole_rest_ink_not_a_block_refusal(ev, _row(), {}) is None


def test_no_verdict_is_no_answer():
    ev = SimpleNamespace(subject=SimpleNamespace(at=lambda k: "cell", to_key=lambda: KEY), verdict=lambda q, subject=None: None)
    assert FP._whole_rest_ink_not_a_block_refusal(ev, _row(), {}) is None
