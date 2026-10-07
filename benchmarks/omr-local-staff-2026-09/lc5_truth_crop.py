import sys, json
sys.path.insert(0, '.')
import cv2, numpy as np
import farhead_per_bar_grid_eval as E
import lc5_crop as C
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-notation-tile-fixes-2837c5/61ecbfe3-efe1-4b05-b3a2-0c894d475fc0/scratchpad/lc/"
d = json.load(open(S + "truth.json"))
fp, L, far, lf, _ = E.build("brahms1-breitkopf", 1, True)
a, b = C.crop(fp.gray, d["old"]), C.crop(fp.gray, d["new"])
h = max(a.shape[0], b.shape[0])
pad = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
cv2.imwrite(S + "truth_crop.png", np.hstack([pad(a), pad(b)]))
print(a.shape, b.shape)
