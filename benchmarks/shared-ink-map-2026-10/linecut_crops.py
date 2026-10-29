"""2.230 line-cut crops for the manager (NOT blind tiles): filed `too_small` heads, half on a line, half in a space, both plates.
Each tile is three panels at 6x: RAW page binary | the CUT ink trim_head kept (bare line pixels out; removed pixels drawn red) |
raw with the detector box (blue) and the filed trimmed box (green) and the no_cut trimmed box (orange).
usage: python3 linecut_crops.py ROWS_JSON OUT_DIR"""
import collections, json, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.getcwd())
from tools.omr.staged import head_ink as HI
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

L = "/Users/seanjohnson/Desktop/ReEngrave/library/editions"
PDF = {"litolff": L + "/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": L + "/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
rows = json.load(open(sys.argv[1]))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)


def where(r):
    if r["rounded"] is None:
        return None
    return "line" if r["rounded"] % 2 == 0 else "space"


pick = []
for plate, n in (("litolff", 3), ("brahms", 2)):
    for w in ("line", "space"):
        c = [r for r in rows if r["plate"] == plate and where(r) == w and 0 <= r["rounded"] <= 8
             and r["filed"] and r["filed"]["noh"] == "too_small"]
        c.sort(key=lambda r: r["sub"])
        step = max(1, len(c) // n)
        pick += c[::step][:n]
by_page = collections.defaultdict(list)
for r in pick:
    by_page[(r["plate"], r["page"])].append(r)
key, tiles, Z = [], [], 6
for (plate, p), rs in sorted(by_page.items()):
    pb = detect_staves(render_page(PDF[plate], p, dpi=600)).page.binary
    for r in rs:
        t = HI.trim_head(pb, r["box"], r["sp"], ())
        x0, y0 = t["origin"]
        ink = t["clean"]
        h, w = ink.shape
        raw = np.asarray(pb[y0:y0 + h, x0:x0 + w]) == 0
        p1 = np.where(raw, 0, 255).astype(np.uint8)
        p1 = cv2.cvtColor(p1, cv2.COLOR_GRAY2BGR)
        p2 = np.full((h, w, 3), 255, np.uint8)
        p2[ink] = 0
        p2[raw & ~ink] = (0, 0, 230)
        p3 = p1.copy()
        def rect(img, b, col):
            cv2.rectangle(img, (int(round(b[0] - x0)), int(round(b[1] - y0))), (int(round(b[2] - x0)) - 1, int(round(b[3] - y0)) - 1), col, 1)
        rect(p3, r["box"], (230, 120, 30))
        if r["filed"].get("trimmed"):
            rect(p3, r["filed"]["trimmed"], (30, 170, 30))
        if r["no_cut"] and r["no_cut"].get("trimmed"):
            rect(p3, r["no_cut"]["trimmed"], (0, 140, 255))
        sep = np.full((h, 2, 3), 160, np.uint8)
        tile = np.hstack([p1, sep, p2, sep, p3])
        tile = cv2.resize(tile, (tile.shape[1] * Z, tile.shape[0] * Z), interpolation=cv2.INTER_NEAREST)
        n = len(key) + 1
        cv2.imwrite("%s/%02d-%s-p%d-%s.png" % (out, n, plate, p, where(r)), tile)
        tiles.append(tile)
        key.append(dict(tile=n, plate=plate, page=p, sub=r["sub"], where=where(r), rounded=r["rounded"], type=r["type"],
                        filed=r["filed"]["ext"], no_cut=(r["no_cut"] or {}).get("ext"), no_cut_noh=(r["no_cut"] or {}).get("noh"),
                        no_line_rows_noh=(r["no_line_rows"] or {}).get("noh")))
json.dump(key, open(out + "/key.json", "w"), indent=1)
print(json.dumps(key))
