"""2.275: tabulate claims_probe output: per bucket, the kind of claim already on the ink.
holder = the register area owner that covers >= half the box (barline, bracket, leading_column, clef, key_signature, meter, word),
else the stroke owner's family of the box's biggest stroke; `head` = only a detector head box (its own or a neighbour's) holds it; none = no stroke."""
import collections
import json
import sys

plate, path = sys.argv[1:3]
res = json.load(open(path))
SHORT = lambda b: b.replace("refused:", "").replace("not_a_notehead:", "")
tab = collections.defaultdict(collections.Counter)
before = collections.Counter()
for x in res:
    h = x["area_kind"] or (x["stroke_family"] if x["stroke_family"] not in (None, "head") else
                           ("own_head_box_only" if x["stroke_family"] == "head" else "none"))
    tab[SHORT(x["bucket"])][h] += 1
    if x["area_kind"]:
        before[(SHORT(x["bucket"]), x["area_before_box"])] += 1
print(plate)
tot = collections.Counter()
for b, c in sorted(tab.items(), key=lambda kv: -sum(kv[1].values())):
    n = sum(c.values())
    print("  %-40s %5d  %s" % (b, n, ", ".join("%s %d" % kv for kv in c.most_common(8))))
    for k, v in c.items():
        tot[k] += v
print("  ALL", sum(tot.values()), dict(tot.most_common()))
print("  area claim id lower than the box id (claim filed before the box):", {str(k): v for k, v in before.items() if k[1] is not None})
# slash rows
sl = sum(1 for x in res if SHORT(x["bucket"]) == "tremolo_slash_crosses_stem" and x["slash_rows_in_cell"] > 0)
print("  tremolo bucket ink whose cell has a Q.STEM_SLASH row with a slash read:", sl, "of", sum(1 for x in res if SHORT(x["bucket"]) == "tremolo_slash_crosses_stem"))
