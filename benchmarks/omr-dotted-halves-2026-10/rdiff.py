import json,sys
a=json.load(open(sys.argv[1]))['durations']; b=json.load(open(sys.argv[2]))['durations']
def sig(r):
    if r is None: return None
    if r['outcome']=='decided': v=r['value']; return ('D',v.get('written') if isinstance(v,dict) else v, r['reason'])
    return (r['outcome'][0], tuple(sorted(str(c.get('written')) for c in r['cands'])), r['reason'])
n=0
for k in a:
    if sig(a[k])!=sig(b[k]):
        n+=1; print(k, sig(a[k]), '->', sig(b[k]))
print('changed',n,'of',len(a))
