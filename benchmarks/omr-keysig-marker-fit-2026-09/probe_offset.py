"""Is there a SYSTEMATIC offset between a marker's box centre and its slot?

A flat glyph is not vertically symmetric: its bowl sits at the notated pitch
and its ascender rises well above, so the BOUNDING-BOX CENTRE reads high. If
that is what is happening, every staff's observations sit at a consistent
offset from the slot table, `max_offset=1.25` is absorbing it, and the staves
that abstain are the ones where it exceeds the cap.

FALSIFIED IF: the offsets scatter, or sharps and flats behave the same.
"""
import json, sys, statistics, collections
sys.path.insert(0, ".")
from tools.omr.key_signature_geometry import slot_positions

for tag, path in (("litolff", "out/litolff.json"),
                  ("breitkopf", "out/brahms1-breitkopf.json")):
    rows = json.load(open(f"benchmarks/omr-keysig-marker-fit-2026-09/{path}"))["rows"]
    print(f"\n######## {tag} ########")
    allo = []
    for r in rows:
        slots = slot_positions(r["clef"], r["accidental"])
        if not slots: continue
        obs = sorted(r["observed"])
        s = sorted(slots[:len(obs)])
        # drop the far outliers (>10 steps) -- those are junk, not signature ink
        pairs = [(o, sl) for o, sl in zip(obs, s) if abs(o) < 10]
        if not pairs: continue
        offs = [o - sl for o, sl in pairs]
        med = statistics.median(offs)
        allo.extend(offs)
        print(f"   {r['staff']:14s} {r['clef']:7s} {r['accidental']} n={len(pairs)} "
              f"offsets={[round(o,2) for o in offs]}  median {med:+.2f}  "
              f"fit={r['fit']}")
    if allo:
        print(f"   ---- pooled: n={len(allo)}  median {statistics.median(allo):+.3f}  "
              f"min {min(allo):+.2f}  max {max(allo):+.2f}")
