"""2.280 r2: which labelled / seeded heads of the 2.280 micro test are no longer a KEPT head after re-adjudication, and why (the new verdict's reason).
usage: q1_gone.py plate REC_DIR POP_DIR"""
import collections
import json
import sys

plate, rec, popd = sys.argv[1:4]
old = {r["sub"]: r for r in json.load(open("out/2.280/pop_%s.json" % plate))}
new = {r["sub"] for r in json.load(open("%s/pop_%s.json" % (popd, plate)))}
lab = json.load(open("out/2.280/labels_%s.json" % plate))
print(plate, "old kept", len(old), "new kept", len(new), "dropped", len(set(old) - new), "added", len(new - set(old)))
print("labels", dict(collections.Counter(lab.values())))
gone = [s for s in lab if s not in new]
print("labelled and gone now:", dict(collections.Counter(lab[s] for s in gone)))
reasons = {}
for line in open(rec + "/verdicts.jsonl"):
    if '"notehead_is_not_a_notehead"' in line:
        v = json.loads(line)
        if v["subject"] in lab or v["subject"] in old:
            reasons[v["subject"]] = (v["outcome"], v["reason"])
for s in gone:
    print("  ", s, lab[s], reasons.get(s))
dropped = collections.Counter(reasons.get(s, ("?", "?"))[1] for s in old if s not in new)
print("all dropped heads by new reason:", dict(dropped))
