"""2.206f: crops of the cells whose cv beam stroke is WIDER leftward ON than OFF (Brahms). OFF strokes blue, ON strokes red, on the ORIGINAL cell ink.
usage: beam_widen_crops.py WORKDIR OUT.png CELL [CELL ...]   (CELL = page/system/staff/measure)"""
import sys, json, collections, numpy as np, cv2
sys.path.insert(0, ".")
from tools.omr.staged import gather as G, pipeline
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
work, out, cells_want = sys.argv[1], sys.argv[2], sys.argv[3:]
S = {}
for a in ("off", "on"):
    r = json.load(open(f"{work}/brahms.{a}.gathered.record.json"))["record"]
    d = collections.defaultdict(list)
    for o in r["observations"]:
        if o["quantity"] == "beam_stroke" and o["reader"] == "cv_lines":
            d[o["subject"]].append(o["value"])
    S[a] = d
tiles = []
for pg in sorted({int(c.split("/")[0]) for c in cells_want}):
    pws, cells = pipeline.prepare_pages(PDF, [pg], dpi=600)[0]
    loc = G.gather_geometry(G.Log(), pws)
    for c in cells:
        key = loc.get(c.staff_index)
        if not key: continue
        ck = "%d/%s/%s/%s" % (pg, key[0], key[1], c.measure_index)
        if ck not in cells_want: continue
        sub = "cell/" + ck
        img = cv2.cvtColor(c.binary.copy(), cv2.COLOR_GRAY2BGR)
        for a, col in (("off", (255, 0, 0)), ("on", (0, 0, 255))):
            for (x, y, w, h) in S[a].get(sub, []):
                cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), col, 3 if a == "off" else 2)
        ys = [v[1] for a in S for v in S[a].get(sub, [])] or [0]
        ye = [v[1] + v[3] for a in S for v in S[a].get(sub, [])] or [img.shape[0]]
        xs = [v[0] for a in S for v in S[a].get(sub, [])] or [0]
        xe = [v[0] + v[2] for a in S for v in S[a].get(sub, [])] or [img.shape[1]]
        crop = img[max(0, min(ys) - 150):min(img.shape[0], max(ye) + 60), max(0, min(xs) - 60):min(img.shape[1], max(xe) + 60)]
        cv2.putText(crop, ck, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 140, 0), 2)
        tiles.append(crop)
W = max(t.shape[1] for t in tiles)
sheet = np.vstack([cv2.copyMakeBorder(t, 0, 10, 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles])
cv2.imwrite(out, sheet); print(sheet.shape)
