"""2.274 step 1 measurement (STAGED GATHER reader `tools/omr/staged/page_arcs.py`, run on a saved gather's rows; no detector, no OCR).

    python3 measure.py PLATE PAGE OUTDIR [--tag 20261104-night]

Rebuilds the page canvas exactly as GATHER does (`canvas.py`), reads the rows of the saved night slice, runs the module's own `read_runs`,
`witnesses_of` and `seed_read`, and counts runs / witnessed / NEW / detector curves covered whole / MISSED. Writes OUTDIR/PLATE-pPAGE.step1.json.
`readback(rec, page)` reads the fields a gather with the flag ON files (the same fields), for the gather-vs-standalone control.
"""
import json
import os
import pathlib
import resource
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged import pipeline as P  # noqa: E402
from tools.omr.staged import page_strokes as PS  # noqa: E402
from tools.omr.staged import barline_columns as BC  # noqa: E402
from tools.omr.staged import page_arcs as PA  # noqa: E402

if os.environ.get("R2_PA_FILE"):        # the round-1 reader (git show 33a43d211:tools/omr/staged/page_arcs.py), for the before column on the same pages
    import importlib.util as _u
    _spec = _u.spec_from_file_location("page_arcs_r1", os.environ["R2_PA_FILE"])
    PA = _u.module_from_spec(_spec)
    _spec.loader.exec_module(PA)

REFUSED = "refused_not_an_arc"
for _kv in [t for t in os.environ.get("R2_SET", "").split(",") if t]:     # experiments: R2_SET="MAX_THICK_SP=0.6,JAG_SP=0.1"
    _k, _v = _kv.split("=")
    setattr(PA, _k, type(getattr(PA, _k))(_v))


def readback(rec, page):
    """The filed rows of one page as plain dicts (reads every detail field the reader files)."""
    out = []
    for o in PA.rows_of(rec, page):
        d = o.detail or {}
        out.append(dict(value=o.value, box=d.get("bbox_page_px"), points=d.get("points"), ends=d.get("ends"), width=d.get("width_spaces"),
                        sagitta=d.get("sagitta_spaces"), thickness=d.get("thickness_spaces"), resid=d.get("resid_spaces"), inked=d.get("inked"),
                        chord=d.get("chord_deg"), strokes=d.get("page_strokes"), witnesses=d.get("witnesses"), staff=d.get("staff"),
                        box_class=d.get("box_class")))
    return out


def slice_rows(plate, page, tag):
    d = L.slice_dir(plate, tag)
    rows, curves, refused = [], [], set()
    with open(d / "observations.jsonl") as fh:
        for line in fh:
            if '"glyph_box"' not in line and '"claimed_area"' not in line and '"system_arc"' not in line:
                continue
            o = json.loads(line)
            s = (o.get("subject") or "").split("/")
            if len(s) < 2 or s[1] != str(page):
                continue
            if o["quantity"] == "system_arc":
                curves.append(o)
            else:
                rows.append((o["quantity"], o["subject"], o["value"], o.get("detail")))
    with open(d / "verdicts.jsonl") as fh:
        for line in fh:
            if '"arc_kind"' not in line or REFUSED not in line:
                continue
            v = json.loads(line)
            s = (v.get("subject") or "").split("/")
            if len(s) > 1 and s[1] == str(page):
                refused.add(v["subject"])
    return rows, curves, refused


def covered_by(run_pts, trace, sp):
    """share of the curve's columns that one run lies within 0.6 sp of"""
    xs = run_pts[:, 0]
    ok = 0
    for x, t, b in trace:
        if x < xs[0] or x > xs[-1]:
            continue
        y = float(np.interp(x, xs, run_pts[:, 1]))
        if abs(y - (t + b) / 2.0) <= 0.6 * sp:
            ok += 1
    return ok / max(1, len(trace))


def main():
    argv = sys.argv[1:]
    tag = "20261104-night"
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        del argv[i:i + 2]
    plate, page, out = argv[0], int(argv[1]), pathlib.Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    pdf = str(L.LIB / L.PLATES[plate]["pdf"])
    t0 = time.time()
    import os
    cache = os.environ.get("R2_CACHE")
    cf = pathlib.Path(cache) / ("%s-p%d.canvas.npz" % (plate, page)) if cache else None
    import cv2
    if cf is not None and cf.exists():
        z = np.load(cf, allow_pickle=True)
        canvas, raw, sp, staves = z["canvas"], z["raw"], float(z["sp"]), json.loads(str(z["staves"]))
    else:
        (pws, cells), = P.prepare_pages(pdf, [page])
        asm = PS.assemble(pws, cells)
        sp = PS.page_spacing(pws)
        PS.carve_columns(asm.canvas, BC.fit_columns(pws), sp)
        canvas, raw = asm.canvas, pws.page.binary
        staves = [dict(lines=[float(y) for y in st.line_ys], x0=float(getattr(st, "x_start", 0) or 0), x1=float(getattr(st, "x_end", 0) or 0)) for st in pws.staves]
        if cf is not None:
            cf.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cf, canvas=canvas, raw=raw, sp=sp, staves=json.dumps(staves))
    t1 = time.time()
    cv2.imwrite(str(out / ("%s-p%d.raw.png" % (plate, page))), raw)
    rows, curves, refused = slice_rows(plate, page, tag)
    boxes, areas, arc_boxes = PA.inputs_from_rows(rows)
    line_ys = [y for s in staves for y in s['lines']]
    t2 = time.time()
    res = PA.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True)
    runs = res["runs"]
    by_run, alone = PA.witnesses_of(runs, arc_boxes, sp)
    t3 = time.time()
    blank = PA.blank_mask(canvas == 0, boxes, areas)
    seeded = []
    for b in alone:
        s = PA.seed_read(canvas, sp, line_ys, b["box"], blank)
        if s is not None:
            seeded.append(dict(box_subject=b["subject"], run=s))
    t4 = time.time()
    det = []
    for c in curves:
        d = c["detail"]
        pieces = d.get("pieces") or [c["subject"]]
        tr = d.get("trace") or []
        if not tr:
            continue
        det.append(dict(subject=c["subject"], pieces=pieces, refused=any(p in refused for p in pieces), x0=d["x_left_page"], x1=d["x_right_page"],
                        box=[d["x_left_page"], min(t for _x, t, _b in tr), d["x_right_page"], max(b for _x, _t, b in tr)], trace=tr,
                        cut=bool(d.get("cut_at_barline"))))
    kept = [c for c in det if not c["refused"]]
    pts = {r["id"]: np.array(r["pts"], float) for r in runs}
    for c in kept:
        best, bid = 0.0, None
        for r in runs:
            if r["box"][2] < c["x0"] or r["box"][0] > c["x1"]:
                continue
            sh = covered_by(pts[r["id"]], c["trace"], sp)
            if sh > best:
                best, bid = sh, r["id"]
        c["best"], c["run"] = round(best, 2), bid
        # AMENDMENT r2 (disclosed, made on the develop pages before the hold-out ran): a detector curve that joins two arcs meeting at a note is covered by the
        # UNION of the runs on it; the pre-registered one-run share stays the verdict and is reported first
        un = 0
        for x, t_, b_ in c["trace"]:
            for r in runs:
                if r["box"][0] <= x <= r["box"][2]:
                    P = pts[r["id"]]
                    if abs(float(np.interp(x, P[:, 0], P[:, 1])) - (t_ + b_) / 2.0) <= 0.6 * sp:
                        un += 1
                        break
        c["union"] = round(un / max(1, len(c["trace"])), 2)
        sd = 0.0
        for s in seeded:
            sd = max(sd, covered_by(np.array(s["run"]["pts"], float), c["trace"], sp))
        c["seeded_best"] = round(sd, 2)
        # why no run: the rejected track that lies under the curve for most of its span (else none was tracked)
        why, wbest = "no_track", 0.0
        for q in res["rejected"]:
            ov = min(q["x1"], c["x1"]) - max(q["x0"], c["x0"])
            if ov > 0 and c["box"][1] - 0.8 * sp <= q["y"] <= c["box"][3] + 0.8 * sp and ov / max(1.0, c["x1"] - c["x0"]) > wbest:
                why, wbest = "%s(%.2f)" % (q["why"], q["thick_sp"]), ov / max(1.0, c["x1"] - c["x0"])
        c["why_no_run"] = why if c["best"] < 0.8 else None
    summary = dict(plate=plate, page=page, sp=sp,
                   seconds=dict(canvas=round(t1 - t0, 1), rows=round(t2 - t1, 1), runs=round(t3 - t2, 2), seeded=round(t4 - t3, 2)),
                   peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),
                   runs=len(runs), rejected=res["why"], runs_witnessed=sum(1 for v in by_run.values() if v), runs_new=sum(1 for v in by_run.values() if not v),
                   arc_boxes=len(arc_boxes), boxes_without_run=len(alone), seeded_found=len(seeded),
                   curves_total=len(det), curves_refused=sum(1 for c in det if c["refused"]), curves_kept=len(kept),
                   whole=sum(1 for c in kept if c["best"] >= 0.8), partial=sum(1 for c in kept if 0.3 <= c["best"] < 0.8),
                   none=sum(1 for c in kept if c["best"] < 0.3),
                   whole_after_seed=sum(1 for c in kept if c["best"] >= 0.8 or c["seeded_best"] >= 0.8),
                   whole_union=sum(1 for c in kept if c["union"] >= 0.8))
    ink = canvas == 0
    for c in kept:
        x0, y0, x1, y1 = [int(v) for v in c["box"]]
        reg = (slice(max(0, y0 - 8), y1 + 8), slice(max(0, x0), x1))
        tot = int(ink[reg].sum())
        c["blank_share"] = round(float((ink & blank)[reg].sum()) / max(1, tot), 2)
    json.dump(dict(summary=summary, staves=staves, runs=[dict(r, witnesses=by_run[r["id"]]) for r in runs], seeded=seeded, alone=alone,
                   curves=[{k: v for k, v in c.items() if k != "trace"} for c in det]), open(out / ("%s-p%d.step1.json" % (plate, page)), "w"))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
