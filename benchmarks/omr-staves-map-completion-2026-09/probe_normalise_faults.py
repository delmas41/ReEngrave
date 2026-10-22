"""Full tracebacks for the two rows `page_normalise` refuses.

`probe_mappable.py` catches the exception so every row is reported; this one
lets it out, because WHERE it lands decides whether the map is the wrong shape
or the transform has a gap the corpus had never reached.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(HERE))

import page_normalise      # noqa: E402
import candidate_maps      # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")

for rid in sys.argv[1:] or ["mahler-sym5-mvt1-local-p3",
                            "mahler-sym5-mvt1-local-p4",
                            "mahler-sym5-mvt1-local-p5"]:
    print("=" * 72)
    print(rid)
    try:
        page_normalise.normalise(REC / f"{rid}.truth.musicxml",
                                 candidate_maps.flat(rid))
        print("  ACCEPTED")
    except Exception:                                  # noqa: BLE001
        traceback.print_exc()
