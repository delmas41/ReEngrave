import json,collections,sys
d=json.load(open(sys.argv[1]));B=d["boxes"]
OTHER={"notehead","rest","dynamic","clef","flag","ornament","stem","time_sig_digit"}
def head_reason(b):
    hs=b["heads"]; live=[h for h in hs if h["status"]=="live"]; ref=[h for h in hs if h["status"]!="live"]
    if not hs: return "no head box in cell"
    if not live:
        return "every head refused"
    reach=[h for h in live if h["reach"]]
    if not reach: return "heads only to its left"
    near=[h for h in reach if h["dx"]<=1.75]
    if not near: return "heads right but >1.75sp"
    wp=[h for h in near if h["hpos"] is not None]
    if not wp: return "head has no position"
    dy=min(h["dy"] for h in wp); dyc=min((h["dy_c"] for h in wp if h["dy_c"] is not None),default=None)
    if dyc is not None and dyc<=1.4: return "height: class anchor (centre fits)"
    return "height off %s"%("1.4-2" if dy<=2 else "2-3" if dy<=3 else ">3")
def size(b):
    h,w=b["h_sp"],b["w_sp"]
    if h<1.6: return "short(<1.6)"
    if h>4.6 or w>2.2: return "huge"
    return "normal"
def ov(b):
    c=[o for o in b["overlaps"] if o["frac_of_acc"]>=0.5 and o["cat"] in OTHER]
    return c[0]["cls"] if c else ""
if __name__=="__main__":
    t=collections.Counter((size(b),head_reason(b)) for b in B)
    for k,v in sorted(t.items()): print(v,k)
    print(collections.Counter(ov(b) for b in B))
    print(collections.Counter((b["cls"],size(b)) for b in B))
