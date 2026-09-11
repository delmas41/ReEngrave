"""What `<measure number=>` MEANS in the exported file, per part.

⚠️ THE QUESTION §4 OF FINDINGS TURNS ON. MusicXML numbers measures WITHIN a
part, and a part whose instrument is tacet for a system still occupies those
bars of musical time. So the file can only be read vertically if every part
numbers the same instant with the same number -- and whether it does is a fact
about the exporter, not about the join.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SYSTEM_MAP = REPO / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"


def main() -> int:
    smap = json.loads(SYSTEM_MAP.read_text())
    print("Each part's measure numbers, per printed system.")
    print("Read DOWN a column: these are all the same printed bars.\n")
    systems = [(s["page"], s["system"]) for s in smap["systems"]]
    per = {}
    for sd in smap["systems"]:
        for st in sd["staves"]:
            per.setdefault(st["part_index"], {})[(sd["page"], sd["system"])] = (
                st["first_measure"], st["last_measure"])

    print("%-5s %s" % ("part", "  ".join("%-10s" % ("p%d/s%d" % k)
                                         for k in systems)))
    for pi in sorted(per):
        cells = []
        for k in systems:
            r = per[pi].get(k)
            cells.append("%-10s" % ("%d-%d" % r if r else "--"))
        print("P%-4d %s" % (pi + 1, "  ".join(cells)))

    print()
    print("⚠️  DISAGREEMENTS -- one printed system, several numberings:")
    bad = 0
    for k in systems:
        starts = sorted({per[pi][k][0] for pi in per if k in per[pi]})
        if len(starts) > 1:
            bad += 1
            print("   p%d/s%d starts at %s depending on the part"
                  % (k[0], k[1], starts))
    if not bad:
        print("   none")
    print()
    print("So `<measure number=N>` names %s instant across the file."
          % ("ONE" if not bad else "DIFFERENT instants"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
