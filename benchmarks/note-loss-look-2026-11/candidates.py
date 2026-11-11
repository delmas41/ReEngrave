"""List the class c/d/e candidates of `classify.py` with place, owner verdict and the twin's fate. Prints only."""
import json
import sys

d = json.load(open(sys.argv[1]))
for plate, rows in d.items():
    for r in rows:
        if r["cls"].startswith(("c_", "d_", "e_group", "e_wide")):
            print(plate, r["cls"], r["reason"], "p%s s%s st%s c%s" % (r["page"], r["system"], r["staff"], r["cell"]),
                  "box", [round(v) for v in r["box"]], "owner", r["owner"], "(%s)" % r["owner_reason"], r["detail"])
