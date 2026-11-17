"""2.274 step 1: collect the per-page summaries of the measurement dirs into results/summaries.json.   python3 summarise.py OUT.json TAG=DIR [TAG=DIR ...]"""
import glob
import json
import os
import sys

out = {}
for a in sys.argv[2:]:
    tag, d = a.split("=")
    out[tag] = {os.path.basename(f).replace(".step1.json", ""): json.load(open(f))["summary"] for f in sorted(glob.glob(d + "/*.step1.json"))}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print({k: len(v) for k, v in out.items()})
