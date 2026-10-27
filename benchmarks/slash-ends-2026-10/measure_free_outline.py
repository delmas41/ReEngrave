import pickle, sys, math
import numpy as np, cv2
def free_outline(mask, others, sp, eps_sp=0.06):
    m = mask.astype(np.uint8)
    oth = np.zeros_like(m)
    for o in others: oth |= o.astype(np.uint8)
    oth = cv2.dilate(oth, np.ones((3,3),np.uint8), iterations=max(2,int(0.04*sp)))
    cs,_ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, eps_sp*sp, True)[:,0,:].astype(float)
    n=len(ap); per=0; fper=0; straight=0; sharp=0; turn=0
    free=[ (oth[int(round(p[1])),int(round(p[0]))]==0) for p in ap]
    for i in range(n):
        a,b = ap[i], ap[(i+1)%n]; L=math.hypot(*(b-a)); per+=L
        mid=(a+b)/2
        if oth[int(round(mid[1])),int(round(mid[0]))]==0:
            fper+=L
            if L>=0.3*sp: straight+=L
    for i in range(n):
        p,q,r = ap[i-1],ap[i],ap[(i+1)%n]
        if not (free[i-1] or free[i]) : continue
        if not free[i]: continue
        v1,v2=p-q,r-q
        if min(np.hypot(*v1),np.hypot(*v2))<0.2*sp: continue
        ang=math.degrees(math.acos(max(-1,min(1,np.dot(v1,v2)/(np.hypot(*v1)*np.hypot(*v2))))))
        if ang<125: sharp+=1
    return fper/per if per else 0, (straight/fper if fper else 0), sharp
recs=pickle.load(open(sys.argv[1],"rb"))
for r in recs:
    for s in r["strokes"]:
        if s["kind"]=="vertical" or s["share"]<0.5 or s["area"]<0.3: continue
        others=[o["mask"] for o in r["strokes"] if o is not s]
        fr,st,sh=free_outline(s["mask"],others,r["sp"])
        print("%-22s %-14s %-10s len%.2f thk%.2f  free%.2f straight_of_free%.2f sharp_free%d"%(r["id"],str(r["label"])[:14],s["kind"],s["length_sp"],s["thick"],fr,st,sh))
