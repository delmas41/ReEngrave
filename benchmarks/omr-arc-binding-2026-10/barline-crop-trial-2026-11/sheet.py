import glob, sys, cv2, numpy as np
fs = sorted(glob.glob("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aca2654680d85413f/out/print/arc-barline-crop-trial/newboxes/%s*.png" % sys.argv[1]))
tiles = []
for i, f in enumerate(fs):
    im = cv2.imread(f)
    s = 560.0 / im.shape[1]
    im = cv2.resize(im, (560, max(40, min(300, int(im.shape[0] * s)))))
    pad = np.full((300, 560, 3), 255, np.uint8)
    pad[:im.shape[0]] = im
    cv2.putText(pad, str(i), (2, 292), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
    tiles.append(pad)
    print(i, f.split("/")[-1])
rows = [np.hstack(tiles[i:i + 2] + [np.full((300, 560, 3), 255, np.uint8)] * (2 - len(tiles[i:i + 2]))) for i in range(0, len(tiles), 2)]
cv2.imwrite(sys.argv[2], np.vstack(rows))
