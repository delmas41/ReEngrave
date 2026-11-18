"""ROADMAP 2.312 r2 -- re-run GATHER's far-head ledger reader (`FarHeadPage.read`, the inputs `_file_far_head_reading` gives it) on
saved frozen-sample slices, from the record's own boxes / positions / staff lines + the page raster (2.255's `ledger-read-2026-11/reread.py`,
with a slice dir and a page list). CONTROL (can fail): with the flag OFF the re-read must reproduce the record (`repro`); only then is
the ON arm's difference a difference.

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_reread.py PLATE SLICE_DIR PAGES OUT.json [subject ...]

env: OMR_LEDGER_COUNT_TO_INK=0|1 (the arm), LEDGER_TRACE=1 (print per subject), VARY=1 (step 2: for each subject also re-read with one
real-run input swapped for the page-ink-alone one: staff-wide lines, detector box, no other heads' boxes, no text/artic boxes, no outline
margin).
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


def page_grids(pi, staff_lines, page):
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    by_staff = collections.defaultdict(list)
    for c in cells:
        by_staff[c.staff_index].append(c)
    grid, unmatched = {}, 0
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
                     if k in ("offset", "reason", "kind", "how", "line_y", "k", "between", "gaps", "ink")}
        return r
    lg.derive_note_first_step = spy
    try:
        r = ctx.read(subject, box, cls, gl)
    finally:
        lg.derive_note_first_step = o_nf
    return r, cap


def load_rows(base, pages):
    want = ("far_head_ledger_position", "glyph_box", "notehead_staff_position", "staff_lines", "cell_box", "staff_extent",
            "notehead_stem_cross_ink")
    obs, abst = [], []
    for line in open(base / "observations.jsonl"):
        q = line[:400]
        if not any(('"quantity": "%s"' % w) in q for w in want):
            continue
        o = json.loads(line)
        p = LR.page_of(o["subject"])
        if p is None or p in pages:
            obs.append(o)
    for line in open(base / "abstentions.jsonl"):
        if '"far_head_ledger_position"' not in line[:400]:
            continue
        a = json.loads(line)
        if LR.page_of(a["subject"]) in pages:
            abst.append(a)
    return obs, abst


POOL_PAGES = {"litolff": [1, 2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}


def main(plate, slice_dir, pages, out, only=()):
    pages = [int(v) for v in pages.split(",")]
    pool_pages = POOL_PAGES[plate]
    obs, abst = load_rows(LR.pathlib.Path(slice_dir), set(pages) | set(pool_pages))
    rec = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            rec[o["subject"]] = ("pos", int(o["value"]), o["detail"].get("ledger_reason"), o["detail"].get("shape_source"))
    for a in abst:
        rec[a["subject"]] = ("abs", None, (a.get("detail") or {}).get("ledger_reason"), None)
    boxes = collections.defaultdict(list)
    geo, conf = {}, {}
    staff_lines, cell_box, cross = {}, {}, {}
    for o in obs:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            b = o["detail"]["bbox_page_px"]
            boxes[LR.page_of(s)].append((s, o["value"][0], tuple(float(v) for v in b)))
            conf[s] = o.get("score") or 0.0
        elif q == "notehead_staff_position":
            geo[s] = int(round(float(o["value"])))
        elif q == "staff_lines":
            staff_lines[s] = [float(v) for v in o["value"]]
        elif q == "cell_box":
            cell_box[tuple(int(v) for v in s.split("/")[1:5])] = tuple(float(v) for v in o["value"])
        elif q == "notehead_stem_cross_ink":
            cross[s] = dict(o.get("detail") or {})
    cuts = collections.defaultdict(set)
    for (p, sy, st, _c), bb in cell_box.items():
        cuts[(p, sy, st)].update((bb[0], bb[2]))
    pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
    # the document pool GATHER builds page by page (the slice's pages in gather order): a page with no shape of its own adopts the
    # first n samples, n = the record's own `document pool n=N`
    want_n = {}
    for o in obs:
        if o["quantity"] == "far_head_ledger_position":
            src = str(o["detail"].get("shape_source") or "")
            if src.startswith("document pool n="):
                want_n[LR.page_of(o["subject"])] = int(src.split("=")[1])
    doc_pool = []
    for page in pool_pages:
        hs = []
        for (s, c, b) in boxes[page]:
            p = s.split("/")
            own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            if c.startswith("notehead") and s in geo and own in staff_lines:
                hs.append(dict(subject=s, box=b, pos=geo[s], cls=c, score=float(conf.get(s, 0.0)), global_lines=staff_lines[own]))
        if not hs:
            continue
        g0 = cv2.cvtColor(render_page(pdf, page, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
        doc_pool.extend(FH.FarHeadPage(g0, hs, boxes[page], {}, not_a_note={}).samples)
    res, stats = {}, collections.Counter()
    trace = os.environ.get("LEDGER_TRACE")
    vary = os.environ.get("VARY")
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
            if s in rec or lg.far_head_needs_ledger_read(geo[s]):
                jobs.append(dict(subject=s, box=b, cls=c, gl=gl, own=own))
        nan = {}
        for j in jobs:
            p = [int(v) for v in j["subject"].split("/")[1:5]]
            ev = dict(cell_box=cell_box.get(tuple(p)), barline_xs=sorted(cuts.get(tuple(p[:3]), ())))
            if j["subject"] in cross:
                ev["cross"] = cross[j["subject"]]
            nan[j["subject"]] = ev
        ctx = FH.FarHeadPage(gray, heads, boxes[page], used, not_a_note=nan)
        # the record's own shape source (page or document pool): a page whose own shape the record did not use is read as the record did
        if ctx.shape is None and page in want_n:
            ctx.adopt(FH.pooled_shape(doc_pool[:want_n[page]]), "document pool n=%d" % want_n[page])
        print(plate, "page", page, "far jobs", len(jobs), "own shape", ctx.shape is not None, "grid cells", len(grid),
              "unmatched staves", unmatched, flush=True)
        for j in jobs:
            s = j["subject"]
            if only and s not in only:
                continue
            r, cap = spy_read(ctx, s, j["box"], j["cls"], j["gl"])
            got = ("pos", r["pos"], r["reason"]) if r["pos"] is not None else ("abs", None, r["reason"])
            want = rec.get(s)
            same = want is not None and got[0] == want[0] and got[1] == want[1] and (got[0] == "pos" or got[2] == want[2])
            stats["repro" if same else ("no_record_row" if want is None else "differs")] += 1
            row = dict(got=list(got), rec=list(want) if want else None, same=same, cap=cap, geo=geo.get(s),
                       box=[round(float(v), 1) for v in j["box"]],
                       box_used=[round(float(v), 1) for v in (r.get("box_used") or ())],
                       box_source=r.get("box_source"),
                       lines=[round(float(v), 1) for v in (r.get("lines_used") or ())])
            if vary and r.get("lines_used"):
                others = [(t, b) for (t, c, b) in boxes[page] if c.startswith("notehead")]
                acc = [(t, b) for (t, c, b) in boxes[page] if "ccidental" in c]
                base_kw = dict(text_boxes=ctx.text_boxes, thickness_px=ctx.thickness, artic_boxes=ctx.artic_boxes)
                use, lines = tuple(r["box_used"]), list(r["lines_used"])
                staff_wide = staff_lines[j["own"]]
                variants = {
                    "real": (lines, use, others, acc, base_kw),
                    "staff_wide_lines": (staff_wide, use, others, acc, base_kw),
                    "detector_box": (lines, tuple(j["box"]), others, acc, base_kw),
                    "no_other_heads": (lines, use, [], [], base_kw),
                    "no_text_artic": (lines, use, others, acc, dict(base_kw, text_boxes=None, artic_boxes=None)),
                    "no_outline_margin": (lines, use, others, acc, dict(base_kw, thickness_px=None)),
                    "alone_r1": (staff_wide, tuple(j["box"]), [], [], {}),
                }
                vv = {}
                for name, (ln, bx, oth, ac, kw) in variants.items():
                    try:
                        vv[name] = list(FH.read_absolute_position(gray, ln, bx, s, oth, ac, **kw))
                    except Exception as e:      # a variant that cannot run is said, not hidden
                        vv[name] = [None, "error " + repr(e)[:80]]
                row["vary"] = vv
            res[s] = row
            if trace:
                print(json.dumps(dict(s=s, **res[s]), default=str), flush=True)
    print(plate, dict(stats), flush=True)
    json.dump(dict(stats=dict(stats), heads=res), open(out, "w"), default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], set(sys.argv[5:]))
