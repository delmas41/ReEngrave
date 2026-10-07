"""Crops of every box newly refused as a dot (OMR_DOT_FOLLOWS_NOTE): python3 dot_not_a_note_newly_refused.py <replay dir>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2, numpy as np
import truth_set_2_44c as ts
from frame import render_page_matching_gather
DOC = {"brahms": "brahms1-breitkopf", "lito": "beethoven5-litolff"}
d = Path(sys.argv[1])
tiles, g = [], {}
for short in DOC:
    off = json.loads((d / f"{short}_all_off.json").read_text()); on = json.loads((d / f"{short}_all_on.json").read_text())
    for k, a in off["boxes"].items():
        b = on["boxes"][k]
        if (a["np"] or {}).get("v") is not True and (b["np"] or {}).get("v") is True:
            page = int(k.split("/")[1])
            if (short, page) not in g:
                g[(short, page)] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC[short]]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
            bx = a["box"]; cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
            c = cv2.cvtColor(g[(short, page)][int(cy - 50):int(cy + 50), int(cx - 50):int(cx + 50)], cv2.COLOR_GRAY2BGR)
            c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            cv2.rectangle(c, (int((bx[0] - cx + 50) * 3), int((bx[1] - cy + 50) * 3)), (int((bx[2] - cx + 50) * 3), int((bx[3] - cy + 50) * 3)), (0, 140, 255), 1)
            pad = np.full((20, c.shape[1], 3), 255, np.uint8)
            cv2.putText(pad, f"{short} p{page} {k.split('/', 2)[2]} {a['cls'][4:]} {a['w']:.2f}x{a['h']:.2f}", (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            tiles.append(np.vstack([pad, c]))
while len(tiles) % 5:
    tiles.append(np.full_like(tiles[0], 255))
img = np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)])
out = HERE.parents[1] / "out/print/dot_not_a_note_newly_refused.png"
cv2.imwrite(str(out), img)
print("wrote", out, len([t for t in tiles]))
