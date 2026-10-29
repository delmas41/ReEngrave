"""2.222 cause, the CONTROL's comparison: is every written head box on the page the detector's OWN box?

    python3 benchmarks/notehead-box-cap-2026-10/cause/compare.py litolff 2

For each written-note head box of the page (2.202f ON arm, census extract), find the raw ultralytics box (capture.py, xyxy in the
cell image) whose page rectangle -- cell x0,y0 + xyxy / upscale, computed HERE, independently of gather._page_box -- is nearest.
Reports the max corner difference (page px). A box enlarged by any step after the detector cannot match a raw box within 1 px:
the control is run on the 2.221 tile-6 census UNION box (an enlargement we know of) and must FAIL to match.
"""
import json, pathlib, pickle, sys
HERE = pathlib.Path(__file__).resolve().parent
SCR = pathlib.Path("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad")
plate, pg = sys.argv[1], int(sys.argv[2])
calls = json.loads((SCR / "cap" / ("%s.p%d.raw.json" % (plate, pg))).read_text())
raw = []
for c in calls:
    x0, y0 = c["cell_bbox_page_px"][:2]; u = c["upscale"]
    for r in c.get("raw", []):
        a = r["xyxy"]
        raw.append(dict(cls=r["cls"], conf=r["conf"], floor=c.get("conf"), box=[x0 + a[0] / u, y0 + a[1] / u, x0 + a[2] / u, y0 + a[3] / u]))
D = pickle.loads((SCR / "census-extract.pkl").read_bytes())[plate]
by = {r["subject"]: r for r in D["rows"]["glyph_box"]}
rows = json.loads((HERE / "rows.json").read_text())
eye = {r["key"]: r for r in rows if r["plate"] == plate}


def nearest(b, cls=None):
    best = None
    for r in raw:
        if cls and r["cls"] != cls:
            continue
        d = max(abs(r["box"][i] - b[i]) for i in range(4))
        if best is None or d < best[0]:
            best = (d, r)
    return best


keys = sorted({h["rg"] for h in D["hosts"] if h["kind"] == "note" and h["page"] == pg})
worst, n_ok, big = 0.0, 0, []
for k in keys:
    g = by[k]; b = g["detail"]["bbox_page_px"]
    d, r = nearest(b, g["value"][0])
    worst = max(worst, d); n_ok += d <= 1.0
    if k in eye and eye[k]["group"] == "big":
        big.append((k, g["reader"], round(d, 2), r["conf"], r["floor"]))
print("%s p%d: written head boxes %d, matched to a raw detector box within 1 px: %d, worst corner diff %.3f px" % (plate, pg, len(keys), n_ok, worst))
print("oversized ones on this page (key, reader, diff px, raw conf, conf floor of the call):")
for x in big:
    print("   ", x)
union = [2097.52, 3472.52, 2128.4, 3511.72]          # 2.221 tile 6: the census's head|rest8th union, an enlargement by construction
d, r = nearest(union)
print("CONTROL 2.221 tile-6 union box: nearest raw box differs by %.2f px (%s) -> %s" % (d, r["cls"], "CAUGHT" if d > 1.0 else "MISSED"))
import numpy as np
cb, cn = [], []
for k in keys:
    g = by[k]; b = g["detail"]["bbox_page_px"]
    d, r = nearest(b)
    (cb if (k in eye and eye[k]["group"] == "big") else cn).append(r["conf"])
print("detector confidence of written head boxes on this page: oversized median %.2f (n %d) vs the rest median %.2f (n %d, p10 %.2f)"
      % (np.median(cb), len(cb), np.median(cn), len(cn), np.percentile(cn, 10)))
for k in keys:
    g = by[k]; b = g["detail"]["bbox_page_px"]
    d, r = nearest(b, g["value"][0])
    if d > 1.0:
        d2, r2 = nearest(b)
        print("UNMATCHED", k, g["reader"], g["value"][0], [round(v, 1) for v in b],
              {kk: vv for kk, vv in g["detail"].items() if kk != "bbox_page_px"}, "nearest any-class raw", round(d2, 2), r2["cls"])
