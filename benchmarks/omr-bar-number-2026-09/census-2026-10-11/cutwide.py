import json,sys,pickle
from tools.omr.preprocessing import render_page
S=sys.argv[1]
L="/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF={"brahms1-breitkopf":L+"brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     "beethoven5-litolff":L+"beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
for n,pdf in PDF.items():
    d=json.load(open(f"{S}/{n}.json"))
    boxes={o["subject"]:o["detail"]["bbox_page_px"] for o in d["observations"]+d["abstentions"]}
    # space from the vertical band (5.4 spaces tall), robust to x clipping
    out={w:{} for w in (7,8)}; geo={}
    for p in sorted({int(s.split("/")[1]) for s in boxes}):
        img=render_page(pdf,p,600).rgb
        for s,(x0,y0,x1,y1) in boxes.items():
            if int(s.split("/")[1])!=p: continue
            sp=(y1-y0)/5.4; geo[s]=(x0,y0,x1,y1,sp)
            for w in (7,8):
                out[w][s]=img[int(y0):int(y1),int(x0):min(img.shape[1],int(x0+w*sp))].copy()
    for w in (7,8): pickle.dump(out[w],open(f"{S}/{n}_w{w}_crops.pkl","wb"))
    json.dump(geo,open(f"{S}/{n}_geo.json","w"))
    print(n,flush=True)
