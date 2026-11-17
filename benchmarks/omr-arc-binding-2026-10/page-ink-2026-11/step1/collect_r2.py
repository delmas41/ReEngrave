"""2.274 r2: collect the per-page summaries of the measure outputs into results-r2/summaries.json.   python3 collect_r2.py OUT.json NAME=DIR [NAME=DIR ...]"""
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
res = {}
for kv in sys.argv[2:]:
    name, d = kv.split("=")
    res[name] = {p.name.replace(".step1.json", ""): json.load(open(p))["summary"] for p in sorted(pathlib.Path(d).glob("*.step1.json"))}
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(res, open(out, "w"), indent=1)
print({k: len(v) for k, v in res.items()})
