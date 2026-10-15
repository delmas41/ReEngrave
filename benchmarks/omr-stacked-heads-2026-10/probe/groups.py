import sys, json, collections, itertools
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
sys.path.insert(0, "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129")
from tools.omr.hand_truth import store as ST
from match119 import same, kind_of
SP="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129"
G=json.load(open(SP+"/out/brahms_p0.json"))["glyphs"]
page=ST.load("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81/data/hand-truth/pages/imslp317803/0.json")
cells={c.id:c for c in page.cells}
heads=[b for b in page.boxes if b.cls.startswith("notehead") and "all-ink" in cells[b.cell_id].inspected]
boxed=[(k,g) for k,g in G.items() if g["box_page"]]
t_of=collections.defaultdict(set)
for h in heads:
    for k,g in boxed:
        if same(list(h.rect),g["box_page"]): t_of[k].add(h.id)
groups=collections.defaultdict(list)
for k,g in G.items():
    for r in g["rows"]:
        if r["q"]=="stacked_head_fit" and r["kind"]=="observation":
            v=json.loads(r["value"]); d=json.loads(r["detail"]) if r["detail"] and not r["detail"].endswith("~") else None
            if d is None: continue
            pos=[json.loads(x["value"]) for x in g["rows"] if x["q"]=="notehead_staff_position" and x["kind"]=="observation"]
            groups[(k.rsplit("/",2)[0], d["stem"], d["side"])].append((k,v,d,pos[-1] if pos else None))
rows=[]
for gk,mem in groups.items():
    scores={int(p):s for p,s in mem[0][2]["scores"].items()}
    ts=[t_of.get(m[0],set()) for m in mem]
    alltruth=set().union(*ts)
    label = "unmatched" if not alltruth else ("two_real" if len(alltruth)>=2 else "one_head")
    k=mem[0][1][0]
    ks=sorted(scores)
    best1=max(scores.values())
    best=None
    for a,b in itertools.combinations(ks,2):
        if b-a>=2:
            t=scores[a]+scores[b]
            if best is None or t>best[0]+1e-6: best=(t,a,b)
    if best: mean_gap=best[0]/2-best1; fill_gap=min(scores[best[1]],scores[best[2]])-0.4
    else: mean_gap=fill_gap=None
    rows.append((gk,len(mem),k,label,round(mean_gap,3) if mean_gap is not None else None,round(fill_gap,3) if fill_gap is not None else None,[round(m[3],2) if m[3] is not None else None for m in mem],len(alltruth)))
for r in sorted(rows,key=lambda r:(r[3],r[2])): print(r)
print(collections.Counter((r[3],r[2]) for r in rows))
