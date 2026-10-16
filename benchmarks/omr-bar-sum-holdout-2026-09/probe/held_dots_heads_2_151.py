"""ROADMAP 2.151 -- head-centric reading of `held_dots_2_151.py`'s output: in each held voice's cell, every kept head
whose live duration carries NO dot and that has a dot mark in its augmentation place (the mark's left edge -0.1..1.5 sp
right of the head, centre within 0.8 sp of the head's centre, and NOT centred over another head of the cell -- a
staccato's place). The mark's role verdict says why the head took no dot. Brahms page px, 33 per staff space.
usage: held_dots_heads_2_151.py HELD_DOTS.json"""
import collections, json, sys

SP = 33.0
rows = json.load(open(sys.argv[1]))
per_deficit = collections.defaultdict(collections.Counter)
cells_with = collections.Counter()
examples = collections.defaultdict(list)
for r in rows:
    b = r["bar"]
    heads = [h for h in r["heads"] if h.get("bbox")]
    found = collections.Counter()
    for d in r["dots"]:
        if d.get("as_head"):
            found["dot_boxed_as_a_refused_head"] += 1
            examples["dot_boxed_as_a_refused_head"].append((d["glyph"], d["head"]))
            continue
        db = d.get("bbox")
        if not db:
            continue
        cx, cy = (db[0] + db[2]) / 2, (db[1] + db[3]) / 2
        if any(abs(cx - (h["bbox"][0] + h["bbox"][2]) / 2) <= 0.5 * SP
               and 0.5 * SP <= abs(cy - (h["bbox"][1] + h["bbox"][3]) / 2) <= 2.0 * SP for h in heads):
            continue                        # centred over/under a head: a staccato's place
        for h in heads:
            hb = h["bbox"]
            gap, dy = (db[0] - hb[2]) / SP, (cy - (hb[1] + hb[3]) / 2) / SP
            if -0.1 <= gap <= 1.5 and abs(dy) <= 0.8:
                if h["outcome"] == "decided" and not h["dots"]:
                    role = d["role"] or "no_role"
                    if role == "augmentation":
                        role = "augmentation_named_" + ("this_head" if d["head"] == h["glyph"] else
                                                        ("a_refused_or_other_head" if d["head"] else "no_head"))
                    found["undotted_head_with_dot:" + role] += 1
                    examples[role].append((d["glyph"], h["glyph"]))
                break
    for k in found:
        cells_with[k] += 1
    for q in b["quarters"]:
        deficit = round(q - b["want_quarters"], 3)
        for k in found:
            per_deficit[deficit][k] += 1
print("held cells with each kind (a cell counted once per kind):")
for k, n in cells_with.most_common():
    print("  %4d %s" % (n, k))
for deficit in (-0.5, -1.0, -1.5, 0.5, 1.0):
    print("deficit %+.2f" % deficit, dict(per_deficit[deficit]))
for k, ex in examples.items():
    print(k, ex[:6])
