"""The page truth has to land on the ink, and the ways it did not are pinned.

Both real errors this file guards were caught the same way — the symbol COUNTS
agreed almost exactly while nothing matched positionally, which is the signature
of a frame error and never of a recognition result.
"""

from __future__ import annotations

import pytest

from tools.omr.page_truth import (
    _EXPAND_TO_GLYPHS,
    NOT_SCORED,
    SCORED_CLASSES,
    glyph_box_templates,
    symbols_in_svg,
)
from tools.omr.score_reading import (
    CV_SOURCED,
    confusions,
    detector_family,
    match,
)

verovio = pytest.importorskip("verovio", reason="page truth needs verovio")


# --------------------------------------------------------------------------
# Frame
# --------------------------------------------------------------------------

_SVG = """<svg width="800px" height="1000px">
 <defs><g id="E0A4-x"><path transform="scale(1,-1)" d="M0 0"/></g></defs>
 <svg class="definition-scale" viewBox="0 0 20000 25000">
  <g class="page-margin" transform="translate(500, 500)">
   <g id="n1" class="note"><g id="bbox-n1" class="note bounding-box">
     <rect x="1000" y="900" height="200" width="240" fill="transparent" /></g>
    <g class="notehead"><use xlink:href="#E0A4-x" transform="translate(1000, 1000)" /></g>
   </g>
  </g>
 </svg>
</svg>"""


def test_the_page_margin_translate_is_applied():
    """⚠️ Verovio wraps the page in `<g class="page-margin" transform=...>` and
    every coordinate below it is inside that translate. Missing it put the whole
    truth a constant 62.5 px off at 300 dpi — against a 22.5 px staff space, so
    NOTHING matched at any tolerance while noteheads counted 259 against 259.
    """
    boxed, glyphs = symbols_in_svg(_SVG, px_per_css=300 / 96)
    k = (300 / 96) / (20000 / 800)          # internal units -> image px
    assert boxed and boxed[0]["family"] == "notehead"
    assert boxed[0]["x"] == pytest.approx((1000 + 500) * k)
    assert boxed[0]["y"] == pytest.approx((900 + 500) * k)
    assert glyphs[0]["x"] == pytest.approx((1000 + 500) * k)


def test_without_the_margin_the_truth_would_be_a_constant_offset_out():
    """The control for the test above: it is a translation, not a scale."""
    boxed, _ = symbols_in_svg(_SVG, px_per_css=300 / 96)
    k = (300 / 96) / (20000 / 800)
    assert boxed[0]["x"] - 1000 * k == pytest.approx(500 * k)


# --------------------------------------------------------------------------
# Glyph boxes
# --------------------------------------------------------------------------


def test_a_glyph_box_is_calibrated_from_a_single_glyph_rect():
    rects = [("accid", {"x": 10.0, "y": 4.0, "w": 6.0, "h": 20.0})]
    glyphs = [{"smufl": "E260", "x": 12.0, "y": 14.0}]
    tpl = glyph_box_templates(rects, glyphs)
    assert tpl["E260"] == {"dx": -2.0, "dy": -10.0, "w": 6.0, "h": 20.0}


def test_a_rect_holding_two_glyphs_calibrates_nothing():
    """A `keySig` rect spans several accidentals, so it says nothing about any
    one of them. Calibrating from it would invent a box."""
    rects = [("keySig", {"x": 0.0, "y": 0.0, "w": 100.0, "h": 40.0})]
    glyphs = [{"smufl": "E260", "x": 10.0, "y": 20.0},
              {"smufl": "E260", "x": 40.0, "y": 20.0}]
    assert glyph_box_templates(rects, glyphs) == {}


def test_the_anchor_is_not_assumed_to_be_the_centre():
    """⚠️ The measured error this guards: SMuFL puts a flat's origin at the
    staff position it alters, not at its middle. Treating the anchor as a centre
    put the key-signature truth 0.59 staff spaces high and scored a correctly
    read signature at F1 0.078 — it went to 0.990 on calibration.
    """
    rects = [("accid", {"x": 0.0, "y": 0.0, "w": 10.0, "h": 40.0})]
    glyphs = [{"smufl": "E260", "x": 0.0, "y": 30.0}]     # anchor low in the box
    tpl = glyph_box_templates(rects, glyphs)["E260"]
    assert tpl["dy"] == -30.0, "the offset must come from the rect, not from h/2"


# --------------------------------------------------------------------------
# Group expansion
# --------------------------------------------------------------------------


def test_group_expansion_is_gated_by_the_smufl_block():
    """⚠️ Position alone leaks: these group boxes sit flush against their
    neighbours. Measured on the Brahms fixture, selecting by position put 30
    time-signature digits inside `keySig` and 4 noteheads inside `dynam`.
    """
    for head, (_family, (lo, hi)) in _EXPAND_TO_GLYPHS.items():
        assert lo < hi
    assert _EXPAND_TO_GLYPHS["dynam"][1] == (0xE520, 0xE54F)
    assert not (_EXPAND_TO_GLYPHS["keySig"][1][0]
                <= 0xE086 <= _EXPAND_TO_GLYPHS["keySig"][1][1]), (
        "a time-signature digit must not be admissible as a key accidental")
    assert not (_EXPAND_TO_GLYPHS["dynam"][1][0]
                <= 0xE0A4 <= _EXPAND_TO_GLYPHS["dynam"][1][1]), (
        "a notehead must not be admissible as a dynamic letter")


def test_scored_and_unscored_classes_are_disjoint_and_reasoned():
    assert not (set(SCORED_CLASSES) & set(NOT_SCORED))
    assert all(v for v in NOT_SCORED.values()), "every exclusion needs a reason"


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def _t(family, x, y, w=10.0, h=10.0):
    return {"family": family, "x": x, "y": y, "w": w, "h": h}


def _d(family, cx, cy):
    return {"family": family, "class": family, "cx": cx, "cy": cy, "conf": 0.9}


def test_a_symbol_is_found_when_a_detection_of_its_family_is_near():
    m = match([_t("notehead", 0, 0)], [_d("notehead", 5, 5)], tol_px=2.0)
    assert m["per_family"]["notehead"]["matched"] == 1


def test_a_detection_of_another_family_does_not_count():
    m = match([_t("notehead", 0, 0)], [_d("rest", 5, 5)], tol_px=2.0)
    assert m["per_family"]["notehead"]["matched"] == 0


def test_one_detection_cannot_satisfy_two_symbols():
    m = match([_t("notehead", 0, 0), _t("notehead", 2, 0)],
              [_d("notehead", 5, 5)], tol_px=20.0)
    assert m["per_family"]["notehead"]["matched"] == 1


def test_beyond_the_tolerance_it_is_a_miss():
    m = match([_t("notehead", 0, 0)], [_d("notehead", 100, 100)], tol_px=2.0)
    assert m["per_family"]["notehead"]["matched"] == 0


def test_unscored_detections_are_reported_not_dropped():
    m = match([], [{"family": None, "class": "ledgerLine", "cx": 0, "cy": 0}],
              tol_px=1.0)
    assert m["unscored_detections"] == {"ledgerLine": 1}


# --------------------------------------------------------------------------
# Confusion — the diagnostic that says WHY a family is low
# --------------------------------------------------------------------------


def test_a_miss_with_nothing_there_reports_a_dash():
    c = confusions([_t("tie", 0, 0)], [], tol_px=5.0)
    assert c["tie"] == {"-": 1}


def test_a_miss_with_another_family_there_names_it():
    """Recall alone cannot separate "not seen" from "seen and called something
    else", and those need different fixes."""
    c = confusions([_t("tie", 0, 0)], [_d("slur", 5, 5)], tol_px=20.0)
    assert c["tie"] == {"slur": 1}


# --------------------------------------------------------------------------
# The detector-side vocabulary
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cls,family", [
    ("noteheadBlackOnLine", "notehead"),
    ("noteheadDoubleWholeInSpace", "notehead"),
    ("restQuarter", "rest"),
    ("accidentalFlat", "accidental"),
    ("keyFlat", "key_accidental"),
    ("timeSig4", "time_signature_digit"),
    ("clefG", "clef"),
    ("gClef", "clef"),
    ("dynamicF", "dynamic_letter"),
    ("flag8thUp", "flag"),
    ("augmentationDot", "augmentation_dot"),
])
def test_detector_classes_map_to_families(cls, family):
    assert detector_family(cls) == family


def test_a_hairpin_is_not_a_dynamic_letter():
    """`dynamicCrescendoHairpin` starts with `dynamic` and is a wedge. The
    prefix order is what keeps it out."""
    assert detector_family("dynamicCrescendoHairpin") is None
    assert detector_family("dynamicDiminuendoHairpin") is None


def test_pitch_is_not_scored_here():
    """`OnLine` and `InSpace` are one glyph at two staff positions — that is the
    note's PITCH, resolved from the staff grid, not a recognition question."""
    assert (detector_family("noteheadBlackOnLine")
            == detector_family("noteheadBlackInSpace"))


def test_cv_sourced_families_are_declared():
    assert set(CV_SOURCED) == {"beam", "barline"}
    assert all(v for v in CV_SOURCED.values())
