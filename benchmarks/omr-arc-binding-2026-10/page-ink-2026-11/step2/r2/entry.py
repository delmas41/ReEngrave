"""print the verdict entries of runs: python3 entry.py WORKDIR PLATE PAGE ORD[,ORD]"""
import json
import sys

work, plate, page, ords = sys.argv[1], sys.argv[2], int(sys.argv[3]), [int(x) for x in sys.argv[4].split(",")]
for v in json.load(open("%s/%s.on.extra.json" % (work, plate))):
    if v["subject"] != "page/%d" % page:
        continue
    for r in v["detail"]["runs"]:
        if r["ordinal"] in ords:
            print({k: r[k] for k in r if k not in ("left", "right")})
            print("  L", r.get("left"))
            print("  R", r.get("right"))
