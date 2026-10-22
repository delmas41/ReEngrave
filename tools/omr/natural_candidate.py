"""ROADMAP 2.193 -- MISSING NATURALS (flag `OMR_NATURAL_CANDIDATE`, default ON). STAGED GATHER (shared detector).

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

#: What GATHER files: the best natural score over the ink when it is at least this (a record-size floor, so a later change of `LOWER_BOUND` needs
#: no re-gather as long as it stays at or above it).
STORE_FLOOR = 0.01

#: The lowest natural score ADJUDICATE accepts as a candidate. MEASURED, not tuned to a target (FINDINGS 2.193): on the frozen sample the natural
#: score over inks whose shape reads flat or sharp (non-natural by shape, where the detector offered no natural) has p90 = 0.074 (Litolff) /
#: 0.060 (Brahms), p50 = 0.005 / 0.003 -- 0.05 is the score above which fewer than ~15% / ~12% of such inks sit, i.e. the point at which the
#: natural channel says more than its ordinary noise on a non-natural ink. A convention-free cut-off set on two plates: by CLAUDE section 4 it may
#: only NARROW, so the shape reader must still call the ink a natural and the result is written GUESSED (blue).
LOWER_BOUND = 0.05


def enabled() -> bool:
    """`OMR_NATURAL_CANDIDATE`, default ON (ROADMAP 2.193, Sean 2026-10-22); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")
