"""2.306 two-voice piece, for Sean's 2026-11-21 string ruling: which unison family (`export.staff_unison_family` of `Q.PART_NAME`) each staff of
a record's pages takes, and how often it is not known. Usage: twovoice_family.py RECORD.json [staff-key ...]"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged import export as E
rec = json.load(open(sys.argv[1]))
fam = collections.Counter()
by = {}
for v in rec["verdicts"]:
    if v["quantity"] != "part_name":
        continue
    name = v.get("value") if v.get("outcome") == "decided" else None
    f = E.staff_unison_family(name)
    by[v["subject"]] = (name, f, v.get("outcome"))
    fam[f] += 1
print(sys.argv[1].split("/")[-1], "staves", len(by), dict(fam))
for k in sys.argv[2:]:
    print(k, [(s, t) for s, t in by.items() if s.startswith(k)])
