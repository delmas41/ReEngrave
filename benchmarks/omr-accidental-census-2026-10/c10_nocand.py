"""2.197 C10: WHY `accidental_owner` abstains no_candidate (and what the boxes' height says). usage: c10_nocand.py VIEW.json XML UNIT_PAGE_PX OUT.json
For each accidental-class box whose owner abstained no_candidate: heads of its cell (notehead boxes), the nearest head to its right by the owner's own two bounds
(dx <= 1.75 sp past the glyph's right edge; |head position - glyph anchor position| <= 1.4) -> which bound failed.
Also: box height / staff space per class (the glyphs are ~3 sp tall; a box much shorter than that moves the anchor)."""
import sys, json, collections, statistics
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, fam
v = View(sys.argv[1], sys.argv[2]); UNIT = float(sys.argv[3])
heads = collections.defaultdict(list)
pos = {}
for o in v.obs:
    if o["quantity"] == "notehead_staff_position":
        try: pos[o["subject"]] = float(o["value"])
        except Exception: pass
for pg, bs in v.boxes.items():
    for g in bs:
        if g["category"] == "notehead" and g["reader"] in ("detector",): heads[(g["page"], g["system"], g["staff"], g["cell"])].append(g)
res = collections.Counter(); hh = collections.defaultdict(list)
for pg, bs in v.boxes.items():
    for g in bs:
        if g["reader"] != "detector" or fam(g["cls"]) != "accidental": continue
        b = g["box"]; hh[g["cls"]].append((b[3] - b[1]) / UNIT)
        own = v.verdict(g["key"], "accidental_owner")
        if not own or own["reason"] != "no_candidate": continue
        row = v.accpos.get(g["key"]); dt = (row or {}).get("detail") or {}
        cell = (g["page"], g["system"], g["staff"], g["cell"])
        hs = heads.get(cell, [])
        # drop heads the record refused as not-a-notehead
        live = []
        for h in hs:
            nv = v.verdict(h["key"], "notehead_is_not_a_notehead")
            if nv and nv["outcome"] == "decided" and nv["value"] is True: continue
            live.append(h)
        hsp = (b[3] - b[1]) / UNIT
        if hsp < 1.6 and g["cls"] in ("accidentalFlat", "accidentalSharp", "accidentalNatural"):
            res["SHORT BOX (< 1.6 sp tall: a fragment -- ascender / stem tip)"] += 1; continue
        # a head that WOULD have been a candidate (reaches past the glyph, dx <= 1.75, |dy| <= 1.4) but the record refused it as not-a-notehead
        refused_cand = 0
        for h in hs:
            nv = v.verdict(h["key"], "notehead_is_not_a_notehead")
            if nv and nv["outcome"] == "decided" and nv["value"] is True and h["box"][2] >= b[2] and (h["box"][0] - b[2]) / UNIT <= 1.75 and h["key"] in pos \
                    and row and abs(pos[h["key"]] - float(row["value"])) <= 1.4:
                refused_cand += 1
        if refused_cand: res["the head that fits was REFUSED as not-a-notehead (merged/claimed ink)"] += 1; continue
        if not hs: res["no head box at all in the cell"] += 1; continue
        if not live: res["every head box in the cell refused (not-a-notehead)"] += 1; continue
        apos = float(row["value"]) if row else None
        x1 = b[2]
        reach = [h for h in live if h["box"][2] >= x1]
        if not reach: res["heads exist, none reaches past the glyph (all to its left)"] += 1; continue
        near = [h for h in reach if (h["box"][0] - x1) / UNIT <= 1.75 or h["box"][0] <= x1]
        if not near: res["heads to the right but > 1.75 sp away"] += 1; continue
        withpos = [h for h in near if h["key"] in pos]
        if not withpos: res["head in window has no staff position"] += 1; continue
        dy = min(abs(pos[h["key"]] - apos) for h in withpos)
        res["head in window, height off by %s" % ("1.4-2.0 pos" if dy <= 2.0 else ("2.0-3.0 pos" if dy <= 3.0 else ">3.0 pos"))] += 1
out = dict(no_candidate_causes=dict(res), box_height_sp={k: dict(n=len(x), median=round(statistics.median(x), 2), p10=round(sorted(x)[int(len(x) * .1)], 2), p90=round(sorted(x)[int(len(x) * .9)], 2)) for k, x in hh.items() if len(x) > 5})
json.dump(out, open(sys.argv[4], "w"), indent=1); print(json.dumps(out, indent=1))
