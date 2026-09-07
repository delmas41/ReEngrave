import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS  # fail-loud
chdir_root()

#!/usr/bin/env python3
"""Reach of the clef precedence ladder, from committed transcriptions.

Read-only. Answers:
  1. which rung supplied each staff's clef (`clef_source`)
  2. how often the argmax at transcribe.py:1604 had MORE THAN ONE clef
     detection to choose between, and what the margin was
  3. how often the runner-up carried a DIFFERENT class than the winner
     -- the case where the argmax silently resolves a disagreement
  4. how often a staff's per-measure clef CHANGES mid-staff
"""
import json, os, sys, glob
from collections import Counter


FAMILIES = {
    "scan": sorted(fixtures(SCAN, expect_at_least=11)),
    "engraved": sorted(fixtures(ENGRAVED, expect_at_least=11)),
}

for fam, files in FAMILIES.items():
    src = Counter(); n_staves = 0; n_files = 0
    clef_dets_per_cell = Counter()
    margins = []; diffclass = 0; contests = 0
    cells_with_clef = 0; total_cells = 0
    staff_clef_changes = 0; staves_multi_measure = 0
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        n_files += 1
        for pg in d.get("pages", []):
            for sy in pg.get("systems", []):
                for st in sy.get("staves", []):
                    n_staves += 1
                    src[st.get("clef_source")] += 1
                    seen_clefs = []
                    for m in st.get("measures", []):
                        total_cells += 1
                        cd = [x for x in m.get("detections", [])
                              if x.get("category") == "clef"]
                        clef_dets_per_cell[len(cd)] += 1
                        if cd:
                            cells_with_clef += 1
                        if len(cd) >= 2:
                            contests += 1
                            cd.sort(key=lambda x: -(x.get("confidence") or 0))
                            margins.append(round((cd[0].get("confidence") or 0)
                                                 - (cd[1].get("confidence") or 0), 4))
                            if cd[0].get("class") != cd[1].get("class"):
                                diffclass += 1
                        if m.get("clef") is not None:
                            seen_clefs.append(m["clef"])
                    if len(seen_clefs) > 1:
                        staves_multi_measure += 1
                        if len(set(seen_clefs)) > 1:
                            staff_clef_changes += 1
    print(f"=== {fam}: {n_files} files, {n_staves} staves, {total_cells} cells")
    print("  clef_source:", dict(src))
    print(f"  cells with >=1 clef detection: {cells_with_clef}")
    print("  clef detections per cell:", dict(sorted(clef_dets_per_cell.items())))
    print(f"  ARGMAX CONTESTS (>=2 clef dets in one cell): {contests}")
    if margins:
        margins.sort()
        n = len(margins)
        q = lambda p: margins[min(n-1, int(p*n))]
        print(f"    margin p10={q(.10)} p25={q(.25)} median={q(.50)} p75={q(.75)} max={margins[-1]}")
        print(f"    margin < 0.05: {sum(1 for m in margins if m < 0.05)}  "
              f"< 0.10: {sum(1 for m in margins if m < 0.10)}")
        print(f"    runner-up a DIFFERENT class: {diffclass} of {contests}")
    print(f"  staves whose per-measure clef CHANGES: {staff_clef_changes} "
          f"of {staves_multi_measure} multi-measure staves")
    print()
