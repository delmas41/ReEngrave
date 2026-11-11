"""2.280 r3: class (ii) heads (stem row, no beam/flag read, value narrowed): is the tip window clean, and what did the bare-stem rule say? usage: class_ii.py HEADS.jsonl"""
import collections
import json
import subprocess
import sys

heads = sys.argv[1]
tmp = "/private/tmp/claude-501/cii.json"
subprocess.run([sys.executable, "benchmarks/stems-rerun-2026-11/chain.py", heads, "--list", tmp], stdout=subprocess.DEVNULL, check=True)
subs = set(json.load(open(tmp)).get("(ii) ", []))
c = collections.Counter()
for l in open(heads):
    r = json.loads(l)
    if r["sub"] in subs:
        d = r["d"] or {}
        c[(r["duration"][1], "tip_window_clean=%s" % d.get("bare_stem_tip_window_clean"), "evidence_holds=%s" % d.get("bare_stem_evidence_holds"),
           "likelihood=%s" % d.get("bare_stem_likelihood"), "cv_beams=%s yolo_kept=%s" % (d.get("cv_beams"), d.get("yolo_kept")))] += 1
for k, v in c.most_common():
    print(v, k)
