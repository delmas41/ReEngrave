"""ROADMAP 2.153 -- cut a smaller slice (named systems) out of an existing slice file; no record load.
usage: subslice_2_153.py IN.json OUT.json "p,s;p,s" """
import json
import sys

keep = {tuple(int(x) for x in t.split(",")) for t in sys.argv[3].split(";") if t}
rec = json.load(open(sys.argv[1]))


def want(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in keep
    return True


out = {k: [r for r in v if want(r["subject"])] for k, v in rec.items()}
print({k: len(v) for k, v in out.items()})
json.dump(out, open(sys.argv[2], "w"), default=str)
