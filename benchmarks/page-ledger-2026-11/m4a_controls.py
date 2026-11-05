"""ROADMAP 2.260c M4a controls, read off ONE finished record (gather+adjudicate or `--through gather`, `OMR_PAGE_BEAMS=1`). Usage:

    python3 benchmarks/page-ledger-2026-11/m4a_controls.py REC.json PDF PLATE OUTDIR [N_CROPS]

Prints (1) parity of the page beam strokes against A's (`gather_cv_lines`) slabs by PLACE, with the page side shifted 6 and 12 px as the control that
must fail; (2) the beams on a staff line, page thickness against C's (`Q.BEAM_STROKE_INK`); (3) the beams A filed cut by a cell edge and what the page
holds there; (4) one filing per page stroke; (5) the stem tips where the page's level count differs from D's (`Q.BEAM_STEM_LEVELS`). It then cuts up to
N_CROPS crops (default 12) of places where the page reading and the old reads disagree into `OUTDIR/tiles/`, with `OUTDIR/key_PLATE.json` BESIDE the
tile folder. A crop is the page render around the beam and its end stems with a thin green box over the beam and nothing else drawn. Reads rows only
(plus the page render for the crops)."""
import json
import os
import random
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402

TOL_PX = 4.0       # A's slab and the page stroke are the same ink: their centre lines agree to a few px (0.15 sp on Brahms, 27 px/sp)


def rows_by_quantity(rec):
    r = rec.get("record", rec)
    out = defaultdict(list)
    for o in r["observations"]:
        out[o["quantity"]].append(o)
    return out


def cell_geometry(Q):
    """{cell subject: (page rect, upscale)}: the page rect from Q.CELL_BOX, the upscale from the ratio of a Q.STROKE box to its page box."""
    rect = {o["subject"]: o["value"] for o in Q["cell_box"]}
    ratios = defaultdict(list)
    for o in Q["stroke"]:
        d = o.get("detail") or {}
        b, pb = d.get("stroke_box"), d.get("bbox_page_px")
        if b and pb and pb[2] - pb[0] > 4:
            ratios["cell/" + o["subject"].split("/", 1)[1].rsplit("/", 1)[0]].append(b[2] / float(pb[2] - pb[0]))
    return {c: (rect[c], statistics.median(ratios[c])) for c in rect if ratios.get(c)}


def inter_over_min(a, b):
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy / float(min(a[2] * a[3], b[2] * b[3]))


def page_of(subject):
    return int(subject.split("/")[1])


def a_beams(Q, geo):
    """A's beam slabs (reader cv_lines) in page px, with C's thickness and cut."""
    ink = {(o.get("detail") or {}).get("beam_row_id"): o for o in Q["beam_stroke_ink"]}
    out = []
    for o in Q["beam_stroke"]:
        if o["reader"] != "cv_lines" or not isinstance(o["value"], list) or o["subject"] not in geo:
            continue
        (rx0, ry0, rx1, ry1), up = geo[o["subject"]]
        x, y, w, h = o["value"][:4]
        c = ink.get(o["id"])
        cd = (c or {}).get("detail") or {}
        out.append(dict(id=o["id"], cell=o["subject"], page=page_of(o["subject"]), box=[rx0 + x / up, ry0 + y / up, w / up, h / up],
                        c_thick=(c or {}).get("value"), cut=cd.get("cut") or "", c_detail=cd))
    return out


def dedup(rows, thr=0.8):
    """One slab per place: a beam two cells hold is read twice by A (twins)."""
    kept = []
    for r in rows:
        if not any(r["page"] == k["page"] and inter_over_min(r["box"], k["box"]) >= thr
                   and abs(r["box"][2] * r["box"][3] - k["box"][2] * k["box"][3]) < 0.3 * k["box"][2] * k["box"][3] for k in kept):
            kept.append(r)
    return kept


def centre_line_y(b, x):
    e = b["detail"].get("ends")
    if e and len(e) == 4 and e[2] != e[0]:
        return e[1] + (e[3] - e[1]) * (x - e[0]) / float(e[2] - e[0])
    return b["box"][1] + b["box"][3] / 2.0


def same_place(x, b, dy=0.0):
    """A's slab `x` sits on the page stroke `b` (moved `dy` px down): its centre lies inside b's box and on b's centre line to TOL_PX."""
    if x["page"] != b["page"]:
        return False
    cx, cy = x["box"][0] + x["box"][2] / 2.0, x["box"][1] + x["box"][3] / 2.0
    bx, by, bw, bh = b["box"]
    if not (bx <= cx <= bx + bw and by + dy - 1 <= cy <= by + dy + bh + 1):
        return False
    return abs(cy - (centre_line_y(b, cx) + dy)) <= TOL_PX


def parity(a, p, dy=0.0):
    am = [x for x in a if any(same_place(x, b, dy) for b in p)]
    pm = [b for b in p if any(same_place(x, b, dy) for x in a)]
    return dict(a=len(a), a_matched=len(am), p=len(p), p_matched=len(pm))


def bb(d):
    b = d["bbox_page_px"]
    return [b[0], b[1], b[2] - b[0], b[3] - b[1]]


def main():
    rec_path, pdf, plate, outdir = sys.argv[1:5]
    n_crops = int(sys.argv[5]) if len(sys.argv) > 5 else 12
    rec = load_record(rec_path)
    Q = rows_by_quantity(rec)
    geo = cell_geometry(Q)
    allp = [dict(box=bb(o["detail"]), role=o["value"], ord=o["detail"]["ordinal"], page=page_of(o["subject"]), detail=o["detail"]) for o in Q["page_beam"] if o["value"] != "census"]
    beams = [b for b in allp if b["role"] == "beam"]
    pstrokes = []
    seq = defaultdict(int)
    for o in Q["page_stroke"]:
        pg = page_of(o["subject"])
        pstrokes.append(dict(kind=o["value"], box=bb(o["detail"]), page=pg, ord=o["detail"]["ordinal"]))
    by_ord = {(s["page"], s["ord"]): s for s in pstrokes}
    census = [o["detail"] for o in Q["page_beam"] if o["value"] == "census"]
    A = a_beams(Q, geo)
    Au = dedup(A)
    print("PLATE", plate)
    print("census:", census)
    print("A slab rows %d (%d one per place); page beams %d; one filing per page stroke: %s" % (
        len(A), len(Au), len(beams), len({(b["page"], b["ord"]) for b in beams}) == len(beams)))
    for dy in (0.0, 6.0, 12.0):
        print("parity (same place) dy=%+g:" % dy, parity(Au, beams, dy))
    pairs = [(x, b) for x in Au for b in beams if same_place(x, b)]
    n = dis = cls = 0
    for x, b in pairs:
        if x["c_thick"] is None:
            continue
        n += 1
        t = b["detail"]["thickness_spaces"]
        dis += abs(x["c_thick"] - t) > 0.15
        cls += (x["c_thick"] >= 0.5) != (t >= 0.5)
    print("matched pairs with a C thickness %d; |C - page| > 0.15 sp: %d; one side >= 0.5 sp and the other below: %d" % (n, dis, cls))
    aonly = [x for x in Au if not any(same_place(x, b) for b in beams)]
    why = defaultdict(int)
    for x in aonly:
        roles = sorted({q["role"] for q in allp if q["page"] == x["page"] and inter_over_min(x["box"], q["box"]) >= 0.5})
        kinds = sorted({q["kind"] for q in pstrokes if q["page"] == x["page"] and inter_over_min(x["box"], q["box"]) >= 0.5})
        why[",".join(roles) or ("kinds:" + ",".join(kinds) if kinds else "no page stroke")] += 1
    print("A slabs the page does not read as a beam (%d), by what the page holds there:" % len(aonly), dict(why))
    ponly = [b for b in beams if not any(same_place(x, b) for x in Au)]
    print("page beams with no A slab at their place: %d of %d" % (len(ponly), len(beams)))
    cut = [x for x in Au if x["cut"]]
    whole = [x for x in cut if any(same_place(x, b) and b["box"][2] > 1.05 * x["box"][2] for b in beams)]
    cr = defaultdict(int)
    for x in cut:
        cr[",".join(sorted({q["role"] for q in allp if q["page"] == x["page"] and inter_over_min(x["box"], q["box"]) >= 0.5})) or "none"] += 1
    print("A slabs cut by a cell edge %d (flags %s); a longer page beam stands on them: %d; page roles under them: %s" % (
        len(cut), dict((c, sum(1 for x in cut if x["cut"] == c)) for c in sorted({x["cut"] for x in cut})), len(whole), dict(cr)))
    # the stem tips: page levels against D
    lev = {}
    for o in Q["beam_stem_levels"]:
        lev[(o.get("detail") or {}).get("stem_row_id")] = o["value"]
    page_lv = defaultdict(int)
    stem_of = {}
    for o in Q["page_beam_tip"]:
        d = o["detail"]
        for rid in d["stem_rows"]:
            if o["value"] >= page_lv[rid]:
                stem_of[rid] = (page_of(o["subject"]), d["stem"], d)
            page_lv[rid] = max(page_lv[rid], o["value"])
    dd = [(rid, page_lv[rid], lev[rid]) for rid in page_lv if rid in lev and (page_lv[rid] or lev[rid]) and page_lv[rid] != lev[rid]]
    both = sum(1 for rid in page_lv if rid in lev and (page_lv[rid] or lev[rid]))
    print("stem rows where either D or the page counts a beam: %d; the counts differ on %d" % (both, len(dd)))
    tally = defaultdict(int)
    for _r, pl, dl in dd:
        tally[(pl, dl)] += 1
    print("  (page levels, D levels) -> stems:", dict(sorted(tally.items())))

    # crops
    rnd = random.Random(2260)
    picks = []

    def take(rows, k, kind):
        rows = list(rows)
        rnd.shuffle(rows)
        for r in rows[:k]:
            picks.append((kind, r))
    take(aonly, n_crops // 4, "A reads a beam slab, the page does not")
    take(ponly, n_crops // 4, "the page reads a beam, A has no slab there")
    take(cut, n_crops // 6, "A's slab is cut by a cell edge")
    take(dd, n_crops - len(picks), "the page and D count different beam levels at a stem")
    os.makedirs(os.path.join(outdir, "tiles"), exist_ok=True)
    from tools.omr.preprocessing import render_page
    from PIL import Image, ImageDraw
    pages = {}
    sp_page = statistics.median([o["detail"]["staff_space_local_px"] for o in Q["page_stroke"] if o["detail"].get("staff_space_local_px")])
    key = []
    for i, (kind, r) in enumerate(picks):
        if isinstance(r, tuple):                       # a stem row that differs
            rid, pl, dl = r
            pg, so, d = stem_of[rid]
            bx = by_ord[(pg, so)]["box"]
            beam_boxes = [by_ord[(pg, o)]["box"] for o in d["beams"] if (pg, o) in by_ord]
            target = beam_boxes[0] if beam_boxes else [bx[0] - 0.3 * sp_page, bx[1] if d["end"] == "top" else bx[1] + bx[3], bx[2] + 0.6 * sp_page, 0.6 * sp_page]
            about = dict(stem=so, end=d["end"], page_levels=pl, D_levels=dl)
            cx0, cx1 = min(target[0], bx[0]), max(target[0] + target[2], bx[0] + bx[2])
            cy0, cy1 = min(target[1], bx[1]), max(target[1] + target[3], bx[1] + bx[3])
        else:
            pg = r["page"]
            target = r["box"]
            about = dict(role=r.get("role"), c_thickness=r.get("c_thick"), cut=r.get("cut"))
            cx0, cx1, cy0, cy1 = target[0], target[0] + target[2], target[1], target[1] + target[3]
            for s in (r.get("detail") or {}).get("stems") or ():
                if (pg, s) in by_ord:
                    sb = by_ord[(pg, s)]["box"]
                    cx0, cx1 = min(cx0, sb[0]), max(cx1, sb[0] + sb[2])
                    cy0, cy1 = min(cy0, sb[1]), max(cy1, sb[1] + sb[3])
        if pg not in pages:
            pages[pg] = Image.fromarray(render_page(pdf, pg, dpi=600).rgb).convert("RGB")
        im = pages[pg]
        pad = 3.0 * sp_page
        x0, y0 = int(max(0, cx0 - pad)), int(max(0, cy0 - pad))
        x1, y1 = int(min(im.width, cx1 + pad)), int(min(im.height, cy1 + pad))
        if x1 - x0 > 1100:                             # never wider than the tile: keep the target centred
            mid = target[0] + target[2] / 2.0
            x0, x1 = int(max(0, mid - 550)), int(min(im.width, mid + 550))
        crop = im.crop((x0, y0, x1, y1))
        dr = ImageDraw.Draw(crop)
        dr.rectangle([target[0] - x0 - 2, target[1] - y0 - 2, target[0] + target[2] - x0 + 2, target[1] + target[3] - y0 + 2], outline=(0, 160, 0), width=2)
        name = "m4a_%s_%02d.png" % (plate, i + 1)
        crop.save(os.path.join(outdir, "tiles", name))
        key.append(dict(tile=name, plate=plate, page=pg, why=kind, crop_page_px=[x0, y0, x1, y1], box_page_px=[round(v, 1) for v in target], **about))
    with open(os.path.join(outdir, "key_%s.json" % plate), "w") as f:
        json.dump(key, f, indent=1)
    print("crops:", len(key), "->", os.path.join(outdir, "tiles"))


if __name__ == "__main__":
    main()
