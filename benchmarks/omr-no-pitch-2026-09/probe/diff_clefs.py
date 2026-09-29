"""Diff every staff's Q.CLEF verdict between the 09-28 and 09-29 Litolff
whole-movement records, to find which staves' clef OUTCOME or VALUE moved --
the join `find_no_pitch.py`'s per-staff breakdown pointed at (2.11b,
'adjudicate_clef discounts an off-staff detector clef box')."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def clef_map(path):
    rec = X.Record(load_record(path))
    out = {}
    for v in rec.verdicts_of(Q.CLEF):
        sub = v["subject"]
        out[sub] = {"outcome": v["outcome"], "value": v.get("value"),
                    "reason": v.get("reason")}
    return out


def main(argv):
    p28, p29 = argv[1], argv[2]
    m28 = clef_map(p28)
    m29 = clef_map(p29)
    staves = sorted(set(m28) | set(m29))
    changed = []
    for st in staves:
        a, b = m28.get(st), m29.get(st)
        if a != b:
            changed.append((st, a, b))
    print(f"{len(changed)} staff clef verdicts changed of {len(staves)} total")
    for st, a, b in changed:
        print(f"  {st}: {a} -> {b}")


if __name__ == "__main__":
    main(sys.argv)
