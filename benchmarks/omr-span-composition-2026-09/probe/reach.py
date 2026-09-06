"""Which whole works `OMR_SPAN_REFERENCE_FIT` can reach AT ALL.

`_align_by_span` runs only where `movement_reference.lineup_spans` takes a
boundary, so a work with one span never reaches the composition step and this
flag cannot move it — no measurement needed, and no measurement possible. The
boundary session left committed staff-size profiles for four works; this asks
each of them the reach question directly, so "n=2" is the whole available
population rather than a sample anybody chose.

Usage: reach.py benchmarks/omr-movement-reference-2026-09/out/*.staffprofile.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import movement_reference                        # noqa: E402


def main():
    print(f"{'work':22s} {'pages':>6s} {'spans':>6s}   reach")
    for p in sys.argv[1:]:
        d = json.loads(Path(p).read_text())
        rows = [(int(r["page"]), list(r["systems"])) for r in d["rows"]]
        spans = movement_reference.lineup_spans(rows)
        reach = ("_align_by_span RUNS" if len(spans) > 1
                 else "one span -> _align_by_span never runs; flag unreachable")
        print(f"{Path(p).name.split('.')[0]:22s} {len(rows):6d} "
              f"{len(spans):6d}   {reach}")
        if len(spans) > 1:
            print(f"{'':22s} {'':6s} {'':6s}   "
                  f"{[(min(s), max(s)) for s in spans]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
