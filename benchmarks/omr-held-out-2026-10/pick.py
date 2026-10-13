"""Seeded pick of tile subjects per (doc, rule) quota; writes plan.json for make_tiles.py"""
import json
import random
import sys

P = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/held-out-2101/"
L = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
DOCS = {
    "dvorak": {"pdf": L + "dvorak/symphony-8-op88/dvorak--symphony-8-op88--novello-1892--imslp405841.pdf",
               "record": P + "dvorak8-novello-arm.record.json"},
    "schumann": {"pdf": L + "schumann/symphony-2-op61/schumann--symphony-2-op61--peters-1887--imslp514290.pdf",
                 "record": P + "schumann2-peters-arm.record.json"},
    "tchaikovsky": {"pdf": L + "tchaikovsky/symphony-4-op36/tchaikovsky--symphony-4-op36--jurgenson--imslp377460.pdf",
                    "record": P + "tchaikovsky4-jurgenson-arm.record.json"},
}
cases = {d: json.load(open(P + f"probe/cases-{d}.json"))[d] for d in DOCS}
# (doc, rule, quota, kind, purpose)
QUOTA = [
    ("dvorak", "2.99_rest_decided", 2, "mark", "2.99 rest read from unboxed ink (decided)"),
    ("tchaikovsky", "2.99_rest_decided", 4, "mark", "2.99 rest read from unboxed ink (decided)"),
    ("tchaikovsky", "2.99_refused_stroke", 1, "mark", "2.99 look-alike REFUSED (stroke, not a rest)"),
    ("dvorak", "2.99_abstained_shape", 1, "mark", "2.99 abstained: shape cannot tell"),
    ("tchaikovsky", "2.99_abstained_shape", 1, "mark", "2.99 abstained: shape cannot tell"),
    ("dvorak", "2.88_half_lost_vs_base", 1, "note", "base decided half; arm narrowed"),
    ("dvorak", "2.88_half_tip_unread_same_as_base", 1, "note", "2.88 unread-tip half"),
    ("schumann", "2.88_half_other", 1, "note", "new hollow-head half"),
    ("schumann", "2.81_bare_stem_by_bar", 2, "note", "2.81 bare stem settled by the bar"),
    ("dvorak", "2.81_bare_stem_by_bar", 1, "note", "2.81 bare stem settled by the bar"),
]
rng = random.Random(7)
tiles = []
for doc, rule, k, kind, purpose in QUOTA:
    pool = [c for c in cases[doc] if c["rule"] == rule and c["box_page_px"]]
    if rule == "2.81_bare_stem_by_bar":  # an EIGHTH is among them when one exists
        eighth = [c for c in pool if (c["arm"]["value"] or {}).get("beats") == 0.5]
        quarter = [c for c in pool if (c["arm"]["value"] or {}).get("beats") != 0.5]
        pick = rng.sample(eighth, min(1, len(eighth)))
        pick += rng.sample(quarter, min(k - len(pick), len(quarter)))
    elif rule == "2.99_rest_decided":
        q = [c for c in pool if c["arm"]["value"] == "quarter"]
        e = [c for c in pool if c["arm"]["value"] != "quarter"]
        pick = rng.sample(q, min(1, len(q)))
        pick += rng.sample(e, min(k - len(pick), len(e)))
    else:
        pick = rng.sample(pool, min(k, len(pool)))
    for c in pick:
        tiles.append({"doc": doc, "kind": kind, "subject": c["subject"], "box": c["box_page_px"],
                      "purpose": purpose, "rule": rule,
                      "our_reading": {"arm": c["arm"], "base": c["base"]}})
json.dump({"docs": DOCS, "tiles": tiles}, open(sys.argv[1], "w"), indent=1, default=str)
for t in tiles:
    print(t["doc"], t["rule"], t["subject"], (t["our_reading"]["arm"] or {}).get("value"))
print(len(tiles))
