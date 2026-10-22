"""ROADMAP 2.193 -- MISSING NATURALS (flag `OMR_NATURAL_CANDIDATE`, default OFF). STAGED GATHER (shared detector).

THE CAUSE (benchmarks/omr-one-ink-one-mark-2026-10/FINDINGS.md section 2.193): see there. In one line: `YoloDetector.detect` keeps ONE class per
anchor (the argmax, ultralytics `multi_label=False`) and only above the 0.25 floor, so a natural that scores below the floor, or below a
flat/sharp on the same anchor, is not in the output at all -- and rule 6 (choose only among the detector's candidates) then leaves the ink wrong.

THE CHANGE: for an accidental box the detector DID draw (flat/sharp/double...), keep the best NATURAL score any anchor over that same ink gave
(IoU >= `IOU_MIN` with the box, any best class), when it is at least `LOWER_BOUND`, as `SymbolDetection.natural_score`. It is a CANDIDATE
for the 2.190 shape check, never a box (no ink without an accidental box gets one), and a choice made from it is GUESSED (blue)."""
from __future__ import annotations

import os

ENV = "OMR_NATURAL_CANDIDATE"

#: The class whose sub-floor score is kept.
CLASS_NAME = "accidentalnatural"

#: The same-ink overlap (a convention checked on crops by 2.185 / `one_ink.ONE_INK_IOU_MIN`, restated here because this module is shared).
IOU_MIN = 0.5

#: The lowest natural score kept as a candidate. SET FROM THE MEASUREMENT in FINDINGS 2.193 (CLAUDE section 4: a cut-off tuned on two plates may
#: only NARROW -- a candidate that the shape reader still has to confirm, written GUESSED).
LOWER_BOUND = 0.05


def enabled() -> bool:
    """`OMR_NATURAL_CANDIDATE`, default OFF (ROADMAP 2.193)."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")
