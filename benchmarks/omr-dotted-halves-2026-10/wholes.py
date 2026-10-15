import sys,json,collections; sys.path.insert(0,'.')
from tools.omr.staged import readout as RO
for p in sys.argv[1:]:
    run=RO.load_run(p); c=collections.Counter()
    for g in run.glyphs.values():
        if not (g.cls or '').startswith('noteheadWhole'): continue
        d=run.verdicts_at(g.key,None,'duration'); d0=d[0] if d else None
        hs=run.verdicts_at(g.key,None,'head_stem'); hs=hs[-1] if hs else None
        k=(d0 and d0['outcome'], d0 and d0.get('reason'), hs and hs.get('reason') or (hs and hs['outcome']))
        c[k]+=1
        if k[0]=='decided' and k[2]=='one_stem': print(p,g.key,g.cls,round(g.score or 0,2), (hs.get('detail') or {}).get('flush'),(hs.get('detail') or {}).get('stem_box'),g.box_canon)
    print(p,dict(c))
