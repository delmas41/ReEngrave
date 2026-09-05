"""The class space spells 32 glyphs twice; these pin which spelling wins.

The fault this guards is the one that has cost this project eight fixes: a
signal recognised correctly and dropped on the way out. A detection at class id
192 is a forte; `export._DYNAMIC_LETTER` knows `dynamicF` and not
`dynamicLetterF`, so before `class_aliases` that detection reached the exporter
and left no trace anywhere.
"""

from __future__ import annotations

import pytest

from tools.omr.class_aliases import (
    ALIASES,
    COARSER_THAN_CANONICAL,
    FINE_BLOCK_SIZE,
    canonical,
    canonicalize_names,
    fine_vocabulary,
    unaccounted,
    vocabulary,
)
from tools.omr.export import _DYNAMIC_LETTER
from tools.omr.rhythm import _intrinsic_notehead_duration, _tuplet_digit
from tools.omr.transcribe import articulation_kind
from tools.omr.yolo_detector import _class_name_to_category


def test_vocabulary_is_the_208_class_space():
    v = vocabulary()
    assert len(v) == 208
    # The boundary is a fact about the class space, not a slice: the fine
    # spelling of the dynamic letters is below it and the coarse one above.
    assert v[95] == "dynamicF"
    assert v[192] == "dynamicLetterF"
    assert FINE_BLOCK_SIZE == 136
    assert "dynamicF" in fine_vocabulary()
    assert "dynamicLetterF" not in fine_vocabulary()


def test_every_name_in_the_vocabulary_has_a_decision():
    """No coarse name may be left unclassified — that is a silent drop."""
    assert unaccounted(vocabulary()) == []


def test_a_novel_class_is_not_silently_accepted():
    """A future checkpoint with a wider class space must fail, not drop."""
    assert unaccounted(["noteheadTriangleUpBlackOnLine"]) == [
        "noteheadTriangleUpBlackOnLine"
    ]


def test_the_two_tables_are_disjoint():
    assert not (set(ALIASES) & set(COARSER_THAN_CANONICAL))


def test_every_alias_target_is_a_fine_spelling():
    """An alias must land on a name a consumer actually knows."""
    fine = fine_vocabulary()
    for coarse, target in ALIASES.items():
        assert target in fine, f"{coarse} -> {target} is not in the fine vocabulary"


def test_canonical_is_idempotent_and_leaves_fine_names_alone():
    for name in fine_vocabulary():
        assert canonical(name) == name
    for coarse in ALIASES:
        assert canonical(canonical(coarse)) == canonical(coarse)


# ---------------------------------------------------------------------------
# The point of the rename: the consumer now reads the coarse spelling.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "coarse,letter",
    [("dynamicLetterP", "p"), ("dynamicLetterM", "m"), ("dynamicLetterF", "f"),
     ("dynamicLetterS", "s"), ("dynamicLetterZ", "z"), ("dynamicLetterR", "r")],
)
def test_dynamic_letters_reach_the_exporter(coarse, letter):
    assert _DYNAMIC_LETTER.get(coarse) is None, "the coarse name is still unknown to export"
    assert _DYNAMIC_LETTER[canonical(coarse)] == letter


@pytest.mark.parametrize(
    "coarse,kind,above",
    [("articulationMarcatoAbove", "marcato", True),
     ("articulationMarcatoBelow", "marcato", False)],
)
def test_marcato_reaches_the_articulation_reader(coarse, kind, above):
    assert articulation_kind(coarse) is None
    assert articulation_kind(canonical(coarse)) == (kind, above)


def test_structural_aliases_get_a_category():
    for coarse in ("arpeggio", "tupleBracket", "legerLine"):
        assert _class_name_to_category(coarse) == "unknown"
        assert _class_name_to_category(canonical(coarse)) != "unknown"


def test_coarse_notehead_gets_a_duration():
    """`noteheadFullSmall` is a black head under the coarse spelling.

    Fixed in the consumer rather than by a rename — see the comment on
    `rhythm._NOTEHEAD_INTRINSIC`.
    """
    assert _intrinsic_notehead_duration("noteheadFullSmall") == (1.0, "quarter")


# ---------------------------------------------------------------------------
# What is deliberately NOT renamed, and why. These assert the ABSTENTION.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("digit", [f"numeral{d}" for d in range(10)] + ["numeral"])
def test_a_numeral_never_becomes_a_time_signature(digit):
    """The coarse vocabulary has ONE numeral class for time signatures, tuplet
    digits, fingerings and measure numbers. CLAUDE.md records what a spurious
    `timeSig4` costs: five fired on barline fragments and shipped a 2/4 page as
    common time, at 390 LilyPond bar-check failures against 164 for no meter.
    """
    assert canonical(digit) == digit
    assert _class_name_to_category(digit) != "time_sig_digit"
    assert digit in COARSER_THAN_CANONICAL


def test_a_sideless_articulation_is_not_given_a_side():
    """`articulationStaccato` states no side, and the side is checked against
    geometry downstream. Inventing one would be a measured change, not a rename.
    """
    for coarse in ("articulationAccent", "articulationStaccato", "articulationTenuto"):
        assert canonical(coarse) == coarse
        assert articulation_kind(coarse) is None
        assert coarse in COARSER_THAN_CANONICAL


def test_a_numberless_tuplet_is_not_read_as_a_triplet():
    assert canonical("tuple") == "tuple"
    assert _tuplet_digit("tuple") is None
    assert "tuple" in COARSER_THAN_CANONICAL


# ---------------------------------------------------------------------------
# The wiring.
# ---------------------------------------------------------------------------


def test_canonicalize_names_renames_only_the_aliases():
    raw = {95: "dynamicF", 192: "dynamicLetterF", 205: "tuple", 16: "timeSig4"}
    assert canonicalize_names(raw) == {
        95: "dynamicF",
        192: "dynamicF",   # renamed
        205: "tuple",      # coarser, deliberately left alone
        16: "timeSig4",
    }


def test_detector_canonicalizes_the_model_vocabulary(monkeypatch):
    """The rename happens where the model's own `names` are read, so no call
    site downstream has to know this file exists.

    Exercises `_ensure_loaded` itself rather than re-deriving what it should
    have done — `ultralytics` is imported inside that function, so the fake
    goes into `sys.modules` where the import will find it.
    """
    import sys
    import types

    from tools.omr.yolo_detector import YoloDetector

    class _FakeModel:
        def __init__(self, _path):
            self.names = {95: "dynamicF", 192: "dynamicLetterF", 205: "tuple"}

    fake = types.ModuleType("ultralytics")
    fake.YOLO = _FakeModel
    monkeypatch.setitem(sys.modules, "ultralytics", fake)

    det = YoloDetector("unused.pt")
    det._ensure_loaded()
    assert det._class_names[192] == "dynamicF", "the coarse spelling was not renamed"
    assert det._class_names[95] == "dynamicF"
    assert det._class_names[205] == "tuple", "a coarser name must be left alone"
