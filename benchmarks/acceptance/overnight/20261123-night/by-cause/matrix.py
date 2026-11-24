import json,sys,collections
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-reengrave-manager-20261124-12f953/35f75218-68a4-4d67-aae9-7c7cdda49059/scratchpad/bc/"
for plate in ("lit","br"):
    d=json.load(open(S+"cause-%s.json"%plate))
    own=collections.defaultdict(collections.Counter); bar=collections.defaultdict(collections.Counter); other=collections.Counter()
    tot=collections.Counter()
    for kind,side,page,lab,rg in d["per"]:
        tot[(kind,side)]+=1
        if lab in("none-found","loose/no-glyph"): other[(lab,kind,side)]+=1; continue
        if lab.startswith("bar:"):
            for c in lab[4:].split("+"): bar[c][(kind,side)]+=1/len(lab[4:].split("+"))
        else:
            cs=lab.split("+")
            for c in cs: own[c][(kind,side)]+=1/len(cs)
    print("=====",plate)
    for c in sorted(own):
        print("OWN",c,{"%s %s"%(k[0],k[1][:1]):round(v) for k,v in sorted(own[c].items(),key=lambda x:-x[1]) if v>=0.5})
    for c in sorted(bar):
        print("BAR",c,{"%s %s"%(k[0],k[1][:1]):round(v) for k,v in sorted(bar[c].items(),key=lambda x:-x[1]) if v>=0.5})
    print("OTHER",{"%s|%s %s"%k:v for k,v in other.most_common(14)})
    print("TOTAL changes",sum(tot.values()))
