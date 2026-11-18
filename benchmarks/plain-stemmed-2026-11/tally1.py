import json, collections, sys
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
OUT = {}
for plate, tag, bn in (("litolff", "lit-a", "litolff"), ("brahms", "bra-a", "brahms")):
    f = json.load(open(f"{S}/2311/{tag}.facts.json"))
    items = json.load(open(f"{S}/b311/{bn}.beamnotes.json"))
    g = f["glyphs"]
    bycell = collections.defaultdict(list)
    for k, v in g.items():
        if v.get("head"):
            bycell[k.rsplit("/", 1)[0]].append(k)
    rows = []
    for it in items:
        k = it["key"]
        cellk = k.rsplit("/", 1)[0]
        me = g[k]
        wid = [g[m]["box"][2] - g[m]["box"][0] for m in bycell[cellk]]
        tol = 0.6 * (sum(wid) / len(wid))
        cx = (me["box"][0] + me["box"][2]) / 2
        mates = []
        for m in bycell[cellk]:
            if m == k:
                continue
            gm = g[m]
            if gm["fate"].startswith(("not_a_notehead", "owned_by_another", "mark_group_duplicate")):
                continue
            mx = (gm["box"][0] + gm["box"][2]) / 2
            if abs(mx - cx) <= tol * 1.6:
                mates.append(m)
        def dsc(x):
            v = g[x]["v"]
            d = v.get("duration", {})
            val = d.get("value") or {}
            return dict(key=x, fate=g[x]["fate"], cls=g[x]["head_class"], dur=(val.get("written"), val.get("dots"), val.get("beam_levels")) if val else None,
                        dreason=d.get("reason"), stem=v.get("head_stem", {}).get("value"), hsr=v.get("head_stem", {}).get("reason"),
                        sdir=v.get("stem_direction", {}).get("value"), sdr=v.get("stem_direction", {}).get("reason"),
                        sv=v.get("stem_value", {}).get("reason"), cy=(g[x]["box"][1] + g[x]["box"][3]) / 2, cx=(g[x]["box"][0] + g[x]["box"][2]) / 2)
        r = dict(it=it, me=dsc(k), mates=[dsc(m) for m in mates])
        rows.append(r)
    OUT[plate] = rows
json.dump(OUT, open(S + "/p314/tally1.json", "w"))
for plate, rows in OUT.items():
    c = collections.Counter()
    for r in rows:
        it = r["it"]
        c[(it["mechanism"], len(r["mates"]) > 0)] += 1
    print(plate, len(rows))
    for k, v in sorted(c.items()):
        print("  ", k, v)
