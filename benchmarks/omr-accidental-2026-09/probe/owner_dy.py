"""ROADMAP 2.7 — the DECIDED owners' own height offset, by glyph class.

⚠️ WHY THIS EXISTS. `_ACC_MAX_DY_POSITIONS = 1.4` was read off the dy
histogram of `gap_histogram.py` at `--anchor-flat 0.5` (the branch's own
`out/gap-histogram-*.json`, whose bins match the numbers quoted in
`ownership.py`: Litolff 1.2:58 · 1.3:32 · 1.4:10). GATHER files positions at
the Bravura anchor (0.715 for a flat), and on THAT histogram the cliff at 1.4
is not there (`out/anchor-control-*-0.715.json`). A decided owner with
`dy > 0.5` is one whose head sits nearer the NEXT diatonic step than the
glyph's own; this counts them, per class, so the print check can be pointed
at them.

    python3 benchmarks/omr-accidental-2026-09/probe/owner_dy.py <record> [<record> ...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402


def main() -> int:
    out = {}
    for path in sys.argv[1:]:
        rec = load_record(path)["record"]
        sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
        by = collections.defaultdict(lambda: collections.Counter())
        for v in rec["verdicts"]:
            if (v["quantity"] != "accidental_owner" or v["id"] in sup
                    or v["outcome"] != "decided"):
                continue
            d = v.get("detail") or {}
            dy = float(d.get("dy_positions") or 0.0)
            band = ("<=0.5" if dy <= 0.5 else "0.5-1.0" if dy <= 1.0
                    else "1.0-1.4")
            by[str(d.get("detector_class"))][band] += 1
        out[path] = {k: dict(v) for k, v in sorted(by.items())}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
