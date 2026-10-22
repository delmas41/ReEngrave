import sys, json, collections
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
exec(open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129/groups.py").read().split("rows=[]")[0])
import fitz, numpy as np
pdf=json.load(open(SP+"/out/brahms_p0.json"))["pdf"]
doc=fitz.open(pdf); pg=doc[0]  # pdf page 0 (hand-truth pdf_page_index?)
print("truth pdf page idx", page.pdf_page_index)
pg=doc[page.pdf_page_index]
pix=pg.get_pixmap(dpi=600, colorspace=fitz.csGRAY)
im=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)
ink=im<140
print(ink.shape)
def spacef(gk):
    p=gk.split("/"); sys_,st=int(p[2]),int(p[3])
    for c in page.cells:
        if c.system==sys_ and c.staff==st:
            ys=c.staff_line_ys; sc=(c.rect[2]-c.rect[0])/c.canonical_w
            return (sum(ys[i+1]-ys[i] for i in range(len(ys)-1))/(len(ys)-1))*sc
out=[]
for gk,mem in groups.items():
    boxes=[G[m[0]]["box_page"] for m in mem]
    sp=spacef(gk[0]); side=gk[2]
    x0=min(b[0] for b in boxes); x1=max(b[2] for b in boxes); y0=min(b[1] for b in boxes); y1=max(b[3] for b in boxes)
    w=x1-x0
    bx0,bx1=(x0+0.3*w,x0+0.7*w)
    ya=int(y0-1.0*sp); yb=int(y1+1.0*sp)
    band=ink[ya:yb,int(bx0):int(bx1)].mean(axis=1)>=0.3
    # runs
    runs=[];s=None
    for i,v in enumerate(band):
        if v and s is None: s=i
        if (not v) and s is not None: runs.append((s,i)); s=None
    if s is not None: runs.append((s,len(band)))
    cy=[(b[1]+b[3])/2-ya for b in boxes]
    # longest run containing/overlapping any box centre
    best=0
    for a,b in runs:
        if any(a-0.2*sp<=c<=b+0.2*sp for c in cy): best=max(best,b-a)
    scores={int(p):s for p,s in mem[0][2]["scores"].items()}
    ts=[t_of.get(m[0],set()) for m in mem]; alltruth=set().union(*ts)
    label="unmatched" if not alltruth else ("two_real" if len(alltruth)>=2 else "one_head")
    dy=(max(cy)-min(cy))/sp
    out.append((label,mem[0][1][0],round(best/sp,2),round(dy,2),len(mem),gk[0]+" "+gk[1]))
for r in sorted(out,key=lambda r:(r[0],r[1],r[2])): print(r)
