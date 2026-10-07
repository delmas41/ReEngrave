"""lane-edge-merge-unseen-ledgers (2026-10-06): the NEW arm only of farhead_per_bar_grid_oos.py (the per-bar grid reader on the current
tree), so a before/after of the reader change costs one arm. Same inputs, same output shape (`old` is None).

Original docstring: OUT OF SAMPLE on the 10-06 night-combined records (Litolff pp.4-16, Brahms pp.2-26).
EVERY far head read twice on this tree, in the gather's deskewed frame, no gather, records read only:

  OLD  keyword `per_bar_grid` OFF -- the record's raw staff-wide lines, the +-0.5 sp top-row re-find
  NEW  keyword ON -- the per-bar grid of the head's own bar (for the owner witness: the neighbour's grid at the head's x),
       +-0.3 sp, centre of the dark run

and, for each, the position AND the owner witness (`far_head_owner.owner_by_ledgers`, both candidate staves). A page without
its own head shape reads from the document pool of its OWN arm (the gather's rule). Pass 1 reads every page with the shape it
has and keeps the pools; pass 2 re-reads only the pages that had none.

  python3 farhead_per_bar_grid_oos.py scan <litolff|brahms> <out.json> [--pages 4,5]
"""
from __future__ import annotations

import collections, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import farhead_note_first_oos as O
import farhead_per_bar_grid_lib as GL
import lines_combined_5_lib as LC5
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_owner as FO, far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

NIGHT = "20261006-night-combined"
# attribution: EM_ONLY=a,b -- only these of the new switches on; EM_OFF=a,b -- these off (all others on)
_SW = ("edge_jut_kept", "split_welded_bands", "walk_tol", "rows_clear_of_box")
if os.environ.get("EM_ONLY"):
    for _k in _SW:
        FH.READER_KEYWORDS[_k] = _k in os.environ["EM_ONLY"].split(",")
for _k in filter(None, os.environ.get("EM_OFF", "").split(",")):
    FH.READER_KEYWORDS[_k] = False
SHAPE_FROM_OLD = "--shape-from-old" in sys.argv   # attribution: NEW lines, the OLD arm's head shape
DOCS = {
    "litolff": ("beethoven5-litolff", f"beethoven5-litolff-mvt1-whole-{NIGHT}.record.json", range(4, 17)),
    "brahms": ("brahms1-breitkopf", f"brahms1-breitkopf-mvt1-whole-{NIGHT}.record.json", range(2, 27)),
}


def _arm_read(r):
    d = r.get("detail") or {}
    nf = d.get("note_first") or {}
    return dict(pos=r["pos"], reason=r["reason"], kind=nf.get("kind"), how=nf.get("how"), line_y=nf.get("line_y"),
                edge_y=d.get("edge_y"), k=nf.get("k"), between=nf.get("between"),
                box_used=r.get("box_used"), lines=r.get("lines_used"), fit=r.get("fit"),
                box_source=r.get("box_source"), rungs=r.get("_rungs"))


def _owner(ctx, h, own_key, staves, gray):
    o = FO.owner_by_ledgers(ctx, h["subject"], h["box"], h["cls"], own_key, staves)
    cx = (h["box"][0] + h["box"][2]) / 2.0
    cands = {}
    for k, v in o["candidates"].items():
        st = next(s for s in staves if s["key"] == k)
        ln = FH.frame_lines_for_head(gray, FO.lines_at(st, cx), tuple(float(x) for x in h["box"]))
        cands[k] = dict(fits=v["fits"], pos=v["pos"], reason=v["reason"], unread=bool(v.get("unread")),
                        lines=[float(y) for y in ln], line_y=(v.get("note_first") or {}).get("line_y"),
                        edge_y=v.get("edge_y"))
    return dict(owner=o["owner"], word=o["word"], neighbour=o["neighbour"], cands=cands)


def read_arm(new, gray, heads_raw, heads_grid, page_boxes, staff_lines, staves, far_subjects, pool, adopt, force=None):
    """-> (ctx, rows{subject: dict}); `pool` collects this arm's clean-head samples; `adopt` = a pooled shape or None."""
    FH.READER_KEYWORDS["per_bar_grid"] = new
    heads = heads_grid if new else heads_raw
    ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
    pool.extend(ctx.samples)
    if force is not None:
        ctx.adopt(force, "forced")
    elif ctx.shape is None and adopt is not None:
        ctx.adopt(adopt, "document pool")
    rows = {}
    if ctx.shape is None:
        return ctx, rows
    for h in heads:
        if h["subject"] not in far_subjects:
            continue
        own_key = "staff/" + "/".join(h["subject"].split("/")[1:4])
        LC5._CAP.clear()
        r = ctx.read(h["subject"], h["box"], h["cls"], h["global_lines"])
        r["_rungs"] = LC5.candidates(dict(LC5._CAP)) if LC5._CAP else None
        rows[h["subject"]] = dict(read=_arm_read(r), owner=_owner(ctx, h, own_key, staves, gray))
    return ctx, rows


def scan(which, out_json, only_pages=None):
    doc, fname, pages = DOCS[which]
    cfg = ts.DOCS[doc]
    t0 = time.time()
    rec = EXP.Record(load_record(O.SHARED / fname))
    glyphs = collections.defaultdict(list)
    recorded = {}
    for o in rec.observations:
        if o["quantity"] == Q.GLYPH_BOX and o.get("value"):
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                glyphs[int(o["subject"].split("/")[1])].append(
                    (o["subject"], o["value"][0], tuple(float(v) for v in pb),
                     float(o.get("score") if o.get("score") is not None else 1.0)))
        elif o["quantity"] == Q.FAR_HEAD_LEDGER_POSITION:
            try:
                recorded[o["subject"]] = int(round(float(o["value"])))
            except (TypeError, ValueError):
                pass
    print("record loaded", round(time.time() - t0), "s", flush=True)
    pools = {False: [], True: []}
    rows_out, held, stats = {}, [], collections.Counter()

    def do_page(page, adopt):
        pi = render_page_matching_gather(cfg["pdf"], page, 600)
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        heads_raw, staff_lines, page_boxes = O.page_inputs(rec, page, glyphs[page])
        far = {h["subject"] for h in heads_raw if lg.far_head_needs_ledger_read(h["pos"])}
        if not far:
            return None
        grid_of, staves, raw, unmatched, _pws, _cells = GL.bar_grids(rec, page, pi)
        stats["staves_unmatched"] += len(unmatched)
        heads_grid = []
        for h in heads_raw:
            g = grid_of.get(GL.head_cell(h["subject"]))
            if g is None and h["subject"] in far:
                stats["far_head_no_grid"] += 1
            heads_grid.append(dict(h, global_lines=g or h["global_lines"]))
        for k in FH.GRID_STATS:
            FH.GRID_STATS[k] = 0
        res = {}
        try:
            for new in (True,):
                force = None
                ctx, rows = read_arm(new, gray, heads_raw, heads_grid, page_boxes, staff_lines, staves, far,
                                     pools[new], adopt[new] if adopt else None, force)
                res[new] = (ctx, rows)
                if new:
                    res["grid_stats"] = dict(FH.GRID_STATS)
        finally:
            FH.READER_KEYWORDS["per_bar_grid"] = True
        return far, res, heads_raw

    for page in pages:
        if page not in glyphs or (only_pages and page not in only_pages):
            continue
        t1 = time.time()
        out = do_page(page, None)
        if out is None:
            continue
        far, res, heads_raw = out
        missing = [n for n in (True,) if res[n][0].shape is None]
        print(which, "page", page, "far", len(far), "shape new",
              res[True][0].shape_source, "grid", res.get("grid_stats"),
              round(time.time() - t1), "s", flush=True)
        if missing:
            held.append(page)
            continue
        for s in far:
            rows_out[s] = dict(old=None, new=res[True][1].get(s), recorded=recorded.get(s), page=page)
        stats["grid_" + "refound"] += res["grid_stats"]["refound"]
        stats["grid_not_found"] += res["grid_stats"]["from_grid_not_found"]
        stats["grid_pair"] += res["grid_stats"]["from_grid_pair"]
    adopt = {n: FH.pooled_shape(pools[n]) for n in (False, True)}
    adopt[False] = None
    print("pools", {n: len(pools[n]) for n in pools}, "held pages", held, flush=True)
    for page in held:
        t1 = time.time()
        out = do_page(page, adopt)
        if out is None:
            continue
        far, res, heads_raw = out
        for s in far:
            rows_out[s] = dict(old=None, new=res[True][1].get(s), recorded=recorded.get(s), page=page,
                               pooled=True)
        stats["grid_refound"] += res["grid_stats"]["refound"]
        stats["grid_not_found"] += res["grid_stats"]["from_grid_not_found"]
        stats["grid_pair"] += res["grid_stats"]["from_grid_pair"]
        print(which, "held page", page, "far", len(far), "grid", res["grid_stats"], round(time.time() - t1), "s", flush=True)
    Path(out_json).write_text(json.dumps(dict(stats=dict(stats), heads=rows_out), default=str))
    print("done", len(rows_out), "far heads", dict(stats), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "scan":
        pages = None
        if "--pages" in sys.argv:
            pages = {int(v) for v in sys.argv[sys.argv.index("--pages") + 1].split(",")}
        scan(sys.argv[2], sys.argv[3], pages)
