"""lane-farhead-note-first (2026-10-05): OUT-OF-SAMPLE run of the note-first far-head reader on the far heads of an
existing overnight record (read only; NO gather -- the page is re-rendered in the gather's own frame, the boxes,
staff lines and geometry positions come off the record). Reports, per page range: decided / abstained by reason,
agreement with the recorded run-2 reader and with geometry. Writes the per-head results for the sample sheet.

  python3 farhead_note_first_oos.py litolff 4 16 out.json
  python3 farhead_note_first_oos.py brahms 2 26 out.json
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

RECORDS = {
    "litolff": ("beethoven5-litolff", "beethoven5-litolff-mvt1-whole-20261004-farhead-all.record.json"),
    "brahms": ("brahms1-breitkopf", "brahms1-breitkopf-mvt1-whole-20261004-farhead-all.record.json"),
}
SHARED = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")


def page_inputs(rec, page, glyph_rows):
    heads, staff_lines, page_boxes = [], {}, []
    for sub, cls, box, score in glyph_rows:
        page_boxes.append((sub, cls, box))
        if not cls.startswith("notehead"):
            continue
        sk = "staff/" + "/".join(sub.split("/")[1:4])
        lr = rec.obs(Q.STAFF_LINES, sk)
        po = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        if not lr or not po:
            continue
        gl = [float(y) for y in lr[-1]["value"]]
        staff_lines[sk] = gl
        try:
            pos = int(round(float(po[-1]["value"])))
        except (TypeError, ValueError):
            continue
        heads.append(dict(subject=sub, box=box, pos=pos, cls=cls, score=score, global_lines=gl))
    return heads, staff_lines, page_boxes


def recorded_run2(rec, sub):
    rows = rec.obs(Q.FAR_HEAD_LEDGER_POSITION, sub)
    return int(rows[-1]["value"]) if rows else None


def main(which, p0, p1, out):
    doc, fname = RECORDS[which]
    cfg = ts.DOCS[doc]
    print("loading", fname, flush=True)
    rec = EXP.Record(load_record(SHARED / fname))
    glyphs = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            glyphs[int(o["subject"].split("/")[1])].append(
                (o["subject"], o["value"][0], tuple(float(v) for v in pb),
                 float(o.get("score") if o.get("score") is not None else 1.0)))
    ctxs, pool, results = {}, [], []
    for page in range(p0, p1 + 1):
        if page not in glyphs:
            continue
        heads, staff_lines, page_boxes = page_inputs(rec, page, glyphs[page])
        far = [h for h in heads if lg.far_head_needs_ledger_read(h["pos"])]
        if not far:
            continue
        pi = render_page_matching_gather(cfg["pdf"], page, 600)
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
        pool.extend(ctx.samples)
        ctxs[page] = (ctx, far)
        print("page", page, "heads", len(heads), "far", len(far), "shape", ctx.shape_source, flush=True)
    pooled = FH.pooled_shape(pool)
    for page, (ctx, far) in ctxs.items():
        if ctx.shape is None and pooled is not None:
            ctx.adopt(pooled, f"document pool n={len(pool)}")
        for h in far:
            sk = "staff/" + "/".join(h["subject"].split("/")[1:4])
            row = dict(subject=h["subject"], page=page, geometry=h["pos"], box=h["box"], cls=h["cls"],
                       run2_recorded=recorded_run2(rec, h["subject"]))
            for name, on in (("old", False), ("new", True)):
                FH.READER_KEYWORDS["note_first"] = on
                r = ctx.read(h["subject"], h["box"], h["cls"], h["global_lines"])
                d = r.get("detail", {}) if on else {}
                nf = d.get("note_first") or {}
                row[name] = dict(pos=r["pos"], reason=r["reason"], box_used=r.get("box_used"),
                                 lines=r.get("lines_used"), edge_y=d.get("edge_y"),
                                 line_y=nf.get("line_y"), kind=nf.get("kind"), how=nf.get("how"),
                                 k=nf.get("k"), refused=nf.get("refused_rungs"), between=nf.get("between"), gaps=nf.get("gaps"), seen=nf.get("seen_on_flanks"))
            results.append(row)
    FH.READER_KEYWORDS["note_first"] = True
    Path(out).write_text(json.dumps(results))
    report(which, results)


def reason_key(r):
    return (r.split(" (")[0]).split(" -- ")[0][:60]


def report(which, results):
    n = len(results)
    dec = [r for r in results if r["new"]["pos"] is not None]
    ab = collections.Counter(reason_key(r["new"]["reason"]) for r in results if r["new"]["pos"] is None)
    print(f"== {which}: far heads {n}; note-first decides {len(dec)}, abstains {n - len(dec)}")
    for k, v in ab.most_common():
        print(f"   abstain {v:4d}  {k}")
    old_dec = [r for r in results if r["old"]["pos"] is not None]
    print(f"   old reader (this tree) decides {len(old_dec)}, abstains {n - len(old_dec)}")
    both = [r for r in dec if r["old"]["pos"] is not None]
    print(f"   decided by both: {len(both)}; agree with old: {sum(r['new']['pos'] == r['old']['pos'] for r in both)}")
    rec2 = [r for r in dec if r["run2_recorded"] is not None]
    print(f"   vs the recorded overnight run-2 reader: {len(rec2)} both decided, agree "
          f"{sum(r['new']['pos'] == r['run2_recorded'] for r in rec2)}")
    print(f"   vs geometry: new agrees {sum(r['new']['pos'] == r['geometry'] for r in dec)} / {len(dec)}; "
          f"old agrees {sum(r['old']['pos'] == r['geometry'] for r in old_dec)} / {len(old_dec)}")
    ho = collections.Counter(r["new"]["how"] for r in dec)
    print("   by what line decided it:", dict(ho))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2], json.loads(Path(sys.argv[3]).read_text()))
    else:
        main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
