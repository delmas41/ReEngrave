import json,pickle,sys,cv2
from tools.omr import staff_labels_surya as SL
from tools.omr import bar_number_text as B
S=sys.argv[1]
def prep(rgb,pad,up):
    g=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    g=cv2.copyMakeBorder(g,pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=(255,255,255))
    return cv2.resize(g,None,fx=up,fy=up,interpolation=cv2.INTER_CUBIC) if up>1 else g
for wtag in ["","_w7","_w8"]:
    tess={}
    for up in (2,3):
        out={}
        for rep in (("a","b") if (wtag=="" and up==2) else ("a",)):
            for n in ["brahms1-breitkopf","beethoven5-litolff"]:
                c=pickle.load(open(f"{S}/{n}{wtag}_crops.pkl","rb")); subs=list(c)
                out[n]=dict(zip(subs,SL.read_crops_text([prep(c[s],60,up) for s in subs],max_tokens=16)))
                if up==2 and rep=="a":
                    tess[n]={s:(B.read_crop(c[s]) or (None,))[0] for s in subs}
            json.dump(out,open(f"{S}/surya_w{wtag or '_w6'}u{up}{rep}.json","w"))
    json.dump(tess,open(f"{S}/surya_tess{wtag or '_w6'}.json","w"))
    print("done",wtag,flush=True)
