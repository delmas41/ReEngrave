"""Scratch: observations by id and/or by subject prefix, optional quantity filter, compact.
usage: jm_q2.py REC IDS|- PREFIXES QUANTITIES|-"""
import sys, json, pathlib
sys.path.insert(0, '.')
from tools.omr.staged import judged as J
rec = pathlib.Path(sys.argv[1])
ids = set(sys.argv[2].split(',')) if sys.argv[2] != '-' else set()
prefixes = sys.argv[3].split(',')
quants = set(sys.argv[4].split(',')) if len(sys.argv) > 4 and sys.argv[4] != '-' else None
n = 0
for o in J.iter_array(rec, "observations"):
    n += 1
    sub = o.get("subject") or ""
    if o.get("id") in ids or (any(sub.startswith(p) for p in prefixes)
                              and (quants is None or o.get("quantity") in quants)):
        d = o.get("detail") or {}
        print(o.get("id"), sub, o.get("quantity"), json.dumps(o.get("value")), o.get("reader"), json.dumps(d)[:420])
print("scanned", n, file=sys.stderr)
