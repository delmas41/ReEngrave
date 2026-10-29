import json, sys
for plate in ("litolff", "brahms"):
    I = json.load(open("out/red-bars/work/%s.interior.json" % plate))
    C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
    red = {c["key"]: c for c in C}
    def rate(sel):
        ks = [k for k in I if sel(k)]
        return sum(1 for k in ks if I[k]), len(ks)
    print(plate, "non-red cells", rate(lambda k: k not in red), "red short", rate(lambda k: k in red and not red[k]["over"]), "red over", rate(lambda k: k in red and red[k]["over"]))
    # short pairs
    sp = [k for k in red if not red[k]["over"] and I.get(k)]
    print("  short red with interior:", len(sp), sp[:12])
    op = [k for k in red if red[k]["over"] and I.get(k)]
    print("  over red with interior:", len(op), op[:12])
