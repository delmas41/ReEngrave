"""night 2026-10-06 read, step 2: replay the far-head reader on the gather-frame raster for every far head that has a
Q.FAR_HEAD_LEDGER_POSITION row, to recover the ledger rows it measured (for the off-box check) and, for the note-first
reader, the line it named / the ledgers it counted (for the sheet). Read only; no gather.

  python3 night_1006_replay.py <extract.json> <doc> new|base <out.json>

new  = the record's own reader (note-first, text-not-ledger, not-a-note: the tree's defaults).
base = the 10-04 run-2 reader (READER_KEYWORDS note_first / ledger_not_text / not_a_note off).
CONTROL (can fail): a replay whose position differs from the recorded decided position is `repro=False`; the census
leaves those out and counts them.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_measured as OM
import overnight_1004_report as R
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg


def read_spied(ctx, subject, box, cls, gl):
    cap = {}
    o_far, o_nf = lg.derive_far_head_step, lg.derive_note_first_step

    def spy_far(rungs_y, edge_y, sign, head_near_y, spacing, **kw):
        cap.update(rungs=list(rungs_y), edge=edge_y, sign=sign, sp=spacing)
        return o_far(rungs_y, edge_y, sign, head_near_y, spacing, **kw)

    def spy_nf(img_gray, head_box, edge_y, sign, spacing, rungs_y, *a, **kw):
        cap.update(rungs=list(rungs_y), edge=edge_y, sign=sign, sp=spacing)
        return o_nf(img_gray, head_box, edge_y, sign, spacing, rungs_y, *a, **kw)
    lg.derive_far_head_step, lg.derive_note_first_step = spy_far, spy_nf
    try:
        r = ctx.read(subject, box, cls, gl)
    finally:
        lg.derive_far_head_step, lg.derive_note_first_step = o_far, o_nf
    return r, cap


def main(src, doc, mode, out):
    new = mode == "new"
    FH.READER_KEYWORDS["note_first"] = new
    FH.READER_KEYWORDS["ledger_not_text"] = new
    FH.READER_KEYWORDS["not_a_note"] = new
    data = json.loads(Path(src).read_text())
    G = data["glyphs"]
    rep = OM.CachedReplay(doc, data)
    far = {s: g for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g and "fh" in g}
    by_page = collections.defaultdict(list)
    for s in far:
        by_page[R.page_of(s)].append(s)
    res, stats = {}, collections.Counter()
    for page in sorted(by_page):
        for s in by_page[page]:
            g = far[s]
            ctx = rep.adopt_for(page, g["fh"]["shape_source"])
            key = "staff/" + "/".join(s.split("/")[1:4])
            gl = data["staff_lines"][key]
            cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
            try:
                r, cap = read_spied(ctx, s, tuple(g["box"]), cls, gl)
            except Exception as e:
                stats["raised"] += 1
                res[s] = dict(repro=False, error=repr(e))
                continue
            rec = int(round(float(g["fh"]["value"])))
            ok = (r["pos"] == rec)
            stats["repro" if ok else "mismatch"] += 1
            d = r.get("detail") or {}
            nf = d.get("note_first") or {}
            res[s] = dict(repro=bool(ok), replay_pos=r["pos"], rungs=[float(y) for y in cap.get("rungs", [])],
                          box_used=[float(v) for v in r["box_used"]] if r.get("box_used") else None,
                          lines=[float(y) for y in (r.get("lines_used") or [])],
                          edge_y=d.get("edge_y"), line_y=nf.get("line_y"), kind=nf.get("kind"), how=nf.get("how"),
                          k=nf.get("k"), between=nf.get("between"), seen=nf.get("seen_on_flanks"))
        print(doc, mode, "page", page, dict(stats), flush=True)
        rep.gray.pop(page, None)
    Path(out).write_text(json.dumps(dict(doc=doc, mode=mode, src=src, stats=dict(stats), heads=res)))
    print("wrote", out, dict(stats))


if __name__ == "__main__":
    main(*sys.argv[1:5])
