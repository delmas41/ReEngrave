import sys, json, collections
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
sys.path.insert(0, "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129")
from tools.omr.hand_truth import store as ST
from match119 import same, kind_of
page=ST.load("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81/data/hand-truth/pages/imslp317803/0.json")
cells={c.id:c for c in page.cells}
heads=[b for b in page.boxes if b.cls.startswith("notehead") and kind_of(b.cls)!="other" and "all-ink" in cells[b.cell_id].inspected]
def load(p): return json.load(open(p))["glyphs"]
def stats(G):
    boxed=[(k,g) for k,g in G.items() if g["box_page"] and g["key" if False else "cls"] and k.startswith("glyph/0/")]
    surv={}; dupref=0
    for h in heads:
        c=[k for k,g in boxed if same(list(h.rect),g["box_page"])]
        alive=[k for k in c if G[k]["adj"]!="refused"]
        surv[h.id]=(len(c),len(alive),c)
    ref=[k for k,g in G.items() if any(r["reason"]=="stacked_head_duplicate" for r in g["rows"])]
    return surv,ref
def main(off,on):
    A,refA=stats(load(off)); B,refB=stats(load(on))
    n=len(heads)
    cov=lambda S:sum(1 for v in S.values() if v[1]>=1)
    dup=lambda S:sum(1 for v in S.values() if v[1]>=2)
    print("truth heads",n)
    print("heads with a surviving box  OFF",cov(A),"ON",cov(B))
    print("heads with >=2 surviving boxes (duplicates kept) OFF",dup(A),"ON",dup(B))
    print("stacked_head_duplicate refusals OFF",len(refA),"ON",len(refB))
    gained=[h for h in A if A[h][1]==0 and B[h][1]>=1]; lost=[h for h in A if A[h][1]>=1 and B[h][1]==0]
    dupnew=[h for h in A if A[h][1]<2 and B[h][1]>=2]
    print("truth heads gained",len(gained),gained); print("truth heads lost",len(lost),lost); print("new duplicate-kept heads",len(dupnew),dupnew)
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
