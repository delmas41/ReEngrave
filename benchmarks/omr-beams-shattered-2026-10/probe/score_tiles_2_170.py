"""2.170: score Sean's 2.170-review answers (beats) against each replay arm's standing duration verdict (the judged indexer has
no comparator for numeric answers). usage: score_tiles_2_170.py REPLAYDIR ARM[,ARM...] [DOCS]"""
import json
import sys
from pathlib import Path

RD, ARMS = Path(sys.argv[1]), sys.argv[2].split(",")
DOCS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["litolff", "brahms"]
ans = json.load(open("out/print/2.170-review/answers.json"))["answers"]
man = {t["n"]: t for t in json.load(open("out/print/2.170-review/manifest.json"))["tiles"]}
for arm in ARMS:
    tally = {"right": 0, "wrong": 0, "narrowed": 0, "other": 0}
    rows = []
    for n, t in sorted(man.items()):
        if t["doc"] not in DOCS:
            continue
        g = json.load(open(RD / ("%s.%s.json" % (t["doc"], arm))))["glyphs"].get(t["subject"])
        a = ans.get(str(n))
        if not isinstance(a, (int, float)) or g is None:
            st = "other"
        elif g["outcome"] != "decided":
            st = "narrowed"
        else:
            st = "right" if abs((g["beats"] or 0) - a) < 1e-6 else "wrong"
        tally[st] += 1
        rows.append("%d %s %s Sean=%s ours=%s/%s" % (n, t["doc"], st, a, g and g["outcome"], g and g["beats"]))
    print(arm, tally)
    for r in rows:
        print("   ", r)
