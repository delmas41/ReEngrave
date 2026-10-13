import sys,collections; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
c=collections.Counter(); per=collections.defaultdict(list)
for v in rec['verdicts']:
    if v['quantity']=='key_signature' and v['subject'].startswith('staff/'):
        c[(v['outcome'],v['value'],v['reason'])]+=1
        p=v['subject'].split('/')
        per[(p[1],p[2])].append((p[3],v['value'],v['reason']))
for k,n in sorted(c.items(),key=lambda x:-x[1])[:25]: print(n,k)
print('systems',len(per))
bad=0
for sy,l in sorted(per.items()):
    ks={v for _,v,r in l if r=='markers'}
    if len(ks)>1:
        bad+=1; print(sy,[(s,v,r) for s,v,r in l if r=='markers'])
print('systems with conflicting marker keys',bad)
