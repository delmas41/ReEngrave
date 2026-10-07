"""lc5_one.py <scan.json> <litolff|brahms> <subject> <out.png>: before|after crop of one head from a scan json."""
import json, sys
sys.path.insert(0, '.')
import cv2, numpy as np
import lc5_sheet as S
import lc5_crop as C
import truth_set_2_44c as ts
from frame import render_page_matching_gather
js, doc, subj, out = sys.argv[1:5]
r = json.load(open(js))["heads"][subj]
page = int(subj.split("/")[1])
cfg = ts.DOCS[S.DOC[doc]]
g = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
b, a = S.norm(r["old"]["read"]), S.norm(r["new"]["read"])
cb, ca = C.crop(g, b, sc=4), C.crop(g, a, sc=4)
h = max(cb.shape[0], ca.shape[0])
p = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255))
cv2.imwrite(out, np.hstack([p(cb), p(ca)]))
for n, d in (("before", b), ("after", a)):
    print(n, d["pos"], d["reason"][:80], d["box_source"], "rungs", [round(x["y"], 1) for x in d["rungs"]], "lines", d["lines"])
