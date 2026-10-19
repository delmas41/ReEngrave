"""2.167 probe 5: what does `head_stem: no_stem` cost a KEPT head? Compare kept heads with no stem against kept heads with a stem,
by exporter fate and by duration verdict reason. usage: p5_cost.py ROWS.jsonl"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]


def kept(r):
    return (not r["fate"].startswith("not_a_notehead") and r["fate"] not in ("owned_by_another_staff", "ink_is_a_whole_rest",
                                                                         "mark_group_duplicate"))


def hs(r):
    return (r["head_stem"] or ["none", "none"])[1]


groups = {"no_stem": [], "stemmed": [], "other_join": []}
for r in rows:
    if not kept(r):
        continue
    h = hs(r)
    groups["no_stem" if h == "no_stem" else "stemmed" if h in ("one_stem", "stem_by_side", "stem_by_reach", "stem_by_flush",
                                                                "stem_by_one_per_head") else "other_join"].append(r)
for g, v in groups.items():
    n = len(v)
    f = collections.Counter(("written_in_file" if r["fate"] == "written" and not r["held_cell"] and not r["partial_cell"]
                             else "held_bar" if r["fate"] == "written" and r["held_cell"]
                             else "partial_bar" if r["fate"] == "written" else r["fate"]) for r in v)
    print("==", g, n)
    for k, c in f.most_common():
        print("   %-28s %5d %5.1f%%" % (k, c, 100.0 * c / n))
    dr = collections.Counter((r["duration"] or ["-", "-", "-"])[0] + ":" + str((r["duration"] or ["-", "-"])[1]) for r in v)
    for k, c in dr.most_common(8):
        print("      duration %-45s %5d" % (k, c))
    cl = collections.Counter(r["cls"] for r in v)
    print("      classes", dict(cl.most_common(6)))
# whole-class heads overall
w = [r for r in rows if "Whole" in r["cls"]]
print("== whole-class boxes", len(w), collections.Counter(hs(r) for r in w), collections.Counter(r["fate"] for r in w))
