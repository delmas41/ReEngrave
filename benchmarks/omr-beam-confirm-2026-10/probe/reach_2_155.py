"""ROADMAP 2.155 -- REACH of `OMR_STEM_AT_BAR_EDGE` over a whole 20261014-night record, without a re-gather.

For every cell of the record: the cell is prepared as the gather prepares it (`pipeline.prepare_pages`, matched to the record's
`cell_box` by its page bbox), the detector boxes are the record's own `glyph_box` rows (heads -> `gather._notehead_boxes_for_cell`,
marks -> `_owner_marks_for_cell`, log=None: no 2.39b re-centre), and `detect_lines` runs twice: the staged default (OFF) and the
default + `edge_head` (ON). Then `gather._observe_beam_stem_join` runs on the ON arm's stems x strokes into a scratch log.

CONTROL (faithful): OFF stems vs the record's stored `Q.STEM` rows, per cell (boxes equal). A cell that differs is counted and
skipped. Per rescued stem: the head(s) it ends in (glyph ids), the stored `head_stem` verdict of each (was it `no_stem`?), and the
ON-arm `Q.BEAM_STEM_JOIN` rows at that stem (joined / not joined / abstained, per end).
usage: reach_2_155.py DOC OUT.json      DOC in litolff | brahms
"""
import json
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
DOC, OUT = sys.argv[1:3]
OFF = LD.STEM_FINDER_STAGED_DEFAULT
ON = OFF | {"edge_head"}

cell_box, glyphs, stems, head_stem = {}, defaultdict(list), defaultdict(set), {}
with RC.lock():
    for o in RC.items(RC.RECORDS[DOC], "observations"):
        q = o["quantity"]
        if q == "cell_box":
            cell_box[o["subject"]] = tuple(o["value"])
        elif q == "glyph_box":
            p = o["subject"].split("/")
            glyphs["cell/" + "/".join(p[1:5])].append((int(p[5]), o["value"]))
        elif q == "stem" and o["reader"] == "cv_lines":
            stems[o["subject"]].add(tuple(int(v) for v in o["value"]))
    for v in RC.items(RC.RECORDS[DOC], "verdicts"):
        if v["quantity"] == "head_stem" and v["subject"] not in head_stem:
            head_stem[v["subject"]] = v["outcome"] + ":" + str(v.get("reason"))
print("record read: cells", len(cell_box), "head_stem", len(head_stem), flush=True)

pages = sorted({int(c.split("/")[1]) for c in cell_box})
tot = Counter()
rescued = []
for pg in pages:
    (pws, cells), = prepare_pages(PDFS[DOC], [pg])
    by_bb = {tuple(float(v) for v in c.bbox_page_px): c for c in cells}
    for key, bb in cell_box.items():
        if int(key.split("/")[1]) != pg:
            continue
        c = by_bb.get(tuple(float(v) for v in bb))
        if c is None:
            tot["cell_not_matched"] += 1
            continue
        _, p, s, st, m = key.split("/")
        sub = R.cell(int(p), int(s), int(st), int(m))
        dets = [SimpleNamespace(smufl_name=v[0], x_canonical=v[1], y_canonical=v[2], width_canonical=v[3],
                                height_canonical=v[4], x_center=v[1] + v[3] / 2.0, y_center=v[2] + v[4] / 2.0)
                for _gi, v in sorted(glyphs.get(key, []))]
        gids = [gi for gi, _v in sorted(glyphs.get(key, []))]
        detmap = {sub.to_key(): dets}
        heads = G._notehead_boxes_for_cell(detmap, sub, c, log=None)
        marks = G._owner_marks_for_cell(detmap, sub)
        a = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, marks=marks, stem_finder=OFF)
        b = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, marks=marks, stem_finder=ON)
        box = lambda d: (int(d.x_canonical), int(d.y_canonical), int(d.width_canonical), int(d.height_canonical))  # noqa: E731
        sa, sb = {box(d) for d in a["stems"]}, {box(d) for d in b["stems"]}
        tot["cells"] += 1
        if sa != stems.get(key, set()):
            tot["cell_off_differs_from_record"] += 1
            continue
        tot["cells_faithful"] += 1
        new = [d for d in b["stems"] if box(d) not in sa]
        if not new:
            continue
        tot["cells_with_rescue"] += 1
        tot["stems_rescued"] += len(new)
        if {box(d) for d in a["beams"]} != {box(d) for d in b["beams"]}:
            tot["cells_beam_strokes_changed"] += 1
        # head boxes in the same order as `heads` (only notehead-named dets carry one)
        head_gids = [gi for gi, d in zip(gids, dets) if "notehead" in str(d.smufl_name).lower()]
        lg = R.Log()
        sl = [(d, "stem%d" % i) for i, d in enumerate(new)]
        bl = [(d, "beam%d" % i) for i, d in enumerate(b["beams"])]
        space = LD._staff_line_spacing(c)
        G._observe_beam_stem_join(lg, sub, G.frame_cell(c.measure_index), c, sl, bl, space)
        js = lg.to_json()
        for i, d in enumerate(new):
            x, y, w, h = box(d)
            ends = [gid for gid, hb in zip(head_gids, heads)
                    if LD._run_ends_at_a_head(x, y, w, h, [hb], space, c.width)]
            rows = [r for r in js.get("observations", []) if (r.get("detail") or {}).get("stem_row_id") == "stem%d" % i]
            abst = [r for r in js.get("abstentions", []) if (r.get("detail") or {}).get("stem_row_id") == "stem%d" % i]
            joined = any(r["value"] is True for r in rows)
            kind = "joined" if joined else ("not_joined" if rows else ("no_stroke" if not b["beams"] else "abstained"))
            tot["rescued_" + kind] += 1
            hs = [head_stem.get("glyph/%s/%s/%s/%s/%d" % (p, s, st, m, g)) for g in ends]
            for hv in hs:
                tot["head_was_" + str(hv)] += 1
            rescued.append(dict(cell=key, page_bbox=list(bb), upscale=float(c.upscale_factor), stem=[x, y, w, h],
                                side="right" if x > c.width / 2 else "left", heads=["glyph/%s/%s/%s/%s/%d" % (p, s, st, m, g) for g in ends],
                                head_stem=hs, join=kind,
                                join_rows=[(r["detail"].get("end"), r["value"], r["detail"].get("beam_row_id")) for r in rows]))
    print("page", pg, dict(tot), flush=True)
json.dump(dict(totals=dict(tot), rescued=rescued), open(OUT, "w"), indent=0)
print("DONE", dict(tot))
