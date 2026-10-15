"""2.130 replay: re-decide the DURATION chain on a saved GATHER with the code under --root; env flags decide the arm.
usage: replay.py REC.json --root TREE --out OUT.json"""
import argparse, json, sys, os
from pathlib import Path
def replay(record, root):
    sys.path.insert(0, root)
    from tools.omr.staged import adjudicate, adjudicators  # noqa
    from tools.omr.staged.record import Log, Q, Subject
    from tools.omr.staged.record_io import load_record
    adjudicate._ensure_decisions()
    chain={Q.DURATION,Q.STEM_VALUE,Q.HEAD_STEM}; todo=list(chain)
    while todo:
        spec=adjudicate.REGISTRY.get(todo.pop())
        if spec is None: continue
        for w in list(spec.wants)+([spec.subjects_from] if spec.subjects_from else []):
            if w in adjudicate.REGISTRY and w not in chain: chain.add(w); todo.append(w)
    order=[q for q in adjudicate.ORDER if q in chain]
    keep=set()
    for q in order:
        keep.update(adjudicate.REGISTRY[q].wants); keep.add(adjudicate.REGISTRY[q].subjects_from or q)
    keep.add(Q.MARK_GROUP); keep.discard(None)
    data=load_record(record); rec=data.get("record",data)
    log=Log()
    rows=[(r,"obs") for r in rec["observations"] if r["quantity"] in keep]+[(r,"abs") for r in rec.get("abstentions",[]) if r["quantity"] in keep]
    rows.sort(key=lambda t:t[0]["id"])
    for r,kind in rows:
        sub=Subject.from_key(r["subject"]); detail=dict(r.get("detail") or {})
        if kind=="obs": log.observe(sub,r["quantity"],r["value"],reader=r["reader"],frame=r["frame"],score=r.get("score"),**detail)
        else: log.abstain(sub,r["quantity"],reader=r["reader"],frame=r["frame"],reason=r["reason"],**detail)
    log.freeze(); adjudicate.run(log,order=order)
    out={}
    for o in rec["observations"]:
        if o["quantity"]!=Q.NOTEHEAD_CLASS: continue
        k=o["subject"]; v=log.verdict(Q.DURATION,Subject.from_key(k))
        if v is None: out[k]=None; continue
        cands=[c.value if hasattr(c,'value') else c for c in (getattr(v,'candidates',None) or [])]
        out[k]=dict(outcome=v.outcome.value,reason=v.reason,value=json.loads(json.dumps(v.value,default=str)),
                    cands=json.loads(json.dumps(cands,default=str)))
    saved={}
    for v in rec["verdicts"]:
        if v["quantity"]==Q.DURATION: saved[v["subject"]]=v
    # control: first-decider saved verdicts (ADJUDICATE) vs rebuilt for subjects the saved record also held (last saved is 2.127's narrowing, same code path)
    same=tot=0
    for k,v in saved.items():
        if k not in out or out[k] is None: continue
        tot+=1; r=out[k]
        if r["outcome"]==v["outcome"] and r["reason"]==v.get("reason"): same+=1
    return dict(durations=out, control=[same,tot])
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("record"); ap.add_argument("--root",default="."); ap.add_argument("--out")
    a=ap.parse_args(); res=replay(a.record,str(Path(a.root).resolve()))
    Path(a.out).write_text(json.dumps(res)); print(a.out,"control(same,total)",res["control"], "n",len(res["durations"]))
