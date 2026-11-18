import json
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
POP = json.load(open(S + "/p314/pop.json"))
sel = json.load(open(S + "/p314/look/sel.json"))
for plate in ("litolff", "brahms"):
    byk = {r["it"]["key"]: r for r in POP[plate]}
    for i, k in enumerate(sel[plate], 1):
        r = byk[k]
        it, me = r["it"], r["me"]
        def s(m):
            st = (m["stem"] or "-")[-5:]
            d = m["dur"]
            return "%s %s st=%s %s dur=%s %s" % (m["key"].rsplit("/", 1)[1], m["cls"].replace("notehead", ""), st, m["sdir"], d, m["fate"][:14])
        print("%s#%d %s | %s | " % (plate[:3], i, k, it["mechanism"][:24]) + s(me) + " || " + " ; ".join(s(m) for m in r["mates"] if not m["fate"].startswith(("not_a", "mark_group"))))
