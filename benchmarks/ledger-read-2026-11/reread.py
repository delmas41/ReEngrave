"""2.255: re-run GATHER's far-head ledger reader (`FarHeadPage.read`, the `_file_far_head_reading` inputs) on the
20261029-night slice pages, from the record's own boxes / positions / staff lines + the page raster, and compare with
the record's `far_head_ledger_position` rows.  CONTROL (can fail): with the tree's reader the re-read must reproduce
the record (`repro`); only then is a changed reader's difference a difference.

usage: reread.py PLATE OUT.json [subject ...]     (env LEDGER_TRACE=1 prints the reader's internals per subject)
"""
from __future__ import annotations

import collections
import json
import os
import sys

import cv2

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import extract_measures

TAG = os.environ.get("SLICE_TAG", "20261029-night")


def load(plate):
    base = LR.slice_dir(plate, TAG)
    obs = [json.loads(l) for l in open(base / "observations.jsonl")]
    abst = [json.loads(l) for l in open(base / "abstentions.jsonl")]
    pages = json.load(open(base / "stamp.json"))["pages"]
    return obs, abst, pages


def page_grids(pi, staff_lines, page):
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    by_staff = collections.defaultdict(list)
    for c in cells:
        by_staff[c.staff_index].append(c)
    grid = {}
    unmatched = 0
    for key, lines in staff_lines.items():
        if not key.startswith("staff/%d/" % page):
            continue
        st = next((t for t in pws.staves if [float(v) for v in t.line_ys] == lines), None)
        if st is None:
            unmatched += 1
            continue
        _, _p, s, k = key.split("/")
        for c in by_staff.get(st.staff_index, []):
            gl = FH.cell_grid_page_lines(c)
            if gl is not None:
                grid[(int(s), int(k), c.measure_index)] = gl
    return grid, unmatched


def spy_read(ctx, subject, box, cls, gl):
    cap = {}
    o_nf = lg.derive_note_first_step

    def spy(img_gray, head_box, edge_y, sign, spacing, rungs_y, *a, **kw):
        cap.update(rungs=[round(float(v), 1) for v in rungs_y], edge=round(float(edge_y), 1), sign=sign,
                   sp=round(float(spacing), 2), box=[round(float(v), 1) for v in head_box])
        r = o_nf(img_gray, head_box, edge_y, sign, spacing, rungs_y, *a, **kw)
        cap["nf"] = {k: (v if not isinstance(v, float) else round(v, 2)) for k, v in r.items()
                     if k in ("offset", "reason", "kind", "how", "line_y", "k", "between", "gaps")}
        return r
    lg.derive_note_first_step = spy
    try:
        r = ctx.read(subject, box, cls, gl)
    finally:
        lg.derive_note_first_step = o_nf
    return r, cap


def main(plate, out, only=()):
    obs, abst, pages = load(plate)
    rec = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            rec[o["subject"]] = ("pos", int(o["value"]), o["detail"].get("ledger_reason"))
    for a in abst:
        if a["quantity"] == "far_head_ledger_position":
            rec[a["subject"]] = ("abs", None, (a.get("detail") or {}).get("ledger_reason"))
    boxes = collections.defaultdict(list)
    geo, cls_of, conf = {}, {}, {}
    staff_lines, cell_box, cross, extent = {}, {}, {}, {}
    for o in obs:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            b = o["detail"]["bbox_page_px"]
            boxes[LR.page_of(s)].append((s, o["value"][0], tuple(float(v) for v in b)))
            cls_of[s] = o["value"][0]
            conf[s] = o.get("score") or 0.0
        elif q == "notehead_staff_position":
            geo[s] = int(round(float(o["value"])))
        elif q == "staff_lines":
            staff_lines[s] = [float(v) for v in o["value"]]
        elif q == "cell_box":
            cell_box[tuple(int(v) for v in s.split("/")[1:5])] = tuple(float(v) for v in o["value"])
        elif q == "staff_extent":
            extent[s] = [float(v) for v in o["value"]]
        elif q == "notehead_stem_cross_ink":
            cross[s] = dict(o.get("detail") or {})
    cuts = collections.defaultdict(set)
    for (p, sy, st, _c), bb in cell_box.items():
        cuts[(p, sy, st)].update((bb[0], bb[2]))
    ctxs, jobs_by_page, pool = {}, {}, []
    pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
    for page in pages:
        pi = render_page(pdf, page, dpi=600)
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        grid, unmatched = page_grids(pi, staff_lines, page)
        heads, used, jobs = [], {}, []
        for (s, c, b) in boxes[page]:
            if not c.startswith("notehead") or s not in geo:
                continue
            p = s.split("/")
            own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            if own not in staff_lines:
                continue
            used[own] = staff_lines[own]
            gl = grid.get((int(p[2]), int(p[3]), int(p[4]))) or staff_lines[own]
            heads.append(dict(subject=s, box=b, pos=geo[s], cls=c, score=float(conf.get(s, 0.0)), global_lines=gl))
            if lg.far_head_needs_ledger_read(geo[s]):
                jobs.append(dict(subject=s, box=b, cls=c, gl=gl))
        nan = {}
        for j in jobs:
            p = [int(v) for v in j["subject"].split("/")[1:5]]
            ev = dict(cell_box=cell_box.get(tuple(p)), barline_xs=sorted(cuts.get(tuple(p[:3]), ())))
            if j["subject"] in cross:
                ev["cross"] = cross[j["subject"]]
            nan[j["subject"]] = ev
        ctx = FH.FarHeadPage(gray, heads, boxes[page], used, not_a_note=nan)
        pool.extend(ctx.samples)
        ctxs[page], jobs_by_page[page] = ctx, jobs
        print(plate, "page", page, "far jobs", len(jobs), "own shape", ctx.shape is not None,
              "grid cells", len(grid), "unmatched staves", unmatched, flush=True)
    pooled = FH.pooled_shape(pool)
    # the record's own pool size per page (`document pool n=N`): the whole-movement pool (pool_samples.py), first N
    want_n = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            src = str(o["detail"].get("shape_source") or "")
            if src.startswith("document pool n="):
                want_n[LR.page_of(o["subject"])] = int(src.split("=")[1])
    doc_pool = []
    pj = os.environ.get("POOL_JSON")
    if pj:
        allp = json.load(open(pj))
        for k in sorted(allp, key=int):
            doc_pool.extend(allp[k])
    res, stats = {}, collections.Counter()
    trace = os.environ.get("LEDGER_TRACE")
    for page in pages:
        ctx = ctxs[page]
        if ctx.shape is None and doc_pool and page in want_n:
            ctx.adopt(FH.pooled_shape(doc_pool[:want_n[page]]), "document pool n=%d" % want_n[page])
        if ctx.shape is None and pooled is not None:
            ctx.adopt(pooled, "pool n=%d" % len(pool))
        for j in jobs_by_page[page]:
            s = j["subject"]
            if only and s not in only:
                continue
            r, cap = spy_read(ctx, s, j["box"], j["cls"], j["gl"])
            got = ("pos", r["pos"], r["reason"]) if r["pos"] is not None else ("abs", None, r["reason"])
            want = rec.get(s)
            same = want is not None and got[0] == want[0] and got[1] == want[1]
            stats["repro" if same else ("no_record_row" if want is None else "differs")] += 1
            nb_read = None
            if os.environ.get("OWNER"):
                from tools.omr.annotate import far_head_owner as FO
                p_ = s.split("/")
                staves = [dict(key=k, lines=v, x0=extent[k][0], x1=extent[k][1]) for k, v in staff_lines.items()
                          if k.startswith("staff/%s/" % p_[1]) and k in extent]
                nb = FO.neighbour_staff(j["box"], "staff/%s/%s/%s" % (p_[1], p_[2], p_[3]), staves)
                if nb is not None:
                    rd = FO.read_toward(ctx, s, j["box"], j["cls"], nb["lines"])
                    nb_read = [nb["key"], rd.get("pos"), str(rd.get("reason"))[:60]]
            res[s] = dict(got=list(got), rec=list(want) if want else None, same=same, cap=cap, nb=nb_read,
                          box_used=[round(float(v), 1) for v in (r.get("box_used") or ())],
                          lines=[round(float(v), 1) for v in (r.get("lines_used") or ())])
            if trace:
                print(json.dumps(dict(s=s, **res[s]), default=str))
    print(plate, dict(stats), flush=True)
    json.dump(dict(stats=dict(stats), heads=res), open(out, "w"), default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
