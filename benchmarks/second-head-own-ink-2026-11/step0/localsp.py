import sys, numpy as np, cv2
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae6bdd147632e2db9")
S=sys.argv[1]; sys.path.insert(0,S)
from cases import *
from step0util import sp_at
from tools.omr.staged import head_oval as HO
for k in sys.argv[2:]:
    c=CASES[k]; b=np.load(f"{S}/bin{c['page']}.npy"); sp,st=sp_at(S,c['page'],(c['box'][1]+c['box'][3])/2)
    x0,x1=int(c['box'][0]-3*sp),int(c['box'][2]+3*sp); y0,y1=int(c['box'][1]-5*sp),int(c['box'][3]+5*sp)
    ink=b[y0:y1,x0:x1]==0
    # rows where ink covers >=60% of the window width (staff lines) ; ledger: horizontal opening 1.7sp
    full=ink.mean(axis=1)>=0.6
    kw=int(round(1.7*sp)); hl=cv2.morphologyEx(ink.astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,kw),np.uint8)).any(axis=1)
    def cents(m):
        out=[];r=0
        while r<len(m):
            if m[r]:
                q=r
                while r<len(m) and m[r]: r+=1
                out.append(((q+r-1)/2+y0, r-q))
            else: r+=1
        return out
    print(k,'staff sp',sp,'staff',st['top'],st['bot'],'| full-width rows',[(round(a,1),n) for a,n in cents(full)],'| ledger-or-line rows',[(round(a,1),n) for a,n in cents(hl)])
