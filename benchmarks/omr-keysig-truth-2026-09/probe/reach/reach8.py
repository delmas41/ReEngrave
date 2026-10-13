import sys,collections,json; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
rows=json.load(open('benchmarks/omr-keysig-truth-2026-09/readers-read.json'))
print(rows[0].keys())
mk=collections.defaultdict(list); tpl=collections.defaultdict(dict); clef={}; keyv={}
for o in rec['observations']:
    q=o['quantity']; s=o['subject']
    if not s.startswith('staff/'): continue
    st=s[6:]
    if q=='keysig_marker': mk[st].append(o)
    elif q=='keysig_template_fit': tpl[st][o['value']]=o['detail']
for v in rec['verdicts']:
    s=v['subject']
    if not s.startswith('staff/'): continue
    st=s[6:]
    if v['quantity']=='clef' and v['outcome']=='decided': clef[st]=v['value']
    if v['quantity']=='key_signature': keyv[st]=v
c=collections.Counter()
for r in rows:
    st=f"{r['page']}/{r['system']}/{r['staff']}"
    ms=mk.get(st,[])
    xs=sorted(m['detail']['x'] for m in ms)
    kinds=sorted({m['value'] for m in ms})
    cf=clef.get(st); t=tpl[st].get(cf) if cf else None
    kv=keyv.get(st)
    truth=r['truth_fifths']
    got=None if kv is None or kv['outcome']!='decided' else kv['value']
    tf=None if t is None else t['fifths']
    c[('staged_right' if (got or 0)==truth else 'staged_wrong')+('/abst' if got is None else '')]+=1
    print(st,r['instrument'][:10].ljust(10),'truth',truth,'staged',got,(kv or {}).get('reason'),'| markers',len(ms),kinds,'| clef',cf,'tpl',tf)
print(c)
