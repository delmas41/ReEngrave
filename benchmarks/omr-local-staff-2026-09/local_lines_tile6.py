import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]))
import offbox_measured as OM
from tools.omr.annotate import far_head_reader as FH
doc,page,s="beethoven5-litolff",16,"glyph/16/0/0/0/2"
data=json.load(open(sys.argv[1]+"/x/beethoven5-litolff-20261006-night-combined.json"))
g=data["glyphs"][s]; rep=OM.CachedReplay(doc,data)
gray=rep.gray_of(page)
for key in ("staff/16/0/0","staff/16/0/1"):
    gl=data["staff_lines"][key]; sp=(gl[-1]-gl[0])/4; print(key,[round(v,1) for v in gl],"sp",round(sp,2))
    x0,y0,x1,y1=g["box"]; w=x1-x0; print("box",[round(v,1) for v in g["box"]])
    for name,(a,b) in (("L",(int(x0-2*w),int(x0-w))),("R",(int(x1+w),int(x1+2*w)))):
        print(name,(a,b),[FH._darkest_row(gray,a,b,int(y-sp*.5),int(y+sp*.5)+1) for y in sorted(gl)])
    print("frame",[round(v,1) for v in FH.frame_lines_for_head(gray,gl,g["box"])])
