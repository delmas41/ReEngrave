import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J, farhead_all_wired_eval as W
import numpy as np
doc,page,s=sys.argv[1],int(sys.argv[2]),sys.argv[3]
L,fp,far=J.prepare(doc,page)
h=[x for x in far if x["subject"]==s][0]
g=L["gray_B"]; x0,_,x1,_=h["box"]; w=x1-x0
for a,b in ((int(x0-2*w),int(x0-w)),(int(x1+w),int(x1+2*w))):
    p=g[:,a:b].astype(float).mean(axis=1)
    print(a,b,[(y,int(p[y])) for y in range(int(sys.argv[4]),int(sys.argv[5])) if p[y]<150])
