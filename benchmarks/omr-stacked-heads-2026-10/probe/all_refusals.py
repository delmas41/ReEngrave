import json, collections, sys
import fitz, numpy as np
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129"
D=json.load(open(SP+"/out/refusals_all.json")); R=D["refusals"]
doc=fitz.open(D["pdf"]); cache={}
def ink(p):
    if p not in cache:
        pix=doc[p].get_pixmap(dpi=D["dpi"],colorspace=fitz.csGRAY); cache[p]=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)<140
    return cache[p]
out=[]
for r in R:
    b=r["box_page"]; kb=r["keeper_box_page"]
    if not b or not kb or not r["height_spaces"]: out.append(("nobox",r)); continue
    sp=(b[3]-b[1])/r["height_spaces"]
    cy=(b[1]+b[3])/2; kcy=(kb[1]+kb[3])/2
    dy=abs(cy-kcy)/sp
    x0=min(b[0],kb[0]); x1=max(b[2],kb[2]); w=x1-x0
    I=ink(r["page"]); bx0,bx1=int(x0+0.3*w),int(x0+0.7*w)
    ya=int(min(b[1],kb[1])-sp); yb=int(max(b[3],kb[3])+sp)
    band=I[ya:yb,bx0:bx1].mean(axis=1)>=0.3
    runs=[];s=None
    for i,v in enumerate(band):
        if v and s is None:s=i
        if (not v) and s is not None: runs.append((s,i)); s=None
    if s is not None: runs.append((s,len(band)))
    mid=((cy+kcy)/2-ya); best=0
    for a,c in runs:
        if a-0.2*sp<=mid<=c+0.2*sp or any(a-0.2*sp<=y<=c+0.2*sp for y in (cy-ya,kcy-ya)): best=max(best,c-a)
    out.append(("ok",dict(page=r["page"],dy=round(dy,2),blob=round(best/sp,2),k=(r["signal"] or {}).get("k"),key=r["key"],inkr=r["this_ink"],inko=r["other_ink"])))
ok=[o[1] for o in out if o[0]=="ok"]
print(len(R),"refusals;",len(ok),"measurable")
def cat(o):
    if o["dy"]<0.5: return "A same-spot (dy<0.5sp): true duplicate geometry"
    if o["dy"]>=0.85 and o["blob"]>=1.8: return "B stacked-third: dy>=0.85sp and ink blob>=1.8sp (two heads tall)"
    if o["dy"]>=0.85: return "C dy>=0.85sp, blob<1.8sp: ink does not show two heads"
    return "D 0.5<=dy<0.85sp: ambiguous offset"
c=collections.Counter(cat(o) for o in ok)
for k,v in sorted(c.items()): print(v,k)
print("k in signals",collections.Counter(o["k"] for o in ok))
print("by page B:",sorted(collections.Counter(o["page"] for o in ok if cat(o).startswith("B")).items()))
json.dump(ok,open(SP+"/out/refusals_cat.json","w"))
for o in ok:
    if cat(o)[0] in "CD": print(o)
