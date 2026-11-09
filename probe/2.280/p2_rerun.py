"""2.280 probe 2 (STAGED GATHER, read-only): for kept heads with no touching stem row, re-run the SHIPPED stem finder on the head's cell
and record why no stem was output or connected (2.167 p2_stems.py method), plus whether the PAGE strokes / head_stem_reach rows already
hold a vertical stroke beside the head (the 'computed and never read' bucket).

Population (from p1_population.py rows, 20261104-night slices): kept heads, no stem touches the box, duration NARROWED (stratum A, all of them)
and duration DECIDED (stratum B, seeded sample N_B) -- copies owned by another staff are excluded (their stem lives in the other cell).
CONTROL: the re-run cell's accepted stems equal the slice's Q.STEM rows of that cell, box for box.

usage: python3 probe/2.280/p2_rerun.py litolff|brahms POP.json OUT.json [N_B=30] [SEED=280]
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

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SL = LIB + "_shared-records/lane-report-slices-20261104-night/"
plate, pop_path, out_path = sys.argv[1:4]
NB = int(sys.argv[4]) if len(sys.argv) > 4 else 30
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 280
PDF = PDFS[plate]

pop = json.load(open(pop_path))
A = [r for r in pop if r["n_stem"] == 0 and r["dur"] == "narrowed"]
B = [r for r in pop if r["n_stem"] == 0 and r["dur"] == "decided"]
rng = random.Random(SEED)
B = rng.sample(B, min(NB, len(B)))
sample = [dict(r, stratum="A") for r in A] + [dict(r, stratum="B") for r in B]
print(plate, "A", len(A), "B", len(B), flush=True)
by_page = collections.defaultdict(list)
for r in sample:
    by_page[r["page"]].append(r)
cells_wanted = {r["cell"] for r in sample}

idx = collections.defaultdict(lambda: collections.defaultdict(list))
pstrokes = collections.defaultdict(list)
for l in open(SL + plate + "/observations.jsonl"):
    o = json.loads(l)
    q = o["quantity"]
    if q == "page_stroke":
        pstrokes[int(o["subject"].split("/")[1])].append(o)
        continue
    if q not in ("glyph_box", "stem", "cell_box", "cell_staff_space"):
        continue
    sub = o["subject"]
    ck = sub if sub.startswith("cell/") else ("cell/" + sub[6:].rsplit("/", 1)[0])
    if ck in cells_wanted:
        idx[ck][q].append(o)


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
        ck = r["cell"]
        cr = idx[ck]
        cb = cr["cell_box"][0]["value"]
        cand = [c for c in cells if c.bbox_page_px and max(abs(a - b) for a, b in zip(c.bbox_page_px, cb)) < 2.0]
        if len(cand) != 1:
            res[s] = {"error": "cell match %d" % len(cand), "stratum": r["stratum"]}
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
        got = sorted((round(q.x_canonical), round(q.y_canonical), round(q.width_canonical), round(q.height_canonical)) for q in found["stems"])
        want = sorted(tuple(round(v) for v in o["value"]) for o in cr["stem"])
        ok = got == want
        ctl["cell_agree" if ok else "cell_differ"] += 1
        gb = next(o for o in cr["glyph_box"] if o["subject"] == s)
        name, x, y, w, hh = gb["value"]
        hb = (x, y, w, hh)
        near = []
        for o in cr["stem"]:
            v = o["value"]
            sx, sy, sw, sh = v
            dx = max(0.0, sx - (x + w), x - (sx + sw))
            dy = max(0.0, sy - (y + hh), y - (sy + sh))
            near.append(dict(box=v, dx_sp=round(dx / sp, 3), dy_sp=round(dy / sp, 3), len_sp=round(sh / sp, 2),
                             side="right" if sx + sw / 2.0 > x + w / 2.0 else "left", touches=stem_touches_head(v, hb)))
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
        # PAGE strokes: any page stroke beside the head (page frame), any kind
        px0, py0, px1, py1 = r["page_box"]
        spp = float(r["reach"]["sp"]) if r.get("reach") and r["reach"].get("sp") else sp
        pst = []
        for o in pstrokes[pg]:
            bx0, by0, bx1, by1 = o["detail"]["bbox_page_px"]
            if bx1 < px0 - 0.5 * spp or bx0 > px1 + 0.5 * spp or by1 < py0 - 4 * spp or by0 > py1 + 4 * spp:
                continue
            ext_up = max(0.0, (py0 - by0) / spp)
            ext_dn = max(0.0, (by1 - py1) / spp)
            pst.append(dict(kind=o["value"], len_sp=o["detail"].get("length_spaces"), thick_sp=o["detail"].get("thickness_spaces"),
                            box=[bx0, by0, bx1, by1], ext_up_sp=round(ext_up, 2), ext_dn_sp=round(ext_dn, 2),
                            dx_sp=round(max(0.0, bx0 - px1, px0 - bx1) / spp, 2), ord=o["detail"].get("ordinal")))
        res[s] = dict(page=pg, stratum=r["stratum"], cls=name, box=hb, sp=sp, w_sp=round(w / sp, 2), h_sp=round(hh / sp, 2),
                      dur=r["dur"], dur_reason=r["dur_reason"], cell_control=ok, stems_near=near[:3], refused_near=ref[:6],
                      raw_runs=raw, page_box=r["page_box"], cell_bbox=list(c.bbox_page_px), page_strokes=pst, reach=r.get("reach"))
    print("p%d" % pg, len(by_page[pg]), dict(ctl), flush=True)
    json.dump(res, open(out_path, "w"), indent=0)
print("control", dict(ctl))
json.dump(res, open(out_path, "w"), indent=0)
