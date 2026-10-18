"""ROADMAP 2.161 -- PROBE (no detector, no gather). For every real-note head 2.159 left `head_fill_from_ink` (Litolff 47,
Brahms 15: not refused as a notehead / rest), why it has no stem touching its detector box, or why that box is not one
head's size.

STEM: the page is re-cut into cells exactly as production does (`pipeline.prepare_pages`: render 600 dpi, staves, cells,
staff-line removal -- no detector), the head's cell is matched to the record by its page box, and the SHIPPED
`line_detection.detect_lines` is re-run on it with the record's own detector boxes (from `Q.GLYPH_BOX`) as heads and marks,
`candidates_out` collecting every vertical run the opening produced with the first filter that refused it.
CONTROL: the re-run's accepted stems must equal the record's `Q.STEM` rows of that cell (box for box).
Then per head: the nearest accepted stem (and the gap to the box: side, dx, dy), the nearest refused run beside the head and
its refusal, and -- if no run at all -- the longest vertical ink run in the columns just left/right of the head on the
ERASED cell raster and on the unerased one (a stem cut by line removal, or thinner/shorter than the kernel).

BOX: for a not-head-sized box, which other detector boxes overlap it, and 2.115's part-boxed record (`part_boxed`).
usage: stems_2_161.py SLICEDIR W161DIR OUT.json [doc]"""
import collections
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.line_detection import detect_lines, staged_stem_finder, _binary_ink  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.geometry import stem_touches_head  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SD, W, OUT = sys.argv[1:4]
DOCS = sys.argv[4:] or ["litolff", "brahms"]
C = json.load(open(os.path.join(W, "causes.json")))


def page_rows(doc, pg, cells_wanted):
    """glyph_box / stem / cell_box / cell_staff_space / notehead_ink rows of the wanted cells."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(os.path.join(SD, doc, "p%02d.observations.jsonl" % pg)):
        i = line.find('"subject": "')
        sub = line[i + 12:line.find('"', i + 12)]
        cell = sub if sub.startswith("cell/") else ("cell/" + sub[6:].rsplit("/", 1)[0] if sub.startswith("glyph/") else None)
        if cell not in cells_wanted:
            continue
        o = json.loads(line)
        if o["quantity"] in ("glyph_box", "stem", "cell_box", "cell_staff_space", "notehead_ink", "notehead_recentre",
                             "head_line_cut"):
            out[cell][o["quantity"]].append(o)
    return out


def longest_vertical_run(ink, x0, x1, y0, y1):
    """Longest run of ink pixels down any one column in [x0,x1) over rows [y0,y1) (ink: 1 = ink)."""
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


res = {}
for doc in DOCS:
    R = set(json.load(open(os.path.join(W, "refused_%s.json" % doc)))["refused"])
    heads = [r for r in C[doc]["rows"] if r["subject"] not in R]
    by_page = collections.defaultdict(list)
    for h in heads:
        by_page[int(h["subject"].split("/")[1])].append(h)
    ctl = collections.Counter()
    for pg in sorted(by_page):
        hs = by_page[pg]
        cells_wanted = {"cell/" + h["subject"][6:].rsplit("/", 1)[0] for h in hs}
        rows = page_rows(doc, pg, cells_wanted)
        (pws, cells), = prepare_pages(PDFS[doc], [pg])
        for h in hs:
            s = h["subject"]
            ck = "cell/" + s[6:].rsplit("/", 1)[0]
            cr = rows[ck]
            cb = cr["cell_box"][0]["value"]
            cand = [c for c in cells if c.bbox_page_px and max(abs(a - b) for a, b in zip(c.bbox_page_px, cb)) < 2.0]
            if len(cand) != 1:
                res[s] = {"doc": doc, "error": "cell match %d" % len(cand)}
                continue
            c = cand[0]
            sp = float(cr["cell_staff_space"][0]["value"])
            dets, heads_c, marks = [], [], []
            gboxes = sorted(cr["glyph_box"], key=lambda o: int(o["subject"].rsplit("/", 1)[1]))
            for o in gboxes:
                name, x, y, w, hh = o["value"]
                dets.append(SimpleNamespace(smufl_name=name, x_canonical=x, y_canonical=y, width_canonical=w,
                                            height_canonical=hh, x_center=x + w / 2.0, y_center=y + hh / 2.0))
            dmap = {ck.replace("cell/", "cell/"): dets}
            sub = SimpleNamespace(to_key=lambda ck=ck: ck)
            nh = G._notehead_boxes_for_cell({ck: dets}, sub, c)
            mk = G._owner_marks_for_cell({ck: dets}, sub)
            runs = []
            found = detect_lines(c, candidates_out=runs, noteheads=nh, rescue_tall_beams=True, marks=mk,
                                 stem_finder=staged_stem_finder())
            got = sorted((d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical) for d in found["stems"])
            want = sorted(tuple(o["value"]) for o in cr["stem"])
            ok = got == want
            ctl["cell_agree" if ok else "cell_differ"] += 1
            gb = next(o for o in cr["glyph_box"] if o["subject"] == s)
            name, x, y, w, hh = gb["value"]
            hb = (x, y, w, hh)
            # stems: nearest accepted (record's) stem to the head box
            near = []
            for v in want:
                sx, sy, sw, sh = v
                dx = max(0.0, sx - (x + w), x - (sx + sw))       # horizontal gap, 0 = columns overlap
                dy = max(0.0, sy - (y + hh), y - (sy + sh))
                side = "right" if sx + sw / 2.0 > x + w / 2.0 else "left"
                near.append(dict(box=v, dx_sp=round(dx / sp, 3), dy_sp=round(dy / sp, 3), side=side,
                                 len_sp=round(sh / sp, 2), touches=stem_touches_head(v, hb),
                                 up=bool(sy + sh / 2.0 < y + hh / 2.0)))
            near.sort(key=lambda n: n["dx_sp"] + n["dy_sp"])
            # refused runs within 1.0 sp sideways and 1.0 sp vertically of the head box
            ref = []
            for r in runs:
                dx = max(0.0, r.x - (x + w), x - (r.x + r.w))
                dy = max(0.0, r.y - (y + hh), y - (r.y + r.h))
                if dx <= 1.0 * sp and dy <= 1.0 * sp:
                    ref.append(dict(box=[r.x, r.y, r.w, r.h], outcome=r.outcome, dx_sp=round(dx / sp, 3),
                                    dy_sp=round(dy / sp, 3), h_sp=round(r.h / sp, 2), w_sp=round(r.w / sp, 2),
                                    accepted_but_dropped=(r.outcome == "accepted"
                                                          and (r.x, r.y, r.w, r.h) not in {tuple(v) for v in want})))
            ref.sort(key=lambda n: n["dx_sp"] + n["dy_sp"])
            # raw ink runs beside the head (0.6 sp either side of the box, 4 sp up/down)
            ink_e = _binary_ink(c.image_no_staff) if c.image_no_staff is not None else None
            ink_r = _binary_ink(c.image)
            raw = {}
            for lab, ink in (("erased", ink_e), ("original", ink_r)):
                if ink is None:
                    continue
                for sd, (a, b) in (("left", (x - 0.4 * sp, x + 0.35 * w)), ("right", (x + 0.65 * w, x + w + 0.4 * sp))):
                    run, rx, ry = longest_vertical_run(ink, a, b, y - 4.0 * sp, y + hh + 4.0 * sp)
                    raw["%s_%s" % (lab, sd)] = dict(len_sp=round(run / sp, 2), x=rx, y=ry)
            # box: overlapping other detector boxes
            over = []
            for o in cr["glyph_box"]:
                if o["subject"] == s:
                    continue
                n2, x2, y2, w2, h2 = o["value"]
                ix = min(x + w, x2 + w2) - max(x, x2)
                iy = min(y + hh, y2 + h2) - max(y, y2)
                if ix > 0 and iy > 0:
                    over.append(dict(name=n2, share_of_head=round(ix * iy / float(w * hh), 3), glyph=o["subject"]))
            ni = next((o for o in cr["notehead_ink"] if o["subject"] == s), None)
            nd = (ni or {}).get("detail") or {}
            res[s] = dict(doc=doc, page=pg, name=name, box=hb, sp=sp, w_sp=round(w / sp, 2), h_sp=round(hh / sp, 2),
                          cause_2159=h["cause"], stems_attached=h["stems"], cell_control=ok,
                          stems_near=near[:3], refused_near=ref[:4], raw_runs=raw, overlaps=over,
                          box_source=nd.get("box_source"), part_boxed=nd.get("part_boxed"),
                          recentre=[o["value"] for o in cr["notehead_recentre"] if o["subject"] == s],
                          line_cut=[o["value"] for o in cr["head_line_cut"] if o["subject"] == s],
                          crops=h.get("crops"))
        print(doc, "p%02d" % pg, len(hs), dict(ctl), flush=True)
        json.dump(res, open(OUT, "w"), indent=0)
    print(doc, "control", dict(ctl))
json.dump(res, open(OUT, "w"), indent=0)
