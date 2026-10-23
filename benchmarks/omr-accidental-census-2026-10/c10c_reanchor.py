"""2.197 C10c: of the accidentals whose owner abstained no_candidate with the nearest head 1.4-2.0 positions off (just past the 1.4 bound), how many would fall inside the bound
if the glyph were anchored at its BOX CENTRE (anchor fraction 0.5, what a natural/sharp has) instead of its class's anchor (flat 0.715)? A measurement of how much the class guess
moves the geometry; it changes no verdict. usage: c10c_reanchor.py VIEW.json XML UNIT"""
import sys, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, fam
v = View(sys.argv[1], sys.argv[2]); UNIT = float(sys.argv[3])
pos = {o["subject"]: float(o["value"]) for o in v.obs if o["quantity"] == "notehead_staff_position" and isinstance(o["value"], (int, float))}
heads = collections.defaultdict(list)
for pg, bs in v.boxes.items():
    for g in bs:
        if g["category"] == "notehead" and g["reader"] == "detector": heads[(g["page"], g["system"], g["staff"], g["cell"])].append(g)
c = collections.Counter(); tot = collections.Counter()
for pg, bs in v.boxes.items():
    for g in bs:
        if g["reader"] != "detector" or fam(g["cls"]) != "accidental": continue
        own = v.verdict(g["key"], "accidental_owner")
        if not own or own["reason"] != "no_candidate": continue
        b = g["box"]
        if (b[3] - b[1]) / UNIT < 1.6: continue
        row = v.accpos.get(g["key"]); apos = float(row["value"]); frac = (row["detail"] or {}).get("anchor_fraction")
        cand = []
        for h in heads.get((g["page"], g["system"], g["staff"], g["cell"]), ()):
            nv = v.verdict(h["key"], "notehead_is_not_a_notehead")
            if nv and nv["outcome"] == "decided" and nv["value"] is True: continue
            if h["box"][2] < b[2] or (h["box"][0] - b[2]) / UNIT > 1.75 or h["key"] not in pos: continue
            cand.append(h)
        if not cand: continue
        d = min(abs(pos[h["key"]] - apos) for h in cand)
        if not (1.4 < d <= 2.0): continue
        apos2 = apos - (frac - 0.5) * (b[3] - b[1]) / (UNIT / 2.0)
        d2 = min(abs(pos[h["key"]] - apos2) for h in cand)
        tot[g["cls"]] += 1; c[(g["cls"], "inside" if d2 <= 1.4 else "outside")] += 1
print("near-miss no_candidate by class:", dict(tot)); print("re-anchored at the box centre:", dict(c))
