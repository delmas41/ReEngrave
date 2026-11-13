"""Print, for one bar (page system staff cell), each glyph's head_stem / stem_direction / event / voices / duration OFF vs ON, and the written hosts.
Usage: diag_bar.py PREFIX p s st c"""
import sys, json, collections
pre = sys.argv[1]
bar = tuple(int(x) for x in sys.argv[2:6])
pref = "glyph/%d/%d/%d/%d/" % bar
cpref = "cell/%d/%d/%d/%d" % bar
for arm in ("off", "on"):
    D = json.load(open("%s.%s.json" % (pre, arm)))
    by = collections.defaultdict(dict)
    for v in D["verdicts"]:
        if v["s"].startswith(pref) or v["s"] == cpref:
            by[v["s"]][v["q"]] = v
    print("====", arm)
    for s in sorted(by, key=lambda k: (len(k), k)):
        q = by[s]
        hs, sd, du = q.get("head_stem"), q.get("stem_direction"), q.get("duration")
        nn = q.get("notehead_is_not_a_notehead")
        if hs is None and sd is None:
            if s == cpref:
                for k in ("event", "voices"):
                    if k in q:
                        print("  CELL", k, q[k]["o"], q[k]["r"], json.dumps(q[k]["v"], default=str)[:300])
            continue
        print("  ", s, "| refused" if nn and nn["v"] is True else "",
              "| hs", hs and (hs["o"], hs["r"], hs["v"], (hs.get("d") or {}).get("direction"), (hs.get("d") or {}).get("page_stroke")),
              "| dir", sd and (sd["o"], sd["r"], sd["v"]), "| dur", du and (du["o"], du["r"], (du["v"] or {}).get("written") if isinstance(du["v"], dict) else du["v"]))
    hosts = [h for h in D["hosts"] if (h.get("rg") or "").startswith(pref)]
    for h in hosts:
        print("   WROTE", h.get("rg"), h.get("kind"), h.get("pitch"), h.get("onset"), h.get("type") or "", dict((k, v) for k, v in (h.get("sub") or {}).items() if v), h.get("voice"))
