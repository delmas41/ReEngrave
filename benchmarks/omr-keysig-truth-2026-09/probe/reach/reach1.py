import sys,collections; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
cellsp={}; boxes=collections.defaultdict(list)
for o in rec['observations']:
    q=o['quantity']
    if q=='cell_staff_space' and o['subject'].endswith('/0'):
        cellsp[o['subject'][5:]]=o['value']
    elif q=='glyph_box':
        s=o['subject'].split('/')
        if s[4]=='0': boxes['/'.join(s[1:4])].append((s[5],o['value'],o['score'],o['id']))
n_staff=0; hits=collections.Counter(); ex=[]
for st,bl in boxes.items():
    sp=cellsp.get(st+'/0')
    if not sp: continue
    n_staff+=1
    keys=[b for b in bl if b[1][0].startswith('key')]
    if not keys: continue
    x0=min(b[1][1] for b in keys); x1=max(b[1][1]+b[1][3] for b in keys)
    for gi,v,sc,i in bl:
        c=v[0]
        if c.startswith('key'): continue
        cx=v[1]+v[3]/2
        if x0-0.3*sp<=cx<=x1+0.3*sp:
            hits[c]+=1
            if c.startswith('rest') or c.startswith('notehead'): ex.append((st,gi,v,round(sc,2),(x0,x1),sp))
print('staves',n_staff,'with-key-boxes',sum(1 for st,bl in boxes.items() if any(b[1][0].startswith('key') for b in bl)))
print(hits.most_common())
for e in ex[:60]: print(e)
