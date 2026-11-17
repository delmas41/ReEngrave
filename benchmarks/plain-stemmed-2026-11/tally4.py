import json, collections
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
POP = json.load(open(S + "/p314/pop.json"))
sel = json.load(open(S + "/p314/look/sel.json"))


def cls(r):
    it, me = r["it"], r["me"]
    if it["mechanism"] == "no_stem_attached_to_the_head":
        if me["sdir"] or any(m["stem"] for m in r["mates"]):
            return "single head, no stem joined (a stem direction known)"
        return "single head, no stem joined"
    grp = [me] + [m for m in r["mates"] if m["fate"] == "chord_value_undecided"]
    stems = {m["stem"] for m in grp if m["stem"]}
    nost = [m for m in grp if not m["stem"]]
    durs = {tuple(m["dur"]) for m in grp if m["dur"]}
    if len(stems) >= 2:
        return "two stems at one place (two voices / unison)"
    if len(stems) == 1 and not nost:
        return "one stem, members' values differ"
    if len(stems) == 1:
        return "one member joined to a stem, another not"
    return "chord, no member joined to a stem"


for scope in ("all", "look"):
    tot = collections.Counter()
    for plate in ("litolff", "brahms"):
        c = collections.Counter()
        for r in POP[plate]:
            if scope == "look" and r["it"]["key"] not in sel[plate]:
                continue
            c[cls(r)] += 1
        print(scope, plate, sum(c.values()))
        for k, v in c.most_common():
            print("    %3d  %s" % (v, k))
        tot.update(c)
    print(scope, "BOTH", sum(tot.values()), [(k, v) for k, v in tot.most_common()])
