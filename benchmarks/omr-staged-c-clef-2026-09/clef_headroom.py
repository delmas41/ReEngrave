"""HEADROOM: the whole clef census, and what an ABSTAINING staff actually has.

The reach probe says 16 C-clef detections are dropped; the control says all
nine affected staves are decided anyway. So the remaining question is whether
the repair can change ANY outcome on these documents -- which means counting
the staves whose clef verdict does NOT decide, and asking what evidence each
of them holds.

⚠️ It reports the census BOTH ways. "No abstaining staff holds a dropped C
clef" and "there are no abstaining staves at all" are different facts, and
only the second would make this probe vacuous.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                       # noqa: E402
from clef_reach import measure                              # noqa: E402

DOCS = {
    "Litolff Beethoven 5 p1-p4": "library/_shared-records/beethoven5-p1-p4.record.json",
    "Breitkopf Brahms 1 p0-p3": "library/_shared-records/brahms1-breitkopf-p0-p3.record.json",
}


def main() -> int:
    for label, rel in DOCS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{label}: RECORD ABSENT -- reported, not skipped")
            continue
        r = measure(str(p))
        dropped_staves = {f"staff/{a}/{b}/{c}"
                          for (a, b, c) in r["starved"]}
        # every staff that dropped a C clef, starved or not
        any_drop = set()
        for (a, b, c), v in r["starved"].items():
            any_drop.add(f"staff/{a}/{b}/{c}")

        outcomes = Counter()
        abstain_reasons = Counter()
        abstaining: list[str] = []
        for v in stream_array(str(p), "verdicts"):
            if v.get("quantity") != "clef":
                continue
            out = str(v.get("outcome"))
            outcomes[out] += 1
            if out != "decided":
                abstain_reasons[str(v.get("reason"))] += 1
                abstaining.append(str(v.get("subject")))

        # which abstaining staves hold a locator C-clef reading?
        loc_c: dict[str, list] = {s: [] for s in abstaining}
        for o in stream_array(str(p), "observations"):
            s = str(o.get("subject", ""))
            if s in loc_c and o.get("quantity") == "clef_located":
                loc_c[s].append(o.get("value"))

        print(f"=== {label} ===")
        print(f"  clef verdicts          : {dict(outcomes)}")
        print(f"  non-decided reasons    : {dict(abstain_reasons)}")
        print(f"  staves dropping a C clef: {len(any_drop)}")
        print(f"  abstaining staves ALSO dropping a C clef: "
              f"{len(set(abstaining) & any_drop)}")
        withloc = {s: v for s, v in loc_c.items() if v}
        print(f"  abstaining staves with a LOCATOR reading: {len(withloc)}")
        for s, v in sorted(withloc.items())[:10]:
            print(f"      {s} located={v}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
