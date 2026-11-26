"""The six shared heads: the up stroke at each head's right, its left/right edge per row (reduced px, relative), and the head rows."""
import os, pickle, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "/private/tmp/claude-501/lane-2.306-r25")
import numpy as np
import mapreplay as MR
SIX = [("litolff", 4, (2490, 2160, 2513, 2176)), ("litolff", 8, (2484, 2078, 2504, 2094)), ("litolff", 8, (1849, 2578, 1870, 2594)),
       ("litolff", 9, (685, 1009, 704, 1024)), ("brahms", 0, (2549, 6013, 2590, 6050)), ("brahms", 5, (3456, 5128, 3492, 5156))]
src = sys.argv[1] if len(sys.argv) > 1 else "approx"
cache = {}
for plate, p, hb in SIX:
    if (plate, p) not in cache:
        fn = f"/private/tmp/claude-501/lane-2.306-r25/approx/{plate}_map_p{p}.pkl" if src == "approx" else f"/private/tmp/claude-501/lane-2.306-r25/dump/{plate}/map_p{p}.pkl"
        D = pickle.load(open(fn, "rb"))
        cache[(plate, p)] = MR.run(D)[0]
    res = cache[(plate, p)]
    s = res.scale
    best = None
    for i, st in MR.near(res, hb, pad=2):
        x, y, w, h = st.box
        if st.kind == "vertical" and x >= (hb[0] + hb[2]) / 2 and y < hb[1] and y + h > hb[3]:
            best = (i, st)
    if best is None:
        print(plate, p, hb, "no up stroke through"); continue
    i, st = best
    m, mx, my = res.masks[i]
    hy0, hy1 = int(hb[1] * s) - my, int(hb[3] * s) - my
    L, R = [], []
    for r in range(m.shape[0]):
        xs = np.nonzero(m[r])[0]
        L.append(int(xs[0]) if xs.size else -1); R.append(int(xs[-1]) if xs.size else -1)
    print(plate, p, hb, "stroke", i, st.box, "head rows", hy0, hy1, "of", m.shape[0])
    print("   L", "".join(str(min(9, v)) for v in L))
    print("   R", "".join(str(min(9, v)) for v in R))
    print("   H", "".join("h" if hy0 <= r <= hy1 else "." for r in range(m.shape[0])))
    print("   touches", [(j, c, res.strokes[j].kind, res.strokes[j].box) for j, c in st.touches])
