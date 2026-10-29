import pickle, sys, math
import numpy as np, cv2
def poly_measures(mask, sp, eps_sp=0.06, seg_sp=0.3):
    m = mask.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    per = cv2.arcLength(c, True)
    ap = cv2.approxPolyDP(c, eps_sp*sp, True)[:,0,:].astype(float)
    n = len(ap); segs=[]
    for i in range(n):
        a, b = ap[i], ap[(i+1)%n]; segs.append(math.hypot(*(b-a)))
    long_ = sum(s for s in segs if s >= seg_sp*sp)
    # sharp corners: interior angle < 125 deg between consecutive long-ish segments
    sharp = 0
    for i in range(n):
        p, q, r = ap[i-1], ap[i], ap[(i+1)%n]
        v1, v2 = p-q, r-q
        if min(np.hypot(*v1), np.hypot(*v2)) < 0.2*sp: continue
        ang = math.degrees(math.acos(max(-1,min(1,np.dot(v1,v2)/(np.hypot(*v1)*np.hypot(*v2))))))
        if ang < 125: sharp += 1
    return long_/per, sharp, n
if __name__=="__main__":
    recs = pickle.load(open(sys.argv[1],"rb"))
    for r in recs:
        for s in r["strokes"]:
            if s["kind"]=="vertical" or s["share"]<0.5 or s["area"]<0.3: continue
            ls, sh, n = poly_measures(s["mask"], r["sp"])
            print("%-22s %-14s %-10s len%.2f thk%.2f  straight%.2f sharp%d nvert%d" % (r["id"], str(r["label"])[:14], s["kind"], s["length_sp"], s["thick"], ls, sh, n))
