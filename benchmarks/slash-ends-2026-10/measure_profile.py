import pickle, sys, math
import numpy as np, cv2
def prof(m):
    ys, xs = np.nonzero(m)
    cx, cy = xs.mean(), ys.mean(); dx, dy = xs-cx, ys-cy
    th = 0.5*math.atan2(2*(dx*dy).mean(), (dx*dx).mean()-(dy*dy).mean())
    t = dx*math.cos(th)+dy*math.sin(th)
    b = np.floor(t - t.min()).astype(int)
    w = np.bincount(b).astype(float)
    return w
recs = pickle.load(open(sys.argv[1],"rb"))
for r in recs:
    for s in r["strokes"]:
        if s["kind"]=="vertical" or s["share"]<0.5: continue
        w = prof(s["mask"]); L=len(w); mx=np.percentile(w,90)
        plat = (w>=0.85*mx).mean()
        e = max(1,int(0.08*L)); end = min(w[:e].mean(), w[-e:].mean())/mx
        hull = cv2.convexHull(np.argwhere(s["mask"])[:, ::-1].astype(np.int32))
        sol = s["mask"].sum()/cv2.contourArea(hull)
        print("%-4s %-22s %-10s sh%.2f len%.2f thk%.2f ang%5.1f  plateau%.2f end%.2f sol%.2f" % (r["id"], str(r["label"])[:22], s["kind"], s["share"], s["length_sp"], s["thick"], s["angle"], plat, end, sol))
