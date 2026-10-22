"""ROADMAP 2.169 -- REACH of the stem finder's pair rule exemptions over a whole 20261016-night record, no re-gather.

Per cell of the record (rows json from extract_rows.py): the cell is prepared as the gather prepares it (`prepare_pages`, matched to
the record's `cell_box` by page bbox), detector boxes = the record's own `glyph_box` rows (heads -> `gather._notehead_boxes_for_cell`,
marks -> `_owner_marks_for_cell`, log=None), and `detect_lines` runs three times:
  OFF   the staged default (the shipped finder)
  GATE  the shipped finder + the 2020-09 `OMR_STEM_NOTEHEAD_GATE` (a stroke that overlaps ANY head box is never pair-deleted)
  NEW   the shipped finder + `pair_head_end` (a stroke with an END in a head's rows+columns, not on an accidental, is never
        pair-deleted as the subject)
CONTROL (faithful): OFF stems vs the record's stored `Q.STEM` rows, per cell (boxes equal). A cell that differs is counted and skipped.
For every stroke an arm ADDS over OFF: the heads (glyph ids) it touches by the shipped contact test, those heads' stored `head_stem`
outcome, and whether it lies on an accidental / key box.
usage: reach_2_169.py DOC ROWS.json OUT.json [pages=all|a,b,c]
"""
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
added = []
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
        sa, sn, sg = ({box(x) for x in r["stems"]} for r in (a, n, g))
        tot["cells"] += 1
        if sa != stems.get(key, set()):
            tot["cell_off_differs_from_record"] += 1
            continue
        tot["cells_faithful"] += 1
        if (sa - sn) or (sa - sg):
            tot["ERROR_arm_lost_a_stem"] += 1
        # heads with their stored verdict, glyph boxes (contact test frame)
        hd = [(gi, v) for gi, v in gl if "%s/%s/%s/%s/%d" % (p, s, st, m, gi) and
              "glyph/%s/%s/%s/%s/%d" % (p, s, st, m, gi) in notehead]
        for arm, sx in (("NEW", sn), ("GATE", sg)):
            new = sorted(sx - sa)
            if new:
                tot[arm + "_cells_changed"] += 1
            for bx in new:
                tot[arm + "_strokes_added"] += 1
                ds = SimpleNamespace(x_canonical=bx[0], y_canonical=bx[1], width_canonical=bx[2], height_canonical=bx[3])
                on_acc = any(k in ("accidental", "key") and LD._inside_share(ds, b) >= 0.5 for k, b in marks)
                tot[arm + "_added_on_accidental" if on_acc else arm + "_added_not_on_accidental"] += 1
                touched = []
                for gi, v in hd:
                    if stem_touches_head(bx, tuple(v[1:5])):
                        sid = "glyph/%s/%s/%s/%s/%d" % (p, s, st, m, gi)
                        touched.append((sid, head_stem.get(sid, [None, None])))
                tot[arm + "_added_touches_a_head" if touched else arm + "_added_touches_no_head"] += 1
                for sid, hv in touched:
                    tot[arm + "_head_was_" + str(hv[0]) + ":" + str(hv[1])] += 1
                added.append(dict(arm=arm, cell=key, page_bbox=list(bb), stem=list(bx), on_accidental=on_acc,
                                  heads=[t[0] for t in touched], head_stem=[t[1] for t in touched],
                                  upscale=float(c.upscale_factor)))
    print("page", pg, dict(tot), flush=True)
    json.dump(dict(totals=dict(tot), added=added), open(OUT, "w"), indent=0)
json.dump(dict(totals=dict(tot), added=added), open(OUT, "w"), indent=0)
print("DONE", dict(tot))
