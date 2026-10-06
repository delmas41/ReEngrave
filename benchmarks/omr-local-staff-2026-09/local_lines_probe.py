import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J, farhead_all_wired_eval as W
from tools.omr.annotate import far_head_reader as FH
W.arm(True)
doc,page,s=sys.argv[1],int(sys.argv[2]),sys.argv[3]
L,fp,far=J.prepare(doc,page)
h=[x for x in far if x["subject"]==s][0]
gl=L["staff_lines"]["staff/"+"/".join(s.split("/")[1:4])]
print("box",h["box"],"global",gl)
for kw in (False,True):
    FH.READER_KEYWORDS["local_lines_in_window"]=kw
    ln=FH.frame_lines_for_head(L["gray_B"],gl,h["box"]); print(kw,[round(v,1) for v in ln])
x0,_,x1,_=h["box"]
r=FH.local_staff_lines_in_windows(L["gray_B"],gl,x0,x1,x1-x0); print(r)
