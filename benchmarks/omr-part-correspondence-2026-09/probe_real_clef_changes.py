"""How much REAL mid-staff clef change does this repertoire print? — read-only.

The question that decides whether the clef may be given the corroboration guard
its two siblings have. `key_signature_corroboration` could ship because the
corpus holds **zero** real mid-staff key changes, so its benefit was measurable
and its only unmeasurable cost was hypothetical. Transplanting that guard to the
clef assumes the same asymmetry. This asks the truth files whether it holds.

Counts `<clef>` elements after a part's first measure. A clef in measure 1 is
the staff's opening clef; anything later is a printed mid-staff change — a cello
going tenor, a bassoon coming back to bass.

Exits non-zero if a truth set is missing or empty.
"""
from __future__ import annotations

import collections
import glob
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ.get("REENGRAVE_MAIN", "/Users/seanjohnson/Desktop/ReEngrave"))

SETS = {
    "scan": "benchmarks/omr-scan-e2e-2026-09/fixtures/*.truth.musicxml",
    # ⚠️ the engraved truths are the un-suffixed `.musicxml`; `*.omr.musicxml`
    # beside them is our OWN export and must never be counted as truth.
    "engraved": "benchmarks/omr-orchestral-e2e/fixtures/[!.]*[!r].musicxml",
}


def main() -> int:
    missing = []
    for label, pat in SETS.items():
        files = sorted(glob.glob(str(REPO / pat))) or sorted(glob.glob(str(MAIN / pat)))
        if not files:
            print(f"{label}: NO TRUTH FILES matching {pat}", file=sys.stderr)
            missing.append(label)
            continue
        parts = first = mid = 0
        kinds: collections.Counter[str] = collections.Counter()
        for f in files:
            for part in ET.parse(f).getroot().findall("part"):
                parts += 1
                for m_idx, measure in enumerate(part.findall("measure")):
                    for clef in measure.findall(".//clef"):
                        sign = (clef.findtext("sign") or "") + (clef.findtext("line") or "")
                        if m_idx == 0:
                            first += 1
                        else:
                            mid += 1
                            kinds[sign] += 1
        print(f"{label}: {len(files)} works, {parts} parts | "
              f"clef in m1 = {first} | clef AFTER m1 = {mid} {dict(kinds)}")
    if missing:
        print(f"FATAL: {len(missing)} truth set(s) empty or missing: {missing}",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
