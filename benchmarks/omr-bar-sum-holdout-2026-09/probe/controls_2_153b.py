"""ROADMAP 2.153b -- joined-beam control pool: stored live duration verdicts DECIDED an eighth by the reader (`head_and_marks`)
with one beam level that its stem reaches (`beams_by_stem` >= 1, `stems_attached` >= 1, no flag, no dot). The tile cutter
drops any the flag changes. Such a note can still be wrong (our eighth is our reading), so it is a control that can fail.
usage: controls_2_153b.py DOC SLICEDIR -> out/2.153b/controls_<doc>.json {glyph: brief}"""
import collections
import glob
import json
import os
import sys

DOC, SD = sys.argv[1:3]
chains = collections.defaultdict(list)
for p in glob.glob(os.path.join(SD, DOC, "p*.verdicts.jsonl")):
    for line in open(p):
        v = json.loads(line)
        if v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
out = {}
for g, ch in chains.items():
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    v = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    val, d = (v["value"] if isinstance(v["value"], dict) else {}), (v.get("detail") or {})
    if (v["outcome"] == "decided" and v.get("reason") == "head_and_marks" and val.get("beats") == 0.5
            and val.get("dots") == 0 and val.get("beam_levels") == 1 and (d.get("beams_by_stem") or 0) >= 1
            and (d.get("stems_attached") or 0) >= 1 and not d.get("flags_attached")):
        out[g] = dict(outcome="decided", written=val.get("written"), dots=0, beats=0.5, decider=v.get("decider"),
                      reason=v["reason"], cands=None)
json.dump(out, open("out/2.153b/controls_%s.json" % DOC, "w"))
print(DOC, "joined-beam eighth controls", len(out))
