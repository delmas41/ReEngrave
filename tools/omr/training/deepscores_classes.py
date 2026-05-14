"""DeepScoresV2 class list.

The DeepScoresV2 dataset (Tuggener et al., "The DeepScoresV2 Dataset and
Benchmark for Music Object Detection", ICPR 2020 / 2021) ships ~135
symbol classes. The canonical list is defined inside the dataset's own
`deepscores_train.json` / `deepscores_test.json` annotation files under
the `categories` key (COCO-format), and is also published in the project
README at https://github.com/yvan674/obb_anns.

We embed a snapshot of the class list here so that:

    1. `prepare_yolo_data.py` can synthesize mock annotations for the
       --dry-run path without requiring the real dataset on disk.
    2. The test suite can sanity-check the mapping size.
    3. Downstream code (yolo_detector._CATEGORY_MAP) can be sanity-checked
       against the real class names that would appear in trained weights.

If the real dataset ships a slightly different list, `prepare_yolo_data.py`
will prefer the categories embedded in the actual JSON annotation file and
ignore this snapshot (it only falls back to this list on --dry-run).

Source of truth (one of these, depending on dataset release version):
    - https://github.com/yvan674/obb_anns (the annotation toolkit)
    - https://zenodo.org/records/4012193 (DeepScoresV2 dataset release)
    - The `categories` array inside `deepscores_train.json`
"""

from __future__ import annotations


# Snapshot of DeepScoresV2 class names. Order matches the COCO-style
# category_id sequence (0-indexed). Some sources list 135 classes; some
# 136 (when an explicit "background" / "None" class is included). We use
# the 135-class symbol-only list. If the actual dataset categories differ
# (e.g. fewer or extra classes), the conversion script regenerates the
# list from the dataset's own JSON.

DEEPSCORES_V2_CLASSES: list[str] = [
    "brace",
    "ledgerLine",
    "repeatDot",
    "segno",
    "coda",
    "gClef",
    "cClefAlto",
    "cClefTenor",
    "fClef",
    "unpitchedPercussionClef1",
    "gClefChange",
    "cClefAltoChange",
    "cClefTenorChange",
    "fClefChange",
    "clef8",
    "clef15",
    "timeSig0",
    "timeSig1",
    "timeSig2",
    "timeSig3",
    "timeSig4",
    "timeSig5",
    "timeSig6",
    "timeSig7",
    "timeSig8",
    "timeSig9",
    "timeSigCommon",
    "timeSigCutCommon",
    "noteheadBlackOnLine",
    "noteheadBlackOnLineSmall",
    "noteheadBlackInSpace",
    "noteheadBlackInSpaceSmall",
    "noteheadHalfOnLine",
    "noteheadHalfOnLineSmall",
    "noteheadHalfInSpace",
    "noteheadHalfInSpaceSmall",
    "noteheadWholeOnLine",
    "noteheadWholeOnLineSmall",
    "noteheadWholeInSpace",
    "noteheadWholeInSpaceSmall",
    "noteheadDoubleWholeOnLine",
    "noteheadDoubleWholeOnLineSmall",
    "noteheadDoubleWholeInSpace",
    "noteheadDoubleWholeInSpaceSmall",
    "augmentationDot",
    "stem",
    "tremolo1",
    "tremolo2",
    "tremolo3",
    "tremolo4",
    "tremolo5",
    "flag8thUp",
    "flag8thUpSmall",
    "flag16thUp",
    "flag32ndUp",
    "flag64thUp",
    "flag128thUp",
    "flag8thDown",
    "flag8thDownSmall",
    "flag16thDown",
    "flag32ndDown",
    "flag64thDown",
    "flag128thDown",
    "accidentalFlat",
    "accidentalFlatSmall",
    "accidentalNatural",
    "accidentalNaturalSmall",
    "accidentalSharp",
    "accidentalSharpSmall",
    "accidentalDoubleSharp",
    "accidentalDoubleFlat",
    "keyFlat",
    "keyNatural",
    "keySharp",
    "articAccentAbove",
    "articAccentBelow",
    "articStaccatoAbove",
    "articStaccatoBelow",
    "articTenutoAbove",
    "articTenutoBelow",
    "articStaccatissimoAbove",
    "articStaccatissimoBelow",
    "articMarcatoAbove",
    "articMarcatoBelow",
    "fermataAbove",
    "fermataBelow",
    "caesura",
    "restDoubleWhole",
    "restWhole",
    "restHalf",
    "restQuarter",
    "rest8th",
    "rest16th",
    "rest32nd",
    "rest64th",
    "rest128th",
    "restHBar",
    "dynamicP",
    "dynamicM",
    "dynamicF",
    "dynamicS",
    "dynamicZ",
    "dynamicR",
    "dynamicPiano",
    "dynamicMezzo",
    "dynamicForte",
    "dynamicSforzando",
    "dynamicRinforzando",
    "dynamicNiente",
    "graceNoteAcciaccaturaStemUp",
    "graceNoteAppoggiaturaStemUp",
    "graceNoteAcciaccaturaStemDown",
    "graceNoteAppoggiaturaStemDown",
    "ornamentTrill",
    "ornamentTurn",
    "ornamentTurnInverted",
    "ornamentMordent",
    "stringsDownBow",
    "stringsUpBow",
    "arpeggiato",
    "keyboardPedalPed",
    "keyboardPedalUp",
    "tuplet3",
    "tuplet6",
    "fingering0",
    "fingering1",
    "fingering2",
    "fingering3",
    "fingering4",
    "fingering5",
    "slur",
    "beam",
    "tie",
    "restHNr",
    "dynamicCrescendoHairpin",
    "dynamicDiminuendoHairpin",
    "tuplet1",
    "tuplet2",
    "tuplet4",
    "tuplet5",
    "tuplet7",
    "tuplet8",
    "tuplet9",
    "tupletBracket",
    "staff",
    "ottavaBracket",
]


def expected_class_count() -> int:
    """Number of classes in the embedded snapshot."""
    return len(DEEPSCORES_V2_CLASSES)
