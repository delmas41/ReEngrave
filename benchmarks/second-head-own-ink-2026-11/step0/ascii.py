import sys, numpy as np, pickle
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae6bdd147632e2db9")
S=sys.argv[1]; sys.path.insert(0,S)
from cases import *
from tools.omr.staged import head_ink as HI, head_oval as HO
from step0util import sp_at
for k in sys.argv[2:]:
    c=CASES[k]; b=np.load(f"{S}/bin{c['page']}.npy"); sp,_=sp_at(S,c['page'],(c['box'][1]+c['box'][3])/2)
    t=HI.trim_head(b,c['box'],sp,[])
    tx0,ty0,tx1,ty1=t['trimmed']; bx=[int(round(v)) for v in c['box']]; wr=[int(round(v)) for v in c['written']]
    x0,x1=min(tx0,bx[0],wr[0])-4,max(tx1,bx[2],wr[2])+4; y0,y1=min(ty0,bx[1],wr[1])-4,max(ty1,bx[3],wr[3])+4
    lx0,lx1=int(x0-3*sp),int(x1+3*sp)
    core=HO._line_rows(b[y0:y1,lx0:lx1]==0, dilate=False)
    print(k,c['why'],'trim',t['trimmed'],'ext',t['extent_sp'],'cand',bx,'written',wr)
    for r in range(y0,y1):
        s=''.join(('#' if b[r,x]==0 else '.') if not (x in (tx0-1,tx1)) else '|' for x in range(x0,x1))
        tag=('L' if core[r-y0] else ' ')+('T' if ty0<=r<ty1 else ' ')+('C' if bx[1]<=r<bx[3] else ' ')+('W' if wr[1]<=r<wr[3] else ' ')
        print('%5d %s %s'%(r,tag,s))
