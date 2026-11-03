"""Every written host that differs (pitch or blue) between the cross OFF and ON symbols files, by rg."""
import json
import sys

W = sys.argv[1]
for plate in ("litolff", "brahms"):
    off = {h["rg"]: h for h in json.load(open("%s/%s.off.symbols.json" % (W, plate)))["hosts"] if h.get("rg")}
    on = {h["rg"]: h for h in json.load(open("%s/%s.on.symbols.json" % (W, plate)))["hosts"] if h.get("rg")}
    for rg in sorted(set(off) | set(on)):
        a, b = off.get(rg), on.get(rg)
        if a is None or b is None or a.get("pitch") != b.get("pitch") or a.get("blue") != b.get("blue"):
            print(plate, rg, "OFF", a and (a.get("pitch"), a.get("blue")), "ON", b and (b.get("pitch"), b.get("blue")),
                  "page", (a or b)["page"], [round(v) for v in (a or b)["box"]], (a or b).get("part"), (a or b).get("measure"))
