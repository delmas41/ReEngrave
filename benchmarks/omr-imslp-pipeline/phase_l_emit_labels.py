#!/usr/bin/env python3
"""Phase L — same CV-detected stem/beam labels as Phase K, but emitted
into prod-208 class slots that DSv2 dense does NOT populate.

Phase K used class IDs:
  41=stem, 121=beam, 207=barline

…which work as prod-208 class IDs but COLLIDED with the DSv2 dense
training data we mixed in. DSv2 uses its native 0-145 class space where
slot 41 means noteheadDoubleWholeOnLineSmall and slot 121 means
keyboardPedalUp. The training tried to make slot 41 fire on BOTH stems
(from catalog) AND noteheads (from DSv2) and collapsed to predicting
nothing on either. See PHASE_K_RESULTS.md.

Phase L moves to the prod-extended slots that DSv2 dense never
touches (146-207 range):

  stem    → 160  (prod model has a duplicate "stem" slot at 160,
                  in addition to the conflicting one at 41)
  beam    → 200  (prod model has a duplicate "beam" slot at 200,
                  in addition to the conflicting one at 121)
  barline → 207  (= "staff" in prod; unchanged from Phase K, already
                  in the DSv2-free range)

The training will see DSv2 labels in slots 0-145 and catalog labels in
slots 160/200/207 with zero overlap — clean class signal for each.

The emitter logic is otherwise identical to Phase K — same CV detector,
same XML count validation, same per-cell skipping rules. Only the
output class IDs change.

CLI:
  python3 benchmarks/omr-imslp-pipeline/phase_l_emit_labels.py \\
      --work beethoven-symphony-1 --edition imslp-52848 --mvt 1
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-imslp-pipeline"))

# Import Phase K (the heavy lifting) and override the three constants.
import phase_k_emit_labels as pk  # noqa: E402

# Override class IDs to DSv2-free prod-208 slots.
pk.CLASS_STEM = 160      # was 41 — moved to prod's duplicate-stem slot
pk.CLASS_BEAM = 200      # was 121 — moved to prod's duplicate-beam slot
pk.CLASS_BARLINE = 207   # unchanged — already DSv2-free

# Redirect output dir so Phase K's labels don't get overwritten.
pk.OUT_BASE = ROOT / "benchmarks/omr-imslp-pipeline/phase-l-labels"


def main(argv: list[str]) -> int:
    """Defer to Phase K's main; the overrides above kick in at module load."""
    return pk.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
