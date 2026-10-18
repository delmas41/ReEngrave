"""ROADMAP 2.165 -- judged tiles whose glyph stands on a stem the shared-stem rule touched (`stem_heads_disagree` is held
out at EXPORT, so the duration-reading scorer cannot see it as undecided). usage: judged_stems_2_165.py OUTDIR"""
import json
import sys

D = sys.argv[1]
for doc in ("litolff", "brahms"):
    O = json.load(open("%s/%s.on.json" % (D, doc)))
    J = json.load(open("%s/%s.on.judged.json" % (D, doc)))
    B = json.load(open("%s/%s.base.judged.json" % (D, doc)))
    bs = {(t["item"], str(t["tile"])): t["status"] for t in B["tiles"]}
    for t in J["tiles"]:
        subs = t["subject"] if isinstance(t["subject"], list) else [t["subject"]]
        for s in subs:
            st = O["stems"].get(s)
            if st and st[1] in ("stem_heads_disagree", "stem_heads_one_dissent"):
                print(doc, t["item"], t["tile"], s, st, "base:", bs[(t["item"], str(t["tile"]))], "on:", t["status"],
                      "Sean:", t["answer"])
