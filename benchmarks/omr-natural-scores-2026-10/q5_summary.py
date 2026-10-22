"""Summarise q5 json: per model x class group (human-boxed natural / flat / sharp): n, median own-row score, fraction >= .25 (production's conf floor), >= .05."""
import json, sys, collections
r = json.load(open(sys.argv[1]))
HOLLOW_TRAIN = ("v1-", "v2-", "v3-", "v4-")      # cells hollow-ft saw with these accidentals boxed (train split mixed with val; see FINDINGS)
def rep(rows, title):
    print("\n##", title)
    print("%-17s %-8s %4s %6s %8s %8s" % ("model", "group", "n", "med", ">=.25", ">=.05"))
    for m in dict.fromkeys(x["model"] for x in rows):
        for g in ("natural", "flat", "sharp"):
            v = sorted(x["own"] for x in rows if x["model"] == m and x["grp"] == g)
            if v:
                print("%-17s %-8s %4d %6.3f %7.2f %8.2f" % (m, g, len(v), v[len(v) // 2], sum(a >= .25 for a in v) / len(v), sum(a >= .05 for a in v) / len(v)))
rep(r, "ALL human-boxed accidentals (v1-v4, v14-v22)")
rep([x for x in r if x["ver"].startswith(HOLLOW_TRAIN)], "v1-v4 only (labels hollow-ft trained on)")
rep([x for x in r if not x["ver"].startswith(HOLLOW_TRAIN)], "v14-v22 only (hollow-ft did NOT see these boxes; v14-v18 cells overlap v7/v8 where they were unboxed)")
