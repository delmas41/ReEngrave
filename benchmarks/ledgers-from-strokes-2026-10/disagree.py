import json,sys,collections
base=sys.argv[1]
for plate in ("litolff","brahms"):
    d=base+"/"+plate
    A={};B=collections.defaultdict(list);C={};D={}
    Dabs=collections.Counter();Pabs=collections.Counter();Pobs=0;Dobs=0
    heads_far=set()
    for line in open(d+"/observations.jsonl"):
        if '"glyph_ladder"' in line or '"ledger_rung_ink"' in line or '"ledger_owner_density"' in line or '"far_head_owner_ledger"' in line or '"far_head_ledger_position"' in line:
            r=json.loads(line);q=r["quantity"];det=r["detail"] or {};k=(r["subject"],det.get("candidate"))
            if q=="glyph_ladder":
                if det.get("expected",0)>0:A[k]=bool(r["value"])
            elif q=="ledger_rung_ink":B[k].append(bool(r["value"]))
            elif q=="ledger_owner_density":C[k]=float(r["value"])>=0.15
            elif q=="far_head_owner_ledger":
                nl="no_ledger_needed" in str(det.get("ledger_reason"))
                if not nl: D[k]=True
                Dobs+=1
            elif q=="far_head_ledger_position":Pobs+=1
    for line in open(d+"/abstentions.jsonl"):
        if '"far_head_owner_ledger"' in line or '"far_head_ledger_position"' in line:
            r=json.loads(line);det=r["detail"] or {};k=(r["subject"],det.get("candidate"))
            if r["quantity"]=="far_head_owner_ledger":
                D[k]=False;Dabs[r["reason"]]+=1
            else:Pabs[r["reason"]]+=1
    Bp={k:all(v) for k,v in B.items()}
    keys=set(A)|set(Bp)|set(C)|set(D)
    n=dis=0;pat=collections.Counter()
    for k in keys:
        vals=[("A",A.get(k)),("B",Bp.get(k)),("D",D.get(k))]
        got=[(n_,v) for n_,v in vals if v is not None]
        if len(got)<2:continue
        n+=1
        if len({v for _,v in got})>1:
            dis+=1;pat["".join(n_+("+" if v else "-") for n_,v in got)]+=1
    print(plate,"cands with >=2 readings",n,"disagree",dis,"%.1f%%"%(100*dis/max(n,1)))
    print("  top patterns",pat.most_common(8))
    print("  owner_ledger obs",Dobs,"abst",sum(Dabs.values()),dict(Dabs)," position obs",Pobs,"abst",sum(Pabs.values()),dict(Pabs))
