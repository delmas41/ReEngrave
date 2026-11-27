import sys, numpy as np, cv2
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae6bdd147632e2db9")
S=sys.argv[1]; sys.path.insert(0,S)
from cases import *
from step0util import sp_at
from tools.omr.staged import head_ink as HI, head_oval as HO
def holes_in(ink, wx0,wy0,wx1,wy1, amin):
    w=(~ink[wy0:wy1,wx0:wx1]).astype(np.uint8)
    n,lab,st,ce=cv2.connectedComponentsWithStats(w,connectivity=4)
    out=[]
    for i in range(1,n):
        x,y,ww,hh,a=st[i]
        if x==0 or y==0 or x+ww==w.shape[1] or y+hh==w.shape[0] or a<amin: continue
        out.append((ce[i][0]+wx0, ce[i][1]+wy0, int(a), int(y+wy0), int(y+hh+wy0)))
    return out
for k in sys.argv[2:]:
    c=CASES[k]; b=np.load(f"{S}/bin{c['page']}.npy"); sp,_=sp_at(S,c['page'],(c['box'][1]+c['box'][3])/2)
    t=HI.trim_head(b,c['box'],sp,[])
    if not t.get('trimmed'): print(k,'no trimmed'); continue
    cl=t['clean']; ox,oy=t['origin']; T=[v-o for v,o in zip(t['trimmed'],(ox,oy,ox,oy))]
    raw=(b[oy:oy+cl.shape[0], ox:ox+cl.shape[1]]==0)
    m=int(round(0.6*sp)); W=(max(0,T[0]-2),max(0,T[1]-m),min(cl.shape[1],T[2]+2),min(cl.shape[0],T[3]+m))
    hs=holes_in(cl,*W,amin=0.08*sp*sp)+holes_in(raw,*W,amin=0.08*sp*sp)
    # merge: same hole if centres within 0.3 sp
    H=[]
    for h in sorted(hs,key=lambda h:-h[2]):
        if all(abs(h[1]-g[1])>0.3*sp or abs(h[0]-g[0])>0.5*sp for g in H): H.append(h)
    cy=(c['box'][1]+c['box'][3])/2-oy; wy=(c['written'][1]+c['written'][3])/2-oy
    lr=HO._line_rows(np.asarray(b[oy:oy+cl.shape[0], max(0,ox-int(3*sp)):ox+cl.shape[1]+int(3*sp)])==0)
    kw=max(3,int(round(HI.LEDGER_MIN_SPACES*sp)))
    hl=cv2.morphologyEx(raw.astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,kw),np.uint8)).any(axis=1)
    lr=lr|hl
    hc=[h for h in H if T[1]-2<=h[1]<=T[3]+2]
    own=min(hc,key=lambda h:abs(h[1]-cy)) if hc else None
    other=[h for h in hc if h is not own]
    r0,r1=T[1],T[3]
    if own and other:
        nb=min(other,key=lambda h:abs(h[1]-own[1]))
        mid=(own[1]+nb[1])/2
        if nb[1]<own[1]: r0=max(r0,int(np.ceil(mid)))
        else: r1=min(r1,int(np.floor(mid))+1)
    # rows of candidate's side holding ink in T cols
    rows=[r for r in range(r0,r1) if cl[r,T[0]:T[2]].any()]
    nonline=[r for r in rows if not lr[r]]
    def width(rr):
        xs=[x for r in rr for x in np.nonzero(cl[r,T[0]:T[2]])[0]]
        return (max(xs)-min(xs)+1)/sp if xs else None
    print(f"{k:4s} {c['why'][9:]:24s} trim {t['extent_sp']} | holes {[(round(h[1]+oy),h[2]) for h in hc]} own {round(own[1]+oy) if own else None} | own-side rows {r0+oy}-{r1+oy} h={(r1-r0)/sp:.3f} | w all rows {width(rows):.3f} w non-line rows {width(nonline) if nonline else float('nan'):.3f} | n line rows in T {sum(lr[T[1]:T[3]])}")
    if own:
        hr=[r for r in range(own[3],own[4])]
        print('      own hole rows',own[3]+oy,own[4]+oy,'w on hole rows',round(width(hr),3), 'per-row widths', [int(width([r])*sp+.5) for r in hr])
        # stem: extreme cols with ink run extending >= 1 sp outside own-side rows
        for side,col in (('L',None),('R',None)):
            xs=[x for r in rows for x in np.nonzero(cl[r,T[0]:T[2]])[0]]
            cx=T[0]+(min(xs) if side=='L' else max(xs))
            colink=np.nonzero(raw[:,cx])[0]
            above=sum(1 for y in colink if y<r0); below=sum(1 for y in colink if y>=r1)
            print('      ',side,'edge col',cx+ox,'raw ink rows above own side',above,'below',below)
