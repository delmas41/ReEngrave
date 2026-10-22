"""Which RULE of `OMR_ARC_RECLASS` fires, per work — and how provable each is.

The inventory probe says the veto takes Mozart 41 from 8 ties over the truth to
exactly right, and takes two other works FURTHER BELOW their truth. A count
cannot tell "removed a wrong tie" from "removed a right one", so this asks the
veto itself which rule fired.

The four rules do NOT carry equal weight and must never be summed:

  tie_to_slur_flagged_diff_pitch   PROVABLE. The arc's own two flanked heads
                                   are different STAFF STEPS. A tie joins one
                                   pitch to itself; this cannot be a tie,
                                   whatever the print says.
  tie_to_slur_unpaired_diff_pitch  provable in the same sense, on an arc whose
                                   flank pairing failed, so it exported no tie
                                   anyway — it can only ADD a slur.
  tie_to_slur_flagged_span         INFERRED. A third event of the voice sits
                                   under the arc. Rests spend an ordinal, and
                                   a measure the detector left EMPTY spends
                                   none — so this one can be wrong about
                                   adjacency without being wrong about pitch.
  tie_to_slur_unpaired_span        inferred likewise, on an unpaired arc.

    python3 .../reclass_reasons.py <fixtures-dir> [--tag TAG]
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

os.environ["OMR_ARC_RECLASS"] = "1"

from tools.omr import export as E  # noqa: E402

PROVABLE = ("tie_to_slur_flagged_diff_pitch", "tie_to_slur_unpaired_diff_pitch")
INFERRED = ("tie_to_slur_flagged_span", "tie_to_slur_unpaired_span")
ORDER = PROVABLE + INFERRED + ("slur_to_tie",)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tag = None
    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
    root = pathlib.Path(args[0])
    pattern = f"*.{tag}.omr.json" if tag else "*.omr.json"
    files = sorted(root.glob(pattern))
    if not files:
        sys.stderr.write("FATAL: no `.omr.json` — a dead instrument.\n")
        return 2
    if not E._arc_reclass_enabled():
        sys.stderr.write("FATAL: the flag is OFF inside the probe; every "
                         "count would be zero for the wrong reason.\n")
        return 2
    pooled: collections.Counter = collections.Counter()
    print(f"{'work':34s} " + " ".join(f"{r.replace('tie_to_slur_', '')[:14]:>15s}"
                                      for r in ORDER))
    for f in files:
        E.reset_arc_reclass_stats()
        E.to_musicxml(json.loads(f.read_text()))
        c = collections.Counter(E.ARC_RECLASS_STATS)
        pooled += c
        print(f"{f.name[:34]:34s} " + " ".join(f"{c[r]:15d}" for r in ORDER))
    print(f"{'POOLED':34s} " + " ".join(f"{pooled[r]:15d}" for r in ORDER))
    prov = sum(pooled[r] for r in PROVABLE)
    infr = sum(pooled[r] for r in INFERRED)
    print(f"\n  PROVABLE (a step-different flanked pair): {prov}"
          f"    INFERRED (a span rule): {infr}")
    if prov + infr + pooled["slur_to_tie"] == 0:
        sys.stderr.write("⚠️ ZERO firings — nothing was measured.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
