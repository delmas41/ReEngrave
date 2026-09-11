"""How many arcs does the PRINT actually carry over these four pages?

⚠️ REACH BEFORE ACCURACY. Sean said *"almost no ties or slurs are
converting"*; the exporter writes 32 slurs and 80 ties. Neither number means
anything until the denominator is known, and this repo already holds it: the
`works.json` rows for `beethoven-sym5-mvt1-984073-p1..p4` carry HAND-VERIFIED
measure windows into the reference encoding.

⚠️ A PAGE TRUTH IS NOT AN ENCODING TRUTH and this file says so before it prints
a number. MusicXML writes a `<slur>` at EACH END, so the element count is
roughly twice the curves; a tie is `<tied>` at each end too. The engraver draws
ONE arc per curve and, where it crosses a barline, the detector sees TWO. Those
are three different units and they are reported apart.

⚠️ The reference is read with `tools/omr/training/musicxml_truth.py`'s own
dependency-free reader where possible; here only element counts inside a
measure range are needed, so the `.mxl` is unzipped and counted directly with
the stdlib -- no music21, which the host python cannot import.
"""
from __future__ import annotations

import collections
import json
import sys
import xml.etree.ElementTree as ET
import zipfile


def _score_xml(path: str) -> bytes:
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if n.endswith(".xml") and not n.startswith("META-INF")]
        # container.xml names the rootfile; prefer it over guessing.
        if "META-INF/container.xml" in z.namelist():
            c = ET.fromstring(z.read("META-INF/container.xml"))
            for rf in c.iter():
                if rf.tag.endswith("rootfile") and rf.get("full-path"):
                    return z.read(rf.get("full-path"))
        return z.read(names[0])


def main(works: str, mxl: str, row_prefix: str) -> None:
    rows = json.load(open(works))
    rows = rows["rows"] if isinstance(rows, dict) and "rows" in rows else rows
    windows = []
    for r in rows:
        if not r.get("row_id", "").startswith(row_prefix):
            continue
        w = r.get("window") or {}
        windows.append((r["row_id"], w))
    print("hand-verified windows:")
    for rid, w in windows:
        print(f"  {rid}: {json.dumps(w)}")

    lo = min(int(w["first_ref_measure"]) for _r, w in windows if w.get("first_ref_measure"))
    hi = max(int(w.get("last_ref_measure") or w["first_ref_measure"])
             for _r, w in windows if w.get("first_ref_measure"))
    print(f"\nmeasure range {lo}..{hi}")

    root = ET.fromstring(_score_xml(mxl))
    counts: "collections.Counter[str]" = collections.Counter()
    starts: "collections.Counter[str]" = collections.Counter()
    for part in root.iter("part"):
        n = 0
        for m in part.iter("measure"):
            try:
                n = int(m.get("number"))
            except (TypeError, ValueError):
                n += 1
            if not (lo <= n <= hi):
                continue
            for e in m.iter("slur"):
                counts["slur_elements"] += 1
                if e.get("type") == "start":
                    starts["slur_starts"] += 1
            for e in m.iter("tied"):
                counts["tied_elements"] += 1
                if e.get("type") == "start":
                    starts["tie_starts"] += 1
    print("\nTRUTH over that range:")
    for k, v in list(counts.items()) + list(starts.items()):
        print(f"  {k:16s} {v}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
