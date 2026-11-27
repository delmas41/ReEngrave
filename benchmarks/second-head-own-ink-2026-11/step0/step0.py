import sys, numpy as np, pickle
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae6bdd147632e2db9")
S=sys.argv[1]; sys.path.insert(0,S)
from cases import *
from tools.omr.staged import head_ink as HI
from tools.omr.staged.gather import head_interior_white, notehead_ink_under
from PIL import Image
def sp_at(p, y):
    st=pickle.load(open(f"{S}/st{p}.pkl","rb"))
    s=min(st,key=lambda s:0 if s['top']<=y<=s['bot'] else min(abs(y-s['top']),abs(y-s['bot'])))
    return s['sp'], s
for k in sys.argv[2:] or list(CASES):
    c=CASES[k]; b=np.load(f"{S}/bin{c['page']}.npy")
    sp,st=sp_at(c['page'],(c['box'][1]+c['box'][3])/2)
    got=HI.read_head_ink(b,c['box'],sp,[],head_interior_white,notehead_ink_under)
    print(k,c['why'],'sp',sp,'box',[round(v) for v in c['box']],'trim',got.get('trimmed'),'ext',got.get('extent_sp'),'rim',got.get('rim_trimmed'),'noh',got.get('not_one_head'),'clip',got.get('stack_clipped'),'val',got.get('value'),'oval',got.get('oval_width_sp'))
    # render
    t=got['trimmed']; x0,y0=int(c['box'][0]-2*sp),int(c['box'][1]-2.5*sp); x1,y1=int(c['box'][2]+2*sp),int(c['box'][3]+2.5*sp)
    crop=(b[y0:y1,x0:x1]==0)
    im=np.full(crop.shape+(3,),255,np.uint8); im[crop]=(0,0,0)
    def rect(bb,col):
        a0,b0,a1,b1=[int(round(v)) for v in bb]; a0-=x0;a1-=x0;b0-=y0;b1-=y0
        for xx in range(max(0,a0),min(im.shape[1],a1)):
            for yy in (b0,b1-1):
                if 0<=yy<im.shape[0]: im[yy,xx]=col
        for yy in range(max(0,b0),min(im.shape[0],b1)):
            for xx in (a0,a1-1):
                if 0<=xx<im.shape[1]: im[yy,xx]=col
    rect(c['box'],(255,140,0)); rect(c['written'],(0,170,0))
    if t: rect(t,(0,0,255))
    Image.fromarray(im).resize((im.shape[1]*8,im.shape[0]*8),Image.NEAREST).save(f"{S}/s0_{k}.png")
