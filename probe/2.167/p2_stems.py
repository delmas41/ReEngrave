"""2.167 probe 2 (PART 1c): for a seeded random sample of Litolff `head_stem: no_stem` heads that are KEPT (not refused as a
non-note, not a copy owned by another staff, not a whole-rest ink), where is the stem?

Re-uses 2.161's proven machinery (benchmarks/omr-head-fill-2026-09/probe/stems_2_161.py): the page is re-cut exactly as
production cuts it (prepare_pages), the SHIPPED line_detection.detect_lines is re-run on the head's cell with the record's own
detector boxes, collecting every vertical run with the filter that refused it. CONTROL: the re-run's accepted stems equal the
record's Q.STEM rows of that cell, box for box.

usage: python3 probe/2.167/p2_stems.py RECORD ROWS.jsonl OUT.json [N=40] [SEED=167]
"""
import collections
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.pipeline import prepare_pages          # noqa: E402
from tools.omr.line_detection import detect_lines, staged_stem_finder, _binary_ink   # noqa: E402
from tools.omr.staged import gather as G                     # noqa: E402
from tools.omr.staged.geometry import stem_touches_head      # noqa: E402
from tools.omr.staged.record_io import load_record           # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
record_path, rows_path, out_path = sys.argv[1:4]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 40
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 167

rows = [json.loads(l) for l in open(rows_path)]
A = [r for r in rows if r["head_stem"] and r["head_stem"][1] == "no_stem"
     and not r["fate"].startswith("not_a_notehead")
     and r["fate"] not in ("owned_by_another_staff", "ink_is_a_whole_rest")]
print("stratum A (kept no_stem heads):", len(A), flush=True)
rng = random.Random(SEED)
sample = rng.sample(A, N)
by_page = collections.defaultdict(list)
for r in sample:
    by_page[int(r["sub"].split("/")[1])].append(r)
cells_wanted = {"cell/" + r["sub"][6:].rsplit("/", 1)[0] for r in sample}

d = load_record(record_path)
obs = d["record"]["observations"]
idx = collections.defaultdict(lambda: collections.defaultdict(list))
for o in obs:
    q = o["quantity"]
    if q not in ("glyph_box", "stem", "cell_box", "cell_staff_space", "notehead_ink"):
        continue
    sub = o["subject"]
    ck = sub if sub.startswith("cell/") else ("cell/" + sub[6:].rsplit("/", 1)[0])
    if ck in cells_wanted:
        idx[ck][q].append(o)
del d, obs


def longest_vertical_run(ink, x0, x1, y0, y1):
    H, Wd = ink.shape
    x0, x1, y0, y1 = max(0, int(x0)), min(Wd, int(x1)), max(0, int(y0)), min(H, int(y1))
    best = (0, None, None)
    for x in range(x0, x1):
        col = ink[y0:y1, x] > 0
        run = 0
        for k, v in enumerate(col):
            run = run + 1 if v else 0
            if run > best[0]:
                best = (run, x, y0 + k - run + 1)
    return best


res, ctl = {}, collections.Counter()
for pg in sorted(by_page):
    (pws, cells), = prepare_pages(PDF, [pg])
    for r in by_page[pg]:
        s = r["sub"]
        ck = "cell/" + s[6:].rsplit("/", 1)[0]
        cr = idx[ck]
        cb = cr["cell_box"][0]["value"]
        cand = [c for c in cells if c.bbox_page_px and max(abs(a - b) for a, b in zip(c.bbox_page_px, cb)) < 2.0]
        if len(cand) != 1:
            res[s] = {"error": "cell match %d" % len(cand)}
            continue
        c = cand[0]
        sp = float(cr["cell_staff_space"][0]["value"])
        dets = []
        for o in sorted(cr["glyph_box"], key=lambda o: int(o["subject"].rsplit("/", 1)[1])):
            name, x, y, w, hh = o["value"]
            dets.append(SimpleNamespace(smufl_name=name, x_canonical=x, y_canonical=y, width_canonical=w,
                                        height_canonical=hh, x_center=x + w / 2.0, y_center=y + hh / 2.0))
        sub = SimpleNamespace(to_key=lambda ck=ck: ck)
        nh = G._notehead_boxes_for_cell({ck: dets}, sub, c)
        mk = G._owner_marks_for_cell({ck: dets}, sub)
        runs = []
        found = detect_lines(c, candidates_out=runs, noteheads=nh, rescue_tall_beams=True, marks=mk,
                             stem_finder=staged_stem_finder())
        got = sorted((q.x_canonical, q.y_canonical, q.width_canonical, q.height_canonical) for q in found["stems"])
        want = sorted(tuple(o["value"]) for o in cr["stem"])
        ok = got == want
        ctl["cell_agree" if ok else "cell_differ"] += 1
        gb = next(o for o in cr["glyph_box"] if o["subject"] == s)
        name, x, y, w, hh = gb["value"]
        hb = (x, y, w, hh)
        near = []
        for v in want:
            sx, sy, sw, sh = v
            dx = max(0.0, sx - (x + w), x - (sx + sw))
            dy = max(0.0, sy - (y + hh), y - (sy + sh))
            near.append(dict(box=v, dx_sp=round(dx / sp, 3), dy_sp=round(dy / sp, 3),
                             side="right" if sx + sw / 2.0 > x + w / 2.0 else "left",
                             len_sp=round(sh / sp, 2), touches=stem_touches_head(v, hb)))
        near.sort(key=lambda n: n["dx_sp"] + n["dy_sp"])
        ref = []
        for q in runs:
            dx = max(0.0, q.x - (x + w), x - (q.x + q.w))
            dy = max(0.0, q.y - (y + hh), y - (q.y + q.h))
            if dx <= 1.0 * sp and dy <= 1.0 * sp:
                ref.append(dict(box=[q.x, q.y, q.w, q.h], outcome=q.outcome, dx_sp=round(dx / sp, 3),
                                dy_sp=round(dy / sp, 3), h_sp=round(q.h / sp, 2), w_sp=round(q.w / sp, 2)))
        ref.sort(key=lambda n: n["dx_sp"] + n["dy_sp"])
        ink_e = _binary_ink(c.image_no_staff) if c.image_no_staff is not None else None
        ink_r = _binary_ink(c.image)
        raw = {}
        for lab, ink in (("erased", ink_e), ("original", ink_r)):
            if ink is None:
                continue
            for sd, (a, b) in (("left", (x - 0.4 * sp, x + 0.35 * w)), ("right", (x + 0.65 * w, x + w + 0.4 * sp))):
                run, rx, ry = longest_vertical_run(ink, a, b, y - 4.0 * sp, y + hh + 4.0 * sp)
                raw["%s_%s" % (lab, sd)] = dict(len_sp=round(run / sp, 2), x=rx, y=ry)
        res[s] = dict(page=pg, cls=name, box=hb, sp=sp, w_sp=round(w / sp, 2), h_sp=round(hh / sp, 2),
                      fate=r["fate"], cell_control=ok, stems_near=near[:3], refused_near=ref[:5], raw_runs=raw,
                      page_bbox=r["bbox"], cell_bbox=list(c.bbox_page_px))
    print("p%d" % pg, len(by_page[pg]), dict(ctl), flush=True)
    json.dump(res, open(out_path, "w"), indent=0)
print("control", dict(ctl))
json.dump(res, open(out_path, "w"), indent=0)
