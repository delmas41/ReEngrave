"""`pitch_candidates` -- the winner+runner-up+margin record the rest of the
pipeline lacks, present on every notehead, consumed by nobody in production."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, chdir_root, SCAN, ENGRAVED  # fail-loud
chdir_root()

import json
from collections import Counter

for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                   ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
    n = nopitch = distinct_runner = 0
    sizes = Counter()
    margins = []
    for f in files:
        d = json.load(open(f))
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    for m in st.get("measures", []):
                        for det in m.get("detections", []):
                            if det.get("category") != "notehead":
                                continue
                            n += 1
                            if not det.get("pitch"):
                                nopitch += 1
                            pc = det.get("pitch_candidates") or []
                            sizes[len(pc)] += 1
                            if len(pc) >= 2:
                                if pc[0].get("pitch") != pc[1].get("pitch"):
                                    distinct_runner += 1
                                margins.append(round(pc[0].get("weight", 0)
                                                     - pc[1].get("weight", 0), 3))
    margins.sort()
    q = (lambda p: margins[int(p * len(margins))]) if margins else (lambda p: None)
    print(f"=== {fam}: {n} noteheads")
    print(f"   with NO parsable pitch (would become <rest/> at export._parse_pitch): {nopitch}")
    print(f"   candidate-list sizes: {dict(sorted(sizes.items()))}")
    print(f"   with a DISTINCT runner-up: {distinct_runner}")
    print(f"   winner-minus-runner-up weight margin: p10={q(.10)} median={q(.50)} p90={q(.90)}")
