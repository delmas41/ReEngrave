"""Does the Bach reference encode the Cembalo as a GRAND STAFF?

The page prints 12 staves per system; the trimmed truth has 11 parts. If the
SOURCE encoding declares `<staves>2</staves>` on the Cembalo and the trim
flattened it, the shortfall is a trim artefact and belongs upstream. If the
source is single-staff too, the shortfall is the encoding's own convention and
no `staves` map can reach it — the map idiom only ever MERGES reference parts.

A real XML parser, never a regex.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
SRC = (MAIN / "library/reference/bach/brandenburg-concerto-3/"
       "bach--brandenburg-concerto-3--mvt1--gradus.mxl")
TRIM = (MAIN / ".claude/worktrees/reconciliation/benchmarks/"
        "omr-scan-e2e-2026-09/fixtures/"
        "bach-brandenburg3-mvt1-468678-p1.truth.musicxml")


def report(root, label):
    print(f"--- {label}")
    names = {s.get("id"): (s.findtext("part-name") or "").strip()
             for s in root.findall(".//part-list/score-part")}
    for i, part in enumerate(root.findall("part")):
        pid = part.get("id")
        st = part.find(".//attributes/staves")
        n = int(st.text) if st is not None and st.text else 1
        vals = sorted({e.text for e in part.iter("staff") if e.text})
        print(f"  {i:2d} {pid:8s} {names.get(pid, '?'):22s} "
              f"<staves>={n}  <staff> values={vals}")


def main() -> int:
    report(ET.fromstring(zipfile.ZipFile(SRC).read("score.xml")),
           f"SOURCE  {SRC.name}")
    report(ET.parse(TRIM).getroot(), f"TRIMMED {TRIM.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
