import json,sys,collections
def sub(b):
    hs=b["heads"]
    cand=[h for h in hs if h["reach"] and h["dx"]<=1.75 and h["hpos"] is not None]
    def fit(h): return h["dy"]<=1.4 or (h["dy_c"] is not None and h["dy_c"]<=1.4)
    ref=[h for h in cand if h["status"]!="live" and fit(h)]
    live_ok=[h for h in cand if h["status"]=="live" and h["dy"]<=1.4]
    live_c=[h for h in cand if h["status"]=="live" and h["dy"]>1.4 and h["dy_c"] is not None and h["dy_c"]<=1.4]
    off=b["apos"]<-3 or b["apos"]>11
    if live_ok: return "OWNER WOULD FIT (not reproduced)"
    if live_c: return "class anchor: fits at box centre"
    if ref: return "fitting head refused: "+ref[0]["status"].split(":",1)[1]
    if cand:
        dy=min(min(h["dy"],h["dy_c"] if h["dy_c"] is not None else 99) for h in cand)
        return "heads in window, none at its height (min dy %s)"%("1.4-3" if dy<=3 else ">3")+(" [box off the staff]" if off else "")
    if not hs: return "no head box in cell"
    live=[h for h in hs if h["status"]=="live"]
    if not any(h["reach"] for h in hs): return "heads only to its left"
    return "heads >1.75 sp right"
if __name__=="__main__":
    B=json.load(open(sys.argv[1]))["boxes"]; L=json.load(open(sys.argv[2]))
    grp={"notacc":{"stem","rest","frag","bar","dyn","clef"},"real":{"nat","flat","flat?","sharp"},"cropreal":{"flatcrop","natcrop","sharpcrop"},"merged":{"merged","unclear"}}
    inv={x:g for g,s in grp.items() for x in s}
    t=collections.defaultdict(collections.Counter)
    for b in B:
        g=inv[L[b["key"]]]
        if g!="notacc": t[g][sub(b)]+=1
    for g,c in t.items(): print(g,sum(c.values())); [print("   ",v,k) for k,v in c.most_common()]
