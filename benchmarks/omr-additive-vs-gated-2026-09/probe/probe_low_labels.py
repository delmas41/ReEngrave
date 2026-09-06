"""How many margin labels does `MIN_LABEL_CONFIDENCE` drop, and at what
coverage?

`instruments.Match.coverage` is a float; `Match.confidence` buckets it to
high/medium/low (>= 0.6 -> high, ocr_folded -> low unconditionally); `slots`,
`roster`, `contextual` and `absent_instrument` then all drop `low`. The float is
binarised twice on the way into two models (`slots`, `score_layouts`) that are
already additive.

The transcriptions record the dropped ones as `contextual.low_confidence_labels`
and the survivors' tier counts as `contextual.label_tiers`, so the reach is
readable off committed artefacts.
"""
from __future__ import annotations

import collections
import glob
import json
import os

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def main():
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or ("graft09" not in p
                                            and "restamp" not in p))
        low, unresolved, labelled = [], [], 0
        tiers = collections.Counter()
        for path in paths:
            c = (json.load(open(path)).get("contextual") or {})
            labelled += c.get("labelled_staves") or 0
            for k, v in (c.get("label_tiers") or {}).items():
                tiers[k] += v
            for item in (c.get("low_confidence_labels") or []):
                low.append((os.path.basename(path)[:32], item))
            for item in (c.get("unresolved_labels") or []):
                unresolved.append((os.path.basename(path)[:32], item))
        print(f"\n{'='*76}\n{fam.upper()}\n{'='*76}")
        print(f"   labelled staves (consumable)      {labelled}")
        print(f"   reader tiers                      {dict(tiers)}")
        print(f"   dropped at `low` confidence       {len(low)}")
        for row in low:
            print("     *", json.dumps(row)[:180])
        print(f"   read but the lexicon knew nothing {len(unresolved)}")
        for row in unresolved[:20]:
            print("     -", json.dumps(row)[:180])


if __name__ == "__main__":
    main()
