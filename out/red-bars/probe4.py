import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, page, system = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
res = load_record(rec)
r = res["record"] if "record" in res else res
for o in r["observations"]:
    s = o.get("subject") or ""
    if o["quantity"] in ("barline_column",) and s.startswith("system/%d/%d" % (page, system)) or (o["quantity"] == "barline_column" and ("/%d/%d" % (page, system)) in s):
        print(json.dumps(o, default=str)[:700])
cells = collections.defaultdict(dict)
for o in r["observations"]:
    if o["quantity"] == "cell_box":
        p = o["subject"].split("/")
        if int(p[1]) == page and int(p[2]) == system:
            cells[int(p[3])][int(p[4])] = [round(x) for x in o["value"][:3:2]]
for st in sorted(cells):
    print("staff", st, [cells[st][k] for k in sorted(cells[st])][-6:])
