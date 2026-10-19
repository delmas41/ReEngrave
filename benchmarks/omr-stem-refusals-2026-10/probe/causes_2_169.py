"""ROADMAP 2.169 -- for EVERY detected notehead whose stored `head_stem` is no_stem (not a sample): which refused vertical run stands
beside it (the finder's own `candidates_out`, first filter that refused it), and does each arm (OFF / NEW pair_head_end / GATE)
connect it. Whole movement, no re-gather. Same cell preparation + control as reach_2_169.py.

A run "beside" a head: horizontal gap <= 0.6 space and vertical gap <= 0.25 space from the DETECTOR's glyph box, height >= 1.5
spaces, and its columns on the head's right half or left half (a stem stands at a side). The nearest such run (by gap) is the
head's cause. Heads with no such run: "no_run_beside".
usage: causes_2_169.py DOC ROWS.json OUT.json [pages]
"""
import dataclasses
import json
import os
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

sys.path.insert(0, ".")
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.geometry import stem_touches_head  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
DOC, ROWS, OUT = sys.argv[1:4]
ONLY = None if len(sys.argv) < 5 or sys.argv[4] == "all" else {int(x) for x in sys.argv[4].split(",")}
OFF = LD.STEM_FINDER_STAGED_DEFAULT | {"edge_head"}
NEW = OFF | {"pair_head_end"}

d = json.load(open(ROWS))
cell_box = {k: tuple(v) for k, v in d["cell_box"].items()}
glyphs = defaultdict(list)
for sub, v in d["glyph"].items():
    p = sub.split("/")
    glyphs["cell/" + "/".join(p[1:5])].append((int(p[5]), v))
stems = {k: {tuple(int(x) for x in v) for v in vs} for k, vs in d["stems"].items()}
head_stem = d["head_stem"]
notehead = set(d["notehead"])
box = lambda s: (int(s.x_canonical), int(s.y_canonical), int(s.width_canonical), int(s.height_canonical))  # noqa: E731
pages = sorted({int(c.split("/")[1]) for c in cell_box})
if ONLY is not None:
    pages = [p for p in pages if p in ONLY]
tot = Counter()
rows = []
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
        gl = sorted(glyphs.get(key, []))
        want = [(gi, v) for gi, v in gl
                if "glyph/%s/%s/%s/%s/%d" % (p, s, st, m, gi) in notehead
                and head_stem.get("glyph/%s/%s/%s/%s/%d" % (p, s, st, m, gi), [None, None])[1] == "no_stem"]
        tot["cells"] += 1
        if not want:
            continue
        dets = [SimpleNamespace(smufl_name=v[0], x_canonical=v[1], y_canonical=v[2], width_canonical=v[3],
                                height_canonical=v[4], x_center=v[1] + v[3] / 2.0, y_center=v[2] + v[4] / 2.0) for _g, v in gl]
        detmap = {sub.to_key(): dets}
        heads = G._notehead_boxes_for_cell(detmap, sub, c, log=None)
        marks = G._owner_marks_for_cell(detmap, sub)
        runs = []
        a = LD.detect_lines(c, candidates_out=runs, noteheads=heads, rescue_tall_beams=True, marks=marks, stem_finder=OFF)
        n = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, marks=marks, stem_finder=NEW)
        os.environ["OMR_STEM_NOTEHEAD_GATE"] = "1"
        try:
            g = LD.detect_lines(c, noteheads=heads, rescue_tall_beams=True, marks=marks, stem_finder=OFF)
        finally:
            del os.environ["OMR_STEM_NOTEHEAD_GATE"]
        if {box(x) for x in a["stems"]} != stems.get(key, set()):
            tot["cell_off_differs_from_record"] += 1
            continue
        tot["cells_faithful"] += 1
        sp = float(LD._staff_line_spacing(c))
        for gi, v in want:
            hb = tuple(v[1:5])
            x, y, w, h = hb
            tot["no_stem_heads"] += 1
            best = None
            for q in runs:
                if q.h < 1.5 * sp:
                    continue
                dx = max(0.0, q.x - (x + w), x - (q.x + q.w))
                dy = max(0.0, q.y - (y + h), y - (q.y + q.h))
                if dx <= 0.6 * sp and dy <= 0.25 * sp:
                    if best is None or dx + dy < best[0]:
                        best = (dx + dy, q)
            cause = best[1].outcome if best else "no_run_beside"
            tot["cause:" + cause] += 1
            gone_n = any(stem_touches_head(box(q), hb) for q in n["stems"])
            gone_g = any(stem_touches_head(box(q), hb) for q in g["stems"])
            was = any(stem_touches_head(box(q), hb) for q in a["stems"])
            if was:
                tot["off_already_touches"] += 1
            if gone_n and not was:
                tot["NEW_connects"] += 1
                tot["NEW_connects_cause:" + cause] += 1
            if gone_g and not was:
                tot["GATE_connects"] += 1
                tot["GATE_connects_cause:" + cause] += 1
            rows.append(dict(sub="glyph/%s/%s/%s/%s/%d" % (p, s, st, m, gi), cls=v[0], box=list(hb), cause=cause,
                             cause_run=(dataclasses.asdict(best[1]) if best else None), off_touch=was, new_touch=gone_n, gate_touch=gone_g,
                             sp=sp, page_bbox=list(bb), upscale=float(c.upscale_factor)))
    print("page", pg, dict(tot), flush=True)
    json.dump(dict(totals=dict(tot), rows=rows), open(OUT, "w"), indent=0, default=str)
json.dump(dict(totals=dict(tot), rows=rows), open(OUT, "w"), indent=0, default=str)
print("DONE", dict(tot))
