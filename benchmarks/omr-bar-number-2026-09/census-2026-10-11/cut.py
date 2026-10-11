import json, sys, numpy as np, cv2, pickle
from tools.omr.preprocessing import render_page
S=sys.argv[1]
L="/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF={"brahms1-breitkopf":L+"brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     "beethoven5-litolff":L+"beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
for n,pdf in PDF.items():
    d=json.load(open(f"{S}/{n}.json"))
    boxes={}
    for o in d["observations"]+d["abstentions"]:
        boxes[o["subject"]]=o["detail"].get("bbox_page_px")
    pages=sorted({int(s.split("/")[1]) for s in boxes})
    crops={}
    for p in pages:
        img=render_page(pdf,p,600).rgb
        for s,b in boxes.items():
            if int(s.split("/")[1])!=p or not b: continue
            x0,y0,x1,y1=map(int,b)
            crops[s]=img[y0:y1,x0:x1].copy()
            # context: 3x wider left/right, mark box in red
            cx0=max(0,x0-2*(x1-x0)); cx1=min(img.shape[1],x1+2*(x1-x0)); cy0=max(0,y0-(y1-y0)); cy1=min(img.shape[0],y1+(y1-y0))
            ctx=cv2.cvtColor(img[cy0:cy1,cx0:cx1].copy(),cv2.COLOR_RGB2BGR)
            cv2.rectangle(ctx,(x0-cx0,y0-cy0),(x1-cx0,y1-cy0),(0,0,255),3)
            tag=s.replace("/","_")
            cv2.imwrite(f"{S}/{n}_{tag}_ctx.png",ctx)
            cv2.imwrite(f"{S}/{n}_{tag}_crop.png",cv2.cvtColor(crops[s],cv2.COLOR_RGB2BGR))
        print(n,p,flush=True)
    pickle.dump(crops,open(f"{S}/{n}_crops.pkl","wb"))
