import sys,json,collections,glob,os
sys.path.insert(0,'.'); import cmp as C
tags=sys.argv[1:]
allg={}
for t in tags:
    p=f"runs/{t}-on.json"
    if not os.path.exists(p): print("missing",p); continue
    S=C.summary(C.load(p))
    groups=collections.defaultdict(list)
    for k,v in S.items():
        f=v['fit']
        if f and f[2] and 'hollow_pair' in f[2]: groups[k.rsplit('/',1)[0]].append((k,v))
    for g,mem in groups.items():
        nm=mem[0][1]['fit'][2]; kept=mem[0][1]['fit'][1]=='hollow_pair'
        allg[(t,g)]=(kept,nm.get('hollow_pair'),len(mem),nm.get('stem_extension_spaces'),[m[0] for m in mem])
    c=collections.Counter(v[1] for (tt,g),v in allg.items() if tt==t)
    print(t,dict(c))
json.dump({f"{t}|{g}":v for (t,g),v in allg.items()},open('out/hollow_groups.json','w'))
