"""ROADMAP 2.155 continue-a-level -- WHICH of Sean's 40 answered tiles' cells does the new beam rule change? No page gather.

For each tile cell: the cell prepared as the gather prepares it (`pipeline.prepare_pages`, no detector), heads/marks = the tightened
record's own boxes (t2_{doc}_tight_def), `detect_lines` at the CURRENT code with the flag's stem-finder set. Its CV stems/strokes are
compared with the stored CV rows of (a) the tightened record (t2_*_tight_def: guard "never anchor") and (b) the first-arm record
(tiles_*_edge: no guards). Equal to (a): the tile's reading is the tightened record's. Equal to (b): the first arm's GATHER rows are
the new rule's, so its readings stand in. Neither: printed, needs a replay. CONTROL: on every cell the code with the flag OFF must
reproduce the base record's stored CV rows (tiles_{doc}_base).
usage: cells_2_155c.py OUT.json"""
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-missing-notes-2026-09/probe")
sys.path.insert(0, "benchmarks/omr-beam-confirm-2026-10/probe")
from score_2_155 import load  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
D = "out/2.155/"
tiles = [("2.155", t["n"], t["doc"], t["glyph"]) for t in json.load(open("out/print/2.155-review/answers.json"))["tiles"]]
tiles += [("2.155b", t["n"], t["doc"], t["glyph"]) for t in json.load(open("out/print/2.155b-review/answers.json"))["tiles"]]
recs = {(d, a): load(D + p.format(d=d) + ".record.json") for d in PDFS
        for a, p in (("tight", "t2_{d}_tight_def"), ("first", "tiles_{d}_edge"), ("base", "tiles_{d}_base"))}


def cv_rows(r, cell):
    st = {tuple(o["value"]) for o in r["observations"] if o["subject"] == cell and o["quantity"] == "stem" and o["reader"] == "cv_lines"}
    bm = {tuple(o["value"]) for o in r["observations"] if o["subject"] == cell and o["quantity"] == "beam_stroke"
          and o["reader"] == "cv_lines"}
    return st, bm


box = lambda d: (int(d.x_canonical), int(d.y_canonical), int(d.width_canonical), int(d.height_canonical))  # noqa: E731
OFF, ON = LD.STEM_FINDER_STAGED_DEFAULT, LD.STEM_FINDER_STAGED_DEFAULT | {"edge_head"}
prepared, out = {}, []
for gal, n, doc, g in tiles:
    p = g.split("/")
    cell = "cell/" + "/".join(p[1:5])
    rt = recs[(doc, "tight")]
    cb = next((o["value"] for o in rt["observations"] if o["subject"] == cell and o["quantity"] == "cell_box"), None)
    if cb is None:
        out.append(dict(gallery=gal, n=n, glyph=g, status="cell not in record"))
        continue
    pg = int(p[1])
    if (doc, pg) not in prepared:
        (pws, cells), = prepare_pages(PDFS[doc], [pg])
        prepared[(doc, pg)] = {tuple(float(v) for v in c.bbox_page_px): c for c in cells}
    c = prepared[(doc, pg)][tuple(float(v) for v in cb)]
    sub = R.cell(*(int(v) for v in p[1:5]))
    rows = sorted((int(o["subject"].split("/")[5]), o["value"]) for o in rt["observations"]
                  if o["quantity"] == "glyph_box" and o["subject"].startswith(cell.replace("cell", "glyph") + "/"))
    dets = [SimpleNamespace(smufl_name=v[0], x_canonical=v[1], y_canonical=v[2], width_canonical=v[3], height_canonical=v[4],
                            x_center=v[1] + v[3] / 2.0, y_center=v[2] + v[4] / 2.0) for _i, v in rows]
    detmap = {sub.to_key(): dets}
    kw = dict(noteheads=G._notehead_boxes_for_cell(detmap, sub, c, log=None), rescue_tall_beams=True,
              marks=G._owner_marks_for_cell(detmap, sub))
    off, on = LD.detect_lines(c, stem_finder=OFF, **kw), LD.detect_lines(c, stem_finder=ON, **kw)
    now = ({box(d) for d in on["stems"]}, {box(d) for d in on["beams"]})
    ctl = cv_rows(recs[(doc, "base")], cell) == ({box(d) for d in off["stems"]}, {box(d) for d in off["beams"]})
    st = "= tight" if now == cv_rows(rt, cell) else ("= first" if now == cv_rows(recs[(doc, "first")], cell) else "NEW")
    out.append(dict(gallery=gal, n=n, doc=doc, glyph=g, cell=cell, status=st, off_faithful=ctl,
                    beams_now=sorted(now[1]), beams_tight=sorted(cv_rows(rt, cell)[1])))
    print(gal, n, doc, g, st, "off faithful" if ctl else "OFF DIFFERS", "" if st == "= tight" else sorted(now[1]), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
