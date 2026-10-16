"""ROADMAP 2.153 -- classify each judged note tile's reading (from tag_notes_2_153.py outputs) into a MECHANISM class, and
tabulate right / wrong-decided / narrowed per class. usage: mech_2_153.py ARM TAGS.json [TAGS.json ...]"""
import collections
import json
import sys

ARM = sys.argv[1]
rows = []
for p in sys.argv[2:]:
    d = json.load(open(p))[ARM]
    for g, x in d.items():
        if x.get("missing"):
            continue
        x = dict(x, glyph=g, src=p)
        rows.append(x)


def mech(x):
    f = x["feats"] or {}
    ours, sean = x["ours"], x["beats"]
    lc, bj = f.get("levels_certain") or 0, f.get("beams_by_stem") or 0
    fl = f.get("flag_levels") or 0
    if x["is_rest"]:
        return "rest"
    tags = []
    if x["first_reason"] in ("head_and_marks", "hooks_counted"):
        if fl:
            tags.append("flag_read")
        elif lc > 0 and bj == 0:
            tags.append("A0_levels_no_joined_stroke")
        elif lc > bj > 0:
            tags.append("A1_levels_exceed_joined")
        elif lc > 0 and (f.get("beams_neighbour_staff") or f.get("beams_decided_arc")):
            tags.append("B_joined_stroke_arc_near")
        elif lc > 0:
            tags.append("beam_joined_clean")
        elif f.get("beam_evidence") == "reader_declined":
            tags.append("C_no_beam_reader_declined")
        else:
            tags.append("no_beam_no_flag")
    else:
        tags.append("first=%s" % x["first_reason"])
    return "+".join(tags)


tab = collections.defaultdict(collections.Counter)
for x in rows:
    m = mech(x)
    if x["outcome"] == "decided":
        k = "right" if x["right"] else "WRONG"
    elif x["outcome"] == "narrowed":
        k = "narrowed_holding" if x["right"] else "narrowed_NOT"
    else:
        k = x["outcome"]
    tab[m][k] += 1
    x["mech"] = m
for m, c in sorted(tab.items(), key=lambda kv: -sum(kv[1].values())):
    print("%4d %-34s %s" % (sum(c.values()), m, dict(c)))
if "-v" in sys.argv:
    pass
json.dump(rows, open("out/2.153/mech_rows_%s.json" % ARM, "w"), indent=0, default=str)
