"""ROADMAP 2.161 (from 2.159's) -- fold a replay: control, the changes (ADJUDICATE first verdict and live, OFF -> ON), the litolff-unread-35
crop heads, and Sean's judged tiles (every judged duration glyph of that doc whose reading moved; the rest are unchanged by
construction -- an unchanged verdict cannot change a judged result).
usage: sum_replay_2_161.py OUTDIR DOC   (reads OUTDIR/replay2161_<doc>.json)"""
import collections
import json
import os
import sys

OUT, DOC = sys.argv[1:3]
R = json.load(open(os.path.join(OUT, "replay2161_%s.json" % DOC)))
ctl = collections.Counter()
for p in R["pages"].values():
    ctl.update(p["control"])
print(DOC, "CONTROL off-arm first ADJUDICATE duration vs stored:", dict(ctl), "| pages", len(R["pages"]))


def s(b):
    if b is None:
        return "-"
    return "%s %s%s %s" % (b["outcome"], b["written"] if b["written"] is not None else b["cands"],
                           " dots%s" % b["dots"] if b.get("dots") else "", b["reason"])


ch = R["changed"]
kinds = collections.Counter()
for g, c in ch.items():
    kinds[(s(c["adj_off"]).split(" ")[0] + " " + (c["adj_off"] or {}).get("reason", "?"), s(c["adj_on"]))] += 1
print("changed glyphs:", len(ch))
for k, v in kinds.most_common():
    print("  %3d  %s  ->  %s" % (v, k[0], k[1]))
hf = json.load(open(os.path.join(OUT, "%s_hf.json" % DOC)))
hfs = {r["subject"] for r in hf["hf"]}
dec_half = [g for g, c in ch.items() if (c["adj_on"] or {}).get("outcome") == "decided" and (c["adj_on"] or {}).get("written") in (2.0, 3.0)]
print("decided half on (ADJUDICATE):", len(dec_half), "of them head_fill_from_ink before:", len(set(dec_half) & hfs),
      "| live decided half:", sum(1 for g, c in ch.items() if (c["live_on"] or {}).get("outcome") == "decided"
                                  and (c["live_on"] or {}).get("written") in (2.0, 3.0)))
moved_down = [g for g, c in ch.items() if (c["adj_on"] or {}).get("written") is not None
              and (c["adj_on"] or {}).get("written") < 2.0]
print("any change that writes SHORTER than a half (a hollow head called black):", moved_down)
if DOC == "litolff":
    crops = {}
    for t in json.load(open("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/start-here-go-cbd2bc/out/print/"
                            "litolff-unread-35/index.json")):
        if t["n"] <= 22:
            crops.setdefault("glyph/%d/%d/%d/%d/" % (t["page"], t["system"], t["staff"], t["cell"]), []).append(t["n"])
    rec = 0
    for g in sorted(hfs):
        n = crops.get(g.rsplit("/", 1)[0] + "/")
        if n:
            c = ch.get(g)
            on = s(c["adj_on"]) if c else "unchanged (narrowed head_fill_from_ink)"
            rec += bool(c and g in dec_half)
            print("  crop", n, g, "->", on)
    print("crop heads recovered as decided halves:", rec)
J = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
jt = [t for t in J if t.get("doc") == DOC and t.get("subject") in ch and t.get("answer_kind") == "duration"]
others = [t for t in J if t.get("doc") == DOC and t.get("subject") in ch and t.get("answer_kind") != "duration"]
print("judged tiles whose reading moved:", len(jt), "duration +", len(others), "other")
for t in jt + others:
    c = ch[t["subject"]]
    print("  %s %s Sean=%r (%s)  off: %s  | on: %s" % (t["item"], t["tile"], t["answer"], t.get("value"), s(c["adj_off"]),
                                                     s(c["adj_on"])))
