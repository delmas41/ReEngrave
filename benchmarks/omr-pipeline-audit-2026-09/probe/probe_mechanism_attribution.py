"""Which MECHANISM actually supplied each recognition target, counted.

The technology ledger's "read by" column is a design statement. This is the
observed one: over both standing corpora, which reader's answer is on the
record for the clef, the key signature, the meter, the margin label and the
direction text -- and for the glyph families, whether the class exists in the
detector's 208-class space at all.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, chdir_root, SCAN, ENGRAVED  # fail-loud
chdir_root()

import json
from collections import Counter

CLASS_FAMILIES = {
    "notehead": ("noteheadBlack", "noteheadHalf", "noteheadWhole"),
    "stem": ("stem",),
    "beam": ("beam",),
    "staff line": ("staff",),
    "ledger line": ("ledgerLine",),
    "tie": ("tie",),
    "slur": ("slur",),
    "hairpin": ("dynamicCrescendoHairpin", "dynamicDiminuendoHairpin"),
    "barline": ("barline",),
    "family bracket": ("bracket",),
}

for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                   ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
    clef = Counter(); key = Counter(); meter = Counter()
    tiers = Counter(); dirs = Counter(); det_class = Counter()
    staves = 0
    for f in files:
        d = json.load(open(f))
        for k, v in ((d.get("contextual") or {}).get("label_tiers") or {}).items():
            tiers[k] += v if isinstance(v, int) else 0
        dt = d.get("direction_text") or {}
        if dt.get("available"):
            for pg in dt.get("pages", []):
                for k, v in (pg.get("by_reader") or {}).items():
                    dirs[k] += v
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    staves += 1
                    clef[st.get("clef_source")] += 1
                    key[st.get("key_signature_source")] += 1
                    meter[(st.get("time_signature") or {}).get("source")] += 1
                    for m in st.get("measures", []):
                        for det in m.get("detections", []):
                            det_class[det.get("class")] += 1
    print(f"=== {fam}: {staves} staves")
    print(f"   CLEF  supplied by: {dict(clef)}")
    print(f"   KEY   supplied by: {dict(key)}")
    print(f"   METER supplied by: {dict(meter)}")
    print(f"   MARGIN LABEL rung: {dict(tiers)}")
    print(f"   DIRECTION rung   : {dict(dirs) or 'no report (built --no-direction-text)'}")
    print("   detector classes actually emitted, by family:")
    for name, prefixes in CLASS_FAMILIES.items():
        n = sum(v for k, v in det_class.items()
                if k and any(k.startswith(p) for p in prefixes))
        print(f"      {name:16s} {n}")
