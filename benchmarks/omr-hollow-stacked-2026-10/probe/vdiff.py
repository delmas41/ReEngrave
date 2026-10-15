import sys,json,collections
sys.path.insert(0,'tree')
from tools.omr.staged import record_io, readout as RO
def verd(p):
    run=RO.run_from_result(record_io.load_record(p),path=p); d={}
    for sub,lst in run.by_subject.items():
        for stage,kind,r in lst:
            if kind=='verdict' and r.get('quantity') not in ('stacked_head_fit',):
                d[(sub,r.get('quantity'))]=(str(r.get('value'))[:120],r.get('reason'))
    return d,run
A,ra=verd(sys.argv[1]);B,rb=verd(sys.argv[2])
c=collections.Counter(); ex={}
for k in set(A)|set(B):
    if A.get(k)!=B.get(k):
        c[k[1]]+=1; ex.setdefault(k[1],[]).append((k[0],A.get(k),B.get(k)))
print(c)
for q in c:
    if q in sys.argv[3:] or q.startswith(('arc','tie')):
        for e in ex[q][:6]: print(q,e)
