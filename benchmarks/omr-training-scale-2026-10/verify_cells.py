"""2.110 cell check: measure staff space on sampled training cells by a method INDEPENDENT of shown_space's comb
(morphological horizontal-line detection: open the Otsu-binarised cell with a long horizontal kernel, take the
rows that survive, cluster to line centres, keep the best 5 equal-gap run) and compare. Also draws both on the cell.
usage: verify_cells.py <pick.json> <outdir>
legend: GREEN = lines found by the independent run-length method; RED = the 5 lines the comb fit (survey) implies."""
import json, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from shown_space import measure_lines

def indep(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = g.shape
    _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    k = max(15, int(w * 0.25))
    op = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    rows = op.sum(axis=1) / 255.0
    ys = np.where(rows > 0.5 * k)[0]
    if len(ys) == 0:
        return None
    groups, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] <= 2: cur.append(y)
        else: groups.append(cur); cur = [y]
    groups.append(cur)
    cen = np.array([np.average(gr, weights=rows[gr]) for gr in groups])
    best = None
    for i in range(len(cen)):
        for j in range(i + 1, len(cen)):
            d = cen[j] - cen[i]
            if d < 2.5: continue
            # chain of 5 lines i, i+d ...: count how many centres sit within 12% of d of a lattice point
            hits = [cen[i] + k * d for k in range(-4, 5)]
            fit = [c for c in cen if min(abs(c - hp) for hp in hits) < 0.12 * d]
            if len(fit) < 5: continue
            # best consecutive 5 on this lattice
            idx = sorted(set(int(round((c - cen[i]) / d)) for c in fit))
            for a in idx:
                if all((a + k) in idx for k in range(5)):
                    pts = [cen[i] + (a + k) * d for k in range(5)]
                    snapped = [min(cen, key=lambda c: abs(c - p)) for p in pts]
                    gaps = np.diff(snapped)
                    score = gaps.std()
                    if best is None or score < best[0]:
                        best = (score, snapped)
    if best is None:
        return None
    sn = best[1]
    return float(np.median(np.diff(sn))), sn

if __name__ == "__main__":
    pick = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    res = []
    for x in pick:
        img = cv2.imread(x["path"])
        ind = indep(img)
        cm = measure_lines(img)
        vis = img.copy()
        if ind:
            for y in ind[1]: cv2.line(vis, (0, int(round(y))), (img.shape[1], int(round(y))), (0, 200, 0), 1)
        if cm:
            for k in range(5):
                y = int(round(cm[2] + k * cm[0])); cv2.line(vis, (0, y), (img.shape[1], y), (0, 0, 255), 1)
        # scale crop so it is viewable: max side 1000
        sc = min(1.0, 1000 / max(vis.shape[:2])); 
        if sc < 1: vis = cv2.resize(vis, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        ver = x["path"].split("/images/")[0].split("/")[-1].split("-")[0]
        name = f"{ver}_{Path(x['path']).stem}.png"
        cv2.imwrite(str(out / name), vis)
        r = {"cell": f"{ver}/{Path(x['path']).stem}", "h": x["h"], "w": x["w"], "survey": x["space"], "comb": x["comb"],
             "indep": None if ind is None else round(ind[0], 2), "file": name}
        r["err_px"] = None if ind is None or x["space"] is None else round(x["space"] - ind[0], 2)
        r["err_pct"] = None if r["err_px"] is None else round(100 * r["err_px"] / ind[0], 1)
        res.append(r); print(r)
    json.dump(res, open(out / "check.json", "w"), indent=1)
