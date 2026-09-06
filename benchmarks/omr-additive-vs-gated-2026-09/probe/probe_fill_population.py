"""Why does the clef FILL tier reach nothing? Count its population's noteheads.

`propose_clef` needs `MIN_NOTEHEADS` resolved pitches to compute a register fit.
The fill tier fires only where NO clef was read. This asks whether those two
populations overlap at all -- i.e. whether an unread clef and a readable
register are the same staves.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from tools.omr.clef_correction import MIN_NOTEHEADS  # noqa: E402

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def pitched_noteheads(st):
    return sum(1 for m in st.get("measures", [])
               for d in m.get("detections", [])
               if d.get("category") == "notehead" and d.get("pitch"))


def main():
    print(f"MIN_NOTEHEADS = {MIN_NOTEHEADS}")
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or ("graft09" not in p
                                            and "restamp" not in p))
        buckets = {"read": [], "unread": []}
        for path in paths:
            for page in json.load(open(path)).get("pages", []):
                for sysm in page.get("systems", []):
                    for st in sysm.get("staves", []):
                        key = "read" if st.get("clef_source") else "unread"
                        buckets[key].append(pitched_noteheads(st))
        print(f"\n{fam.upper()}")
        for key, vals in buckets.items():
            vals.sort()
            if not vals:
                continue
            enough = sum(1 for v in vals if v >= MIN_NOTEHEADS)
            print(f"   clef {key:7s} n={len(vals):4d}  "
                  f"median pitched noteheads={vals[len(vals)//2]:4d}  "
                  f"zero={sum(1 for v in vals if v == 0):4d}  "
                  f">= MIN_NOTEHEADS: {enough:4d} ({enough/len(vals):.1%})")


if __name__ == "__main__":
    main()
