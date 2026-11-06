"""PAGE-INK ARCS feasibility (measure only). Step 3: score ink-first runs and the detector-first page curves by the rule in RULES.md.

    python3 score.py PLATE PAGE WORKDIR LEDGER.json [--look]

LEDGER.json = the deep-dive ledger of the saved 20261104-night replay (branch arc-deep-dive-2026-11, `results/<plate>.base.ledger.json`):
one row per page curve (Q.SYSTEM_ARC; an over-joined chain split into its boxes), with `fate` ('not_an_arc' = refused).
Brahms p0 is scored against Sean's hand arcs (data/hand-truth/pages/imslp317803/0.json); Litolff p16 has none (RULES.md).
--look writes overview images (runs green, detector curves orange, hand arcs blue) to WORKDIR for the agent's own look.
"""
import collections
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
TRUTH = ROOT / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"


def printed_arcs(sp):
    hb = [b for b in json.load(open(TRUTH))["boxes"] if b["cls"] in ("slur", "tie")]
    for b in hb:
        s, st, m = b["cell_id"].split("-")
        b["_k"] = (s, st, int(m[1:]))
    parent = list(range(len(hb)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(hb):
        for j, b in enumerate(hb):
            if a["_k"][:2] != b["_k"][:2] or b["_k"][2] != a["_k"][2] + 1:
                continue
            ra, rb = a["rect"], b["rect"]
            if abs(rb[0] - ra[2]) <= 1.5 * sp and min(ra[3], rb[3]) > max(ra[1], rb[1]):
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i in range(len(hb)):
        groups[find(i)].append(hb[i])
    out = []
    for g in groups.values():
        rects = [b["rect"] for b in g]
        out.append(dict(ids=[b["id"] for b in g], cls=sorted({b["cls"] for b in g}), rects=rects,
                        x0=min(r[0] for r in rects), x1=max(r[2] for r in rects),
                        box=[min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]))
    return out


def inside(px, py, rects, g):
    return any(r[0] - g <= px <= r[2] + g and r[1] - g <= py <= r[3] + g for r in rects)


def covered(spans, x0, x1):
    """share of [x0, x1] covered by the union of spans"""
    if x1 <= x0:
        return 0.0
    ev = sorted((max(a, x0), min(b, x1)) for a, b in spans if min(b, x1) > max(a, x0))
    tot, cur0, cur1 = 0.0, None, None
    for a, b in ev:
        if cur1 is None or a > cur1:
            if cur1 is not None:
                tot += cur1 - cur0
            cur0, cur1 = a, b
        else:
            cur1 = max(cur1, b)
    if cur1 is not None:
        tot += cur1 - cur0
    return tot / (x1 - x0)


def fate(arcs, items, sp, key="on"):
    """items: dicts with 'span' (x0, x1), 'on' predicate(arc) -> bool. Returns per arc fate and the set of items on some arc."""
    used = set()
    res = collections.Counter()
    per = []
    for a in arcs:
        on = [k for k, it in enumerate(items) if it[key](a)]
        used.update(on)
        best = max((covered([items[k]["span"]], a["x0"], a["x1"]) for k in on), default=0.0)
        union = covered([items[k]["span"] for k in on], a["x0"], a["x1"])
        f = "whole" if best >= 0.8 else "pieces" if union >= 0.8 else "short" if union >= 0.3 else "missed"
        res[f] += 1
        per.append(dict(ids=a["ids"], fate=f, best=round(best, 2), union=round(union, 2), n_on=len(on)))
    return res, used, per


def clipped_on(pts, a, sp):
    """CLIPPED rule (added after the look, see FINDINGS): Sean's hand arcs are one box per CELL and not every cell's half is boxed, so a run
    longer than the boxed part fails '70% of ITS points inside'. Clipped: of the run's points within the arc's own x span (+-0.5 sp), >= 70%
    lie in the arc's hand boxes grown 0.5 sp, and they reach over >= 30% of the span."""
    g = 0.5 * sp
    sel = pts[(pts[:, 0] >= a["x0"] - g) & (pts[:, 0] <= a["x1"] + g)]
    if len(sel) < 2 or (sel[:, 0].max() - sel[:, 0].min()) < 0.3 * (a["x1"] - a["x0"]):
        return False
    return np.mean([inside(x, y, a["rects"], g) for x, y in sel]) >= 0.7


def ink_items(runs, sp):
    items = []
    for r in runs:
        pts = np.array(r["pts"])
        it = dict(id=r["id"], span=(float(pts[:, 0].min()), float(pts[:, 0].max())), box=r["box"], pts=pts)
        it["on"] = (lambda a, pts=pts: np.mean([inside(x, y, a["rects"], 0.5 * sp) for x, y in pts]) >= 0.7)
        it["on_clip"] = (lambda a, pts=pts: clipped_on(pts, a, sp))
        items.append(it)
    return items


def det_items(rows, page, sp):
    items = []
    for r in rows:
        if r.get("page") != page or r.get("fate") == "not_an_arc":
            continue
        b = r.get("box")
        if r.get("x_left") is None:          # a box with no page curve row: the box is all the path has
            if not b:
                continue
            r = dict(r, x_left=b[0], x_right=b[2], y_left=(b[1] + b[3]) / 2.0, y_right=(b[1] + b[3]) / 2.0)
        x0, x1 = float(r["x_left"]), float(r["x_right"])
        b = b or [x0, min(r["y_left"], r["y_right"]), x1, max(r["y_left"], r["y_right"])]
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        ys = np.linspace(r["y_left"], r["y_right"], 41)
        xs = np.linspace(x0, x1, 41)
        it = dict(id=r["curve"], span=(x0, x1), box=b, fate=r["fate"],
                  pts=np.stack([xs, ys], 1))
        it["on"] = (lambda a, cx=cx, cy=cy, xs=xs, ys=ys: inside(cx, cy, a["rects"], 0.5 * sp)
                    and np.mean([inside(x, y, a["rects"], 0.5 * sp) for x, y in zip(xs, ys)]) >= 0.7)
        it["on_clip"] = (lambda a, P=np.stack([xs, ys], 1): clipped_on(P, a, sp))
        items.append(it)
    return items


def overlaps(a, b, g=0):
    return min(a[2], b[2]) + g > max(a[0], b[0]) and min(a[3], b[3]) + g > max(a[1], b[1])


def main():
    plate, page, wd, ledger = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4]
    stem = "%s-p%d" % (plate, page)
    raw_stem = stem
    for v in ("--v2", "--v3", "--v4"):
        if v in sys.argv:
            stem += v[1:].replace("-", ".")
    R = json.load(open(wd / (stem + ".runs.json")))
    sp = float(R["sp"])
    rows = json.load(open(ledger))["rows"]
    ink = ink_items(R["runs"], sp)
    det = det_items(rows, page, sp)
    report = dict(plate=plate, page=page, ink_runs=len(ink), det_curves=len(det))
    if plate == "brahms" and page == 0:
        arcs = printed_arcs(sp)
        report["hand_boxes"] = sum(len(a["ids"]) for a in arcs)
        report["printed_arcs"] = len(arcs)
        report["printed_arcs_multi_cell"] = sum(1 for a in arcs if len(a["ids"]) > 1)
        fi, ui, pi = fate(arcs, ink, sp)
        fd, ud, pd = fate(arcs, det, sp)
        report["ink_first"] = dict(fi)
        report["detector_first"] = dict(fd)
        report["ink_fakes"] = [it["id"] for k, it in enumerate(ink) if k not in ui]
        report["det_fakes"] = [it["id"] for k, it in enumerate(det) if k not in ud]
        # the clipped rule, per grouped printed arc and per hand box (one cell piece each, no grouping)
        ci, uci, pci = fate(arcs, ink, sp, "on_clip")
        cd, ucd, pcd = fate(arcs, det, sp, "on_clip")
        report["CLIPPED_ink_first"] = dict(ci)
        report["CLIPPED_detector_first"] = dict(cd)
        report["CLIPPED_ink_unmatched"] = [it["id"] for k, it in enumerate(ink) if k not in uci]
        report["CLIPPED_det_unmatched_n"] = len([1 for k in range(len(det)) if k not in ucd])
        cells = [dict(ids=[i], rects=[r], x0=r[0], x1=r[2], box=r) for a in arcs for i, r in zip(a["ids"], a["rects"])]
        report["CLIPPED_per_hand_box_ink"] = dict(fate(cells, ink, sp, "on_clip")[0])
        report["CLIPPED_per_hand_box_det"] = dict(fate(cells, det, sp, "on_clip")[0])
        report["per_arc_clipped"] = [dict(ids=a["ids"], box=arc["box"], ink=a["fate"], det=b["fate"]) for a, b, arc in zip(pci, pcd, arcs)]
        both = collections.Counter((a["fate"], b["fate"]) for a, b in zip(pi, pd))
        report["ink_vs_det"] = {"%s|%s" % k: v for k, v in sorted(both.items())}
        multi = collections.Counter((a["fate"], b["fate"]) for a, b, arc in zip(pi, pd, arcs) if len(arc["ids"]) > 1)
        report["multi_cell_ink_vs_det"] = {"%s|%s" % k: v for k, v in sorted(multi.items())}
        report["per_arc"] = [dict(ids=a["ids"], box=arc["box"], ink=a["fate"], ink_best=a["best"], det=b["fate"], det_best=b["best"])
                             for a, b, arc in zip(pi, pd, arcs)]
    else:
        # no truth: agreement with the detector path's kept curves, and the ink runs no kept curve overlaps (to be LOOKED at)
        lone = [it["id"] for it in ink if not any(overlaps(it["box"], d["box"], 0.3 * sp) for d in det)]
        report["ink_runs_no_det_curve"] = lone
        cover = collections.Counter()
        report["det_curves_no_run"] = []
        for d in det:
            on = [it for it in ink if overlaps(it["box"], d["box"], 0.3 * sp)]
            best = max((covered([it["span"]], *d["span"]) for it in on), default=0.0)
            cover["det_curve_covered_by_one_run>=0.8" if best >= 0.8 else "partly" if best >= 0.3 else "no_run"] += 1
            if best < 0.8:
                report["det_curves_no_run"].append(dict(id=d["id"], box=d["box"], fate=d["fate"], best=round(best, 2)))
        report["det_curves_vs_ink"] = dict(cover)
        report["det_curve_widths_sp"] = sorted(round((d["span"][1] - d["span"][0]) / sp, 1) for d in det)
        report["ink_run_widths_sp"] = sorted(round((it["span"][1] - it["span"][0]) / sp, 1) for it in ink)
    json.dump(report, open(wd / (stem + ".score.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("per_arc", "per_arc_clipped")}, default=str)[:3000])
    if "--look" in sys.argv:
        import cv2
        img = cv2.cvtColor(cv2.imread(str(wd / (raw_stem + ".raw.png")), 0), cv2.COLOR_GRAY2BGR)
        if plate == "brahms" and page == 0:
            for a in printed_arcs(sp):
                for r in a["rects"]:
                    cv2.rectangle(img, (int(r[0]), int(r[1])), (int(r[2]), int(r[3])), (255, 120, 0), 3)
        for d in det:
            b = d["box"]
            cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 140, 255), 2)
        for it in ink:
            cv2.polylines(img, [it["pts"].astype(np.int32).reshape(-1, 1, 2)], False, (0, 180, 0), 4)
            cv2.putText(img, str(it["id"]), (int(it["box"][0]), int(it["box"][1]) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 140, 0), 2)
        cv2.imwrite(str(wd / (stem + ".look.png")), img)


if __name__ == "__main__":
    main()
