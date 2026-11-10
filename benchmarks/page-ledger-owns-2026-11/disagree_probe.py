"""2.284 step 1(c): CROSS-CELL OWNER DISAGREEMENT. STAGED, read only (files no row).

Per page pixel, which owner each padded cell's `stroke_owner` verdict names for the stroke standing on it. The cells are re-cut from the
master cell map and matched stroke for stroke to the record exactly as `claim_readout.build_page` does (a mismatched cell is dropped and
counted). A cell's label for a stroke: the owner FAMILY (decided / merged), `contested`, or `none` (unclaimed / refused claims).

    multi      ink px a stroke of two or more cells stands on (the same page ink seen twice)
    disagree   of those, px where two cells' labels differ (any: family vs family, family vs none, family vs contested)
    fam_fam    of those, px where two cells name two DIFFERENT owner families (the hard case: two owners of one ink)
    own_none   px where one cell names an owner and another names none (one cell's claim invisible to the other)

Denominator: the page's dark ink outside the staff lines the erasers took (`claim_readout`'s non-staff ink).

    python3 benchmarks/page-ledger-owns-2026-11/disagree_probe.py SLICE_OR_RECORD [--pages 0] [--env NAME=V] [--out JSON]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import claim_readout as CR  # noqa: E402


def page_disagreement(rows, pdf, page, cm_root, env=None, keep=False):
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import gather as G
    from tools.omr.staged import stroke_map as SM
    prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, page)] for k, v in rows.items()}
    verdicts = CR.owner_verdicts(prows, env)
    rec_boxes = collections.defaultdict(dict)
    keep_whole, touch = {}, {}
    for o in prows["observations"]:
        if o.get("quantity") == "stroke":
            p = o["subject"].split("/")
            g = int(p[5])
            if g >= CR.STROKE_BASE:
                ck = CR.cell_key(o["subject"])
                rec_boxes[ck][g - CR.STROKE_BASE] = (o.get("detail") or {}).get("stroke_box")
                d = o.get("detail") or {}
                if d.get("cell_keep_whole"):
                    keep_whole[ck] = d["cell_keep_whole"]
                if d.get("cell_touch_boxes"):
                    touch[ck] = d["cell_touch_boxes"]
    (pws, cells), = CM.load_prepared(pdf, [page], root=cm_root)
    ink = pws.page.binary == 0
    H, W = ink.shape
    codes = {"none": 1, "contested": 2}
    first = np.zeros((H, W), np.int16)          # the first cell's label code on the pixel (0 = no stroke yet)
    nseen = np.zeros((H, W), np.uint8)
    dis = np.zeros((H, W), bool)
    famfam = np.zeros((H, W), bool)
    ownnone = np.zeros((H, W), bool)
    staff = np.zeros((H, W), bool)
    pair = collections.Counter()
    verify = collections.Counter()
    local = G._system_local(pws.staves)
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None:
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None),
                             keep_whole=keep_whole.get(ck, ()), touch_boxes=touch.get(ck, ()))
        mine = {i: list(s.box) for i, s in enumerate(res.strokes)} if res else {}
        if mine != {i: list(b) for i, b in rec_boxes.get(ck, {}).items()}:
            verify["cells_mismatch"] += 1
            continue
        verify["cells_ok"] += 1
        if not mine:
            continue
        vs = (verdicts.get(ck) or {}).get("strokes") or {}
        n = len(res.strokes) + 1
        code_t = np.zeros(n, np.int16)
        for o in range(len(res.strokes)):
            ent = vs.get(str(o))
            st, fam = (ent[0], ent[1]) if ent else ("unclaimed", None)
            lab_ = fam if st in ("decided", "merged") and fam else ("contested" if st == "contested" else "none")
            if lab_ not in codes:
                codes[lab_] = len(codes) + 1
            code_t[o + 1] = codes[lab_]
        s = res.scale
        hr, wr = int(round(img.shape[0] * s)), int(round(img.shape[1] * s))
        lab = np.zeros((hr, wr), np.int16)
        for i, (m, x0, y0) in enumerate(res.masks):
            mh, mw = m.shape
            y1, x1 = min(hr, y0 + mh), min(wr, x0 + mw)
            if y1 > y0 and x1 > x0:
                sub = lab[y0:y1, x0:x1]
                sub[m[:y1 - y0, :x1 - x0]] = i + 1
        x0, y0, x1, y1 = (int(v) for v in c.bbox_page_px)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            continue
        L = CR.sample_to_rect(CR.fill_labels(lab), w, h)
        cc = code_t[L]
        sl = (slice(y0, y1), slice(x0, x1))
        f = first[sl]
        both = (cc > 0) & (f > 0)
        diff = both & (cc != f)
        fam_a = f >= 3
        fam_b = cc >= 3
        dis[sl] |= diff
        famfam[sl] |= diff & fam_a & fam_b
        ownnone[sl] |= diff & ((fam_a & (cc == 1)) | (fam_b & (f == 1)))
        inv = {v: k for k, v in codes.items()}
        if diff.any():
            ii = ink[sl] & diff
            if ii.any():
                a, b = f[ii], cc[ii]
                for (u, v), k in collections.Counter(zip(a.tolist(), b.tolist())).items():
                    pair[tuple(sorted((inv[u], inv[v])))] += k
        first[sl] = np.where((f == 0) & (cc > 0), cc, f)
        nseen[sl] = np.minimum(nseen[sl].astype(np.int16) + (cc > 0), 255).astype(np.uint8)
        raw = getattr(c, "binary", None)
        if raw is not None:
            er = (raw == 0) & (img != 0)
            staff[sl] |= CR.sample_to_rect(er.astype(np.uint8), w, h).astype(bool)
    base = ink & ~staff
    out = {
        "page": page, "verify": dict(verify), "ink_nonstaff_px": int(base.sum()),
        "stroke_px": int((base & (nseen > 0)).sum()),
        "multi_px": int((base & (nseen >= 2)).sum()),
        "disagree_px": int((base & dis).sum()),
        "fam_fam_px": int((base & famfam).sum()),
        "own_none_px": int((base & ownnone).sum()),
        "pairs": {"%s|%s" % k: v for k, v in pair.most_common(15)},
    }
    if keep:
        out["_masks"] = {"dis": base & dis, "famfam": base & famfam}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    src = CR.resolve_source(a.rec)
    if src.suffix == ".json":
        src = CR.cut_record(src)
    pages = [int(p) for p in a.pages.split(",")] if a.pages else CR.slice_pages(src)
    rows = CR.read_rows(src, pages)
    pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
    env = CR.parse_env(a.env)
    res = []
    for pg in pages:
        r = page_disagreement(rows, pdf, pg, CR.RECORDS / "cell-maps", env)
        b = max(1, r["ink_nonstaff_px"])
        print("p%d  ink %d  multi %.2f%%  DISAGREE %.2f%%  fam-vs-fam %.2f%%  owner-vs-none %.2f%%  cells %s" % (
            pg, r["ink_nonstaff_px"], 100 * r["multi_px"] / b, 100 * r["disagree_px"] / b, 100 * r["fam_fam_px"] / b,
            100 * r["own_none_px"] / b, r["verify"]))
        for k, v in r["pairs"].items():
            print("     %-28s %8d px  %.2f%%" % (k, v, 100 * v / b))
        res.append(r)
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
