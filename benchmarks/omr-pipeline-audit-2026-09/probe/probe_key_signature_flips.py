"""Mid-staff KEY-SIGNATURE overwrites, and the stale `key_signature_final`.

The third instance of the per-cell-overwrite family, between the clef
(transcribe.py:1604) and the meter (:1634): transcribe.py:1628-1631.

⚠️ The first version of this probe keyed on a `fifths` field the summary dicts
do not carry, so every staff stringified to "None", every staff looked
constant, and it printed a clean all-zero table at exit 0 -- the exact silent
failure this benchmark's `_fixtures` helper exists to prevent, arriving in the
report's own evidence. The key is (sharps, flats).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, chdir_root, SCAN, ENGRAVED  # fail-loud
chdir_root()

import json
from collections import Counter


def ks(k):
    if not k:
        return None
    assert "sharps" in k and "flats" in k, f"unexpected key summary: {k!r}"
    return (k["sharps"], k["flats"])


for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                   ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
    staves = fin = stale = 0
    flips = []
    first_markers = later_markers = 0
    later_conf = []
    src = Counter()
    for f in files:
        d = json.load(open(f))
        nm = os.path.basename(f).split(".")[0]
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    staves += 1
                    src[st.get("key_signature_source")] += 1
                    ms = st.get("measures", [])
                    seq = [ks(m.get("key_signature")) for m in ms]
                    seen = [x for x in seq if x is not None]
                    changed = len(set(seen)) > 1
                    if st.get("key_signature_final") is not None:
                        fin += 1
                        if not changed:
                            stale += 1
                    prev = None
                    for i, m in enumerate(ms):
                        kd = [x for x in m.get("detections", [])
                              if (x.get("class") or "").lower().startswith("key")]
                        if kd:
                            if i == 0:
                                first_markers += 1
                            else:
                                later_markers += 1
                                later_conf += [x["confidence"] for x in kd]
                        cur = ks(m.get("key_signature"))
                        if cur is not None and prev is not None and cur != prev:
                            flips.append((nm, st["staff_index"], st.get("instrument"), i,
                                          prev, cur, st.get("key_signature_source"),
                                          [(x["class"], round(x["confidence"], 2)) for x in kd]))
                        if cur is not None:
                            prev = cur
    print(f"=== {fam}: {staves} staves")
    print(f"   key_signature_source: {dict(src)}")
    print(f"   cells with a key marker: first cell = {first_markers}, LATER cell = {later_markers}")
    if later_conf:
        later_conf.sort()
        print(f"   later-cell marker confidence: min={later_conf[0]:.2f} "
              f"median={later_conf[len(later_conf)//2]:.2f} max={later_conf[-1]:.2f}")
    print(f"   key_signature_final present={fin}, of which STALE={stale}")
    print(f"   MID-STAFF KEY-SIGNATURE FLIPS: {len(flips)}")
    for x in flips:
        print("     ", x)
