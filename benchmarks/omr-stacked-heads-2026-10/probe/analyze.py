# NOTE: paths in this probe are scratch-local (the 2.129 session scratchpad); match119.py is 2.119 benchmarks/omr-twins-2026-10/match.py copied unchanged.
import sys, json, collections, statistics
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
sys.path.insert(0, "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129")
from tools.omr.hand_truth import store as ST
from match119 import iou, same, kind_of
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129"
D = json.load(open(SP+"/out/brahms_p0.json"))
G = D["glyphs"]
page = ST.load("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81/data/hand-truth/pages/imslp317803/0.json")
cells = {c.id: c for c in page.cells}
def space(c):
    ys=c.staff_line_ys; sc=(c.rect[2]-c.rect[0])/c.canonical_w
    return (sum(ys[i+1]-ys[i] for i in range(len(ys)-1))/(len(ys)-1))*sc
heads=[]; stems=[]
for b in page.boxes:
    c=cells[b.cell_id]
    if "all-ink" not in c.inspected: continue
    if b.cls.startswith("notehead") and kind_of(b.cls)!="other":
        heads.append({"id":b.id,"cls":b.cls,"rect":list(b.rect),"cell":b.cell_id,"sp":space(c)})
    if b.cls=="stem": stems.append({"id":b.id,"rect":list(b.rect),"cell":b.cell_id})
cx=lambda r:(r[0]+r[2])/2; cy=lambda r:(r[1]+r[3])/2
# attach heads to stems
for h in heads: h["stem"]=None
for s in stems:
    for h in heads:
        if h["cell"]!=s["cell"]: continue
        r=h["rect"]; sr=s["rect"]
        gap_x=max(sr[0]-r[2], r[0]-sr[2], 0); gap_y=max(sr[1]-r[3], r[1]-sr[3],0)
        if gap_x<=0.2*h["sp"] and gap_y<=0.0*h["sp"]+1e-9:
            h.setdefault("stems",[]).append(s["id"])
by_stem=collections.defaultdict(list)
for h in heads:
    for sid in h.get("stems",[]): by_stem[sid].append(h)
sm={s["id"]:s for s in stems}
boxed=[(k,g) for k,g in G.items() if g["box_page"] is not None]
for h in heads:
    h["cands"]=[k for k,g in boxed if same(h["rect"],g["box_page"])]
def info(k):
    g=G[k]; fit=[r for r in g["rows"] if r["q"]=="stacked_head_fit" and r["kind"]=="observation"]
    absf=[r for r in g["rows"] if r["q"]=="stacked_head_fit" and r["kind"]=="abstention"]
    ref=[r for r in g["rows"] if r["reason"]=="stacked_head_duplicate"]
    return {"fit":fit[-1]["value"] if fit else None,"fitabs":absf[-1]["reason"] if absf else None,"refused_dup":bool(ref),"adj":g["adj"],"why":g["adj_why"]}
out=[]
chords=[]
for sid,hs in by_stem.items():
    if len(hs)<2: continue
    hs=sorted(hs,key=lambda h:cy(h["rect"]))
    sp=hs[0]["sp"]
    for a,b in zip(hs,hs[1:]):
        d=abs(cy(a["rect"])-cy(b["rect"]))/sp
        if d<=1.5:
            sx=cx(sm[sid]["rect"])
            chords.append({"stem":sid,"cell":a["cell"],"a":a["id"],"b":b["id"],"dist_sp":round(d,2),
              "side_a":"R" if cx(a["rect"])>sx else "L","side_b":"R" if cx(b["rect"])>sx else "L",
              "cands_a":[(k,info(k)) for k in a["cands"]],"cands_b":[(k,info(k)) for k in b["cands"]]})
json.dump(chords,open(SP+"/out/chords.json","w"),indent=1,default=str)
print("truth heads",len(heads),"with stem",sum(1 for h in heads if h.get("stems")),"chords<=1.5sp pairs",len(chords))
for c in chords:
    print(c["cell"],c["stem"],c["a"],c["b"],c["dist_sp"],c["side_a"],c["side_b"])
    for nm in("cands_a","cands_b"):
        for k,i in c[nm]: print("   ",nm,k,i["fit"],i["fitabs"],"DUPREF" if i["refused_dup"] else "",i["adj"],i["why"][:2] if i["why"] else "")
    if not c["cands_a"] or not c["cands_b"]: print("    MISSING BOX", not c["cands_a"], not c["cands_b"])
# 211 split
cls=collections.Counter(); rows=[]
box2truth=collections.defaultdict(list)
for h in heads:
    for k in h["cands"]: box2truth[k].append(h["id"])
for k,g in G.items():
    ref=[r for r in g["rows"] if r["reason"]=="stacked_head_duplicate"]
    if not ref: continue
    det=json.loads(ref[-1]["detail"]) if ref[-1]["detail"] and not ref[-1]["detail"].endswith("~") else {}
    dup=det.get("duplicate_of")
    kd = None
    if dup:
        kd = dup if dup in G else None
    t_me=set(box2truth.get(k,[])); t_k=set(box2truth.get(dup,[])) if dup else set()
    if not t_me: c="refused box matches no truth head"
    elif t_me & t_k: c="TRUE DUPLICATE (keeper on same truth head)"
    else:
        c="REAL SECOND HEAD LOST (keeper on %s)" % ("another truth head" if t_k else "no truth head")
        # was this truth head rescued by another box?
        alt=[kk for h in heads if h["id"] in t_me for kk in h["cands"] if kk!=k and not info(kk)["refused_dup"]]
        if alt: c="refused, truth head still has another surviving box"
    cls[c]+=1; rows.append((k,c,sorted(t_me),dup,sorted(t_k)))
print(sum(cls.values()),"refusals"); 
for c,n in cls.most_common(): print(n,c)
json.dump(rows,open(SP+"/out/refusals.json","w"),indent=1)
