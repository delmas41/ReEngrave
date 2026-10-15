import sys,json
sys.path.insert(0,'tree')
from tools.omr.staged import record_io, readout as RO
def load(p):
    r=record_io.load_record(p); return RO.run_from_result(r,path=p)
def summary(run):
    out={}
    for k,g in run.glyphs.items():
        if not (g.cls or '').startswith('notehead'): continue
        fit=None; refused=None
        for s,kd,r in run.rows_at(k):
            if r.get('quantity')=='stacked_head_fit' and kd=='observation': fit=(r['value'],(r.get('detail') or {}).get('second_head_by'),(r.get('detail') or {}).get('near_miss'))
            if r.get('quantity')=='notehead_is_not_a_notehead' and kd=='verdict': refused=(r.get('value'),r.get('reason'))
        st,why=RO.adjudicate_status(run,g)
        out[k]=dict(cls=g.cls,fit=fit,refused=refused,adj=st)
    return out
if __name__=="__main__":
    a,b=sys.argv[1],sys.argv[2]
    A=summary(load(a));B=summary(load(b))
    d=[k for k in A if A[k]!=B.get(k)]
    print("noteheads",len(A),len(B),"changed",len(d))
    for k in d: print(k,A[k],'->',B.get(k))
    nm=[(k,B[k]['fit'][2]) for k in B if B[k]['fit'] and B[k]['fit'][2] and 'hollow_pair' in json.dumps(B[k]['fit'][2])]
    print("hollow near-miss rows (ON)",len(nm))
    for k,v in nm: print(k,json.dumps(v)[:300])
