"""ROADMAP 2.161 -- one STEM cause and one BOX cause per real-note head of stems_<doc>.json (stems_2_161.py), first match:
STEM (heads with no stem box touching the detector box):
  S1 stem_beside_box   the stem finder FOUND a stem (a `Q.STEM` row) standing within 0.5 sp of the box, rows overlapping,
                        but it does not touch the box (geometry.stem_touches_head)
  S1v stem_off_box_vert the same with the stem above/below the box (columns overlap, rows do not)
  S2.. refused:<why>    no such stem; a vertical run beside/through the head (within 0.35 sp, rows overlapping, >= 1.5 sp
                        long) was refused by the stem finder: PAIRED (the accidental pair rule), TALL (> 8 sp: merged with a
                        barline / another stem), EDGE (at the cell edge), WIDE, SHORT
  S3 no_stem_ink        no vertical ink run >= 1.5 sp beside the head at all (no stem printed, or not a note)
BOX (heads whose detector box is not head-sized): short/tall/wide/narrow (2.159's order) x located (2.115 part-boxed,
  2.73 line cut, 2.39b re-centre) or why not, and what other detector box overlaps it.
usage: causes_2_161.py W161DIR"""
import collections
import json
import os
import sys

W = sys.argv[1]


def stem_cause(r):
    if r["stems_attached"]:
        return None
    for n in r["stems_near"]:
        if not n["touches"] and n["dy_sp"] == 0 and n["dx_sp"] <= 0.5:
            return "S1 stem_beside_box"
    for n in r["stems_near"]:
        if not n["touches"] and n["dx_sp"] == 0 and n["dy_sp"] <= 0.5:
            return "S1v stem_off_box_vertically"
    for n in r["refused_near"]:
        if n["outcome"] != "accepted" and n["dx_sp"] <= 0.35 and n["dy_sp"] == 0 and n["h_sp"] >= 1.5:
            o = n["outcome"]
            tag = ("PAIRED" if "PAIRED" in o else "TALL" if "TALL" in o else "EDGE" if "EDGE" in o
                   else "WIDE" if "WIDE" in o else "SHORT" if "SHORT" in o else o)
            return "S2 refused:" + tag
    if max((v["len_sp"] for v in r["raw_runs"].values()), default=0) >= 1.5:
        return "S2x ink_run_not_a_candidate"
    return "S3 no_stem_ink"


def box_cause(r):
    c = r["cause_2159"]
    if not c.startswith("box"):
        return None
    kind = c.split()[0].replace("box_too_", "")
    if r["line_cut"]:
        loc = "located:line_cut"
    elif r["box_source"] == "part_boxed_recentre":
        loc = "located:part_boxed"
    elif r["recentre"]:
        loc = "located:recentre"
    elif r["part_boxed"]:
        loc = "not_located:2.115_" + str((r["part_boxed"] or {}).get("reason"))
    else:
        loc = "not_located"
    heads = [o for o in r["overlaps"] if o["name"].startswith("notehead") and o["share_of_head"] >= 0.1]
    other = [o for o in r["overlaps"] if not o["name"].startswith(("notehead", "staff", "ledger"))
             and o["share_of_head"] >= 0.3]
    with_ = "with_another_head" if heads else ("with_" + other[0]["name"]) if other else "alone"
    return kind, loc, with_


out = {}
for doc in ("litolff", "brahms"):
    R = json.load(open(os.path.join(W, "stems_%s.json" % doc)))
    sc, bc, bk = collections.Counter(), collections.Counter(), collections.Counter()
    rows = {}
    for s, r in sorted(R.items()):
        a, b = stem_cause(r), box_cause(r)
        rows[s] = dict(stem=a, box=b, crops=r.get("crops"))
        if a:
            sc[a] += 1
        if b:
            bc[b[0] + " | " + b[1]] += 1
            bk[b[0] + " | " + b[2]] += 1
    out[doc] = dict(stem=dict(sc), box_located=dict(bc), box_with=dict(bk), rows=rows)
    print("==", doc, "heads", len(R), "no stem", sum(sc.values()), "box not head-sized", sum(bc.values()))
    for k, v in sc.most_common():
        print("   %-34s %d  %s" % (k, v, [s for s, x in rows.items() if x["stem"] == k][:12]))
    for k, v in sorted(bc.items()):
        print("   box %-44s %d" % (k, v))
    for k, v in sorted(bk.items()):
        print("   box %-44s %d" % (k, v))
json.dump(out, open(os.path.join(W, "causes_2161.json"), "w"), indent=0)
