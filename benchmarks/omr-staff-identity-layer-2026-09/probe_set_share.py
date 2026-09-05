#!/usr/bin/env python3
"""How many staves carry a usable SET even though no NAME was committed?

MEASUREMENT ONLY. Needs no truth, so it runs over ALL 396 staves of the 20-row
gate rather than the 198 that have hand-read page truth.

WHY THIS IS THE NUMBER. The identity record carries two quantities that must
never be collapsed:

    P(name)   this specific instrument is correct -- for consumers that must
              COMMIT: part naming, an identity-driven clef override, the roster
    P(set)    the truth is somewhere in this candidate set -- for consumers
              that only RULE OUT: the written-range veto, a pitch prior,
              `_dedupe_cross_staff_detections` arbitration

They cannot be derived from one another by any fixed factor, and this
workstream's own numbers are why: where the namer is WRONG the truth is in its
set 0.200 of the time, where it ABSTAINS 0.902
(`probe_candidate_sets.py`). Those are different epistemic states and one
blended number destroys the distinction.

The consequence is that an ABSTAINING staff is not information-free, and the
namer's coverage is therefore NOT the ceiling on the layer's usefulness. This
probe measures the gap between the two reaches.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_set_share.py

── RESULTS 2026-09-05 ────────────────────────────────────────────────────────
    TOTAL staves in the 20-row gate     396
      committed NAME (P(name) applies)  306   0.773
      NO name but a usable SET           90   0.227
      nothing at all                      0   0.000
      ANY usable set                    396   1.000
      set size  median 5.0  mean 5.33  max 8   (lexicon is 28)

Every staff on the gate carries a candidate set, and the set-shaped consumers
therefore reach 1.000 where the namer reaches 0.773 -- 90 staves that are dead
ends today become 5-way shortlists that hold the truth about nine times in ten.

⚠️ Read this TOGETHER with the CSP result, or the two look contradictory. The
CSP is a COVERAGE mechanism: pruning moves staves from abstention into
resolution and barely touches wrong answers. That is a division of labour
rather than a disappointment -- the CSP grows the population carrying a
committed name, and P(set) is what makes the un-pruned remainder useful
meanwhile.

⚠️ `set size median 5.0` is not `P(set)` and must not be reported as one. It is
how much there is left to prune; the probability that the truth is IN the set
is measured against truth in `probe_candidate_sets.py` (0.899 pooled) and is
calibrated separately.
"""
from __future__ import annotations

import glob
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.score_layouts import LAYOUTS, align_to_layout, fit_layouts  # noqa: E402

FIXTURES = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
TAG = ".reconciliation"
RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}


def main():
    paths = sorted(glob.glob(f"{FIXTURES}/*{TAG}.omr.json"))
    print(f"FIXTURES {FIXTURES}\nTAG {TAG!r}   rows {len(paths)}")
    if len(paths) != 20:
        raise SystemExit(f"expected the 20-row gate, found {len(paths)}")

    tot = named = setonly = nothing = 0
    sizes = []
    per_pub = Counter()
    for p in paths:
        rid = Path(p).name[: -len(f"{TAG}.omr.json")].rstrip(".")
        pub = rid.split("-")[0]
        for page in json.loads(Path(p).read_text()).get("pages", []):
            for sysd in page.get("systems", []):
                staves = sorted(
                    sysd.get("staves", []),
                    key=lambda s: (s.get("staff_geometry") or {})
                    .get("line_ys_page", [0])[0])
                n = len(staves)
                clefs = {i: s["clef"] for i, s in enumerate(staves)
                         if s.get("clef_source") in RAW_CLEF_SOURCES
                         and s.get("clef")}
                fit = fit_layouts(n, labels=None, clefs=clefs or None)
                union = [set() for _ in range(n)]
                for layout in LAYOUTS:
                    _, assign = align_to_layout(layout, n, None, clefs or None)
                    for i, nm in enumerate(assign):
                        if nm:
                            union[i].add(nm)
                for i in range(n):
                    tot += 1
                    has_name = bool(fit and fit.assignment[i])
                    if union[i]:
                        sizes.append(len(union[i]))
                    if has_name:
                        named += 1
                    elif union[i]:
                        setonly += 1
                        per_pub[pub] += 1
                    else:
                        nothing += 1

    if not tot:
        raise SystemExit("REFUSING to report: no staves read.")
    print(f"\nTOTAL staves in the 20-row gate     {tot}")
    print(f"  committed NAME (P(name) applies)  {named:4d}   {named/tot:.3f}")
    print(f"  NO name but a usable SET          {setonly:4d}   {setonly/tot:.3f}")
    print(f"  nothing at all                    {nothing:4d}   {nothing/tot:.3f}")
    print(f"  ANY usable set                    {named+setonly:4d}   "
          f"{(named+setonly)/tot:.3f}")
    print(f"  set size  median {statistics.median(sizes):.1f}  "
          f"mean {statistics.mean(sizes):.2f}  max {max(sizes)}   "
          f"(lexicon is 28)")
    print(f"\n  set-only staves by publisher: {dict(per_pub)}")


if __name__ == "__main__":
    main()
