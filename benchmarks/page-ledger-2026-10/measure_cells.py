"""ROADMAP 2.240 -- cells are views, the page is the ledger: MEASURE the cut (STAGED GATHER geometry; read-only).

Per page of the 20261029-night frozen-sample slices, on the master cell map (the same cells the overnight cut):
  A. vertical: page area and stroke ink seen by two or more cells, split by who the cells are (adjacent staves of one system,
     staves of two systems, same staff) and by where the ink stands (inside the OTHER staff's five lines / in the gap).
  B. horizontal: overlap between cells of one staff (expected 0: no x pad); per (staff, barline) the local rule's x against the
     system's one cut x (tilt), the rule ink left/right of the cut, the rule ink outside the +-0.45 sp barline claim, the non-rule ink
     standing between the cut and the local rule (filed in the wrong bar by the tilt), and ink rows continuous across the rule
     (straddling marks: ties, slurs, hairpins, beams) -- each such run is cut in two cells.
  C. detector boxes (record rows, page px): same-class pairs from two staves' cells at IoU >= 0.5 (one mark boxed twice by two
     views), and boxes flush with a cell's top/bottom (vertical crop) or left/right (barline cut) edge, by class.

Usage: python3 benchmarks/page-ledger-2026-10/measure_cells.py litolff|brahms [--pages 4,8] [--out DIR]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import claim_readout as CR  # noqa: E402
from tools.omr.staged import cell_map as CM  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402

SLICES = CR.RECORDS / "lane-report-slices-20261029-night"


def glyph_rows(src: pathlib.Path, pages):
    """glyph_box rows (page px) and cell_box rows, per page."""
    boxes = collections.defaultdict(list)
    cells = {}
    want = set(pages)
    with open(src / "observations.jsonl") as fh:
        for line in fh:
            if '"quantity": "glyph_box"' in line[:200]:
                r = json.loads(line)
                p = r["subject"].split("/")
                pg = int(p[1])
                if pg in want:
                    bb = (r.get("detail") or {}).get("bbox_page_px")
                    if bb:
                        boxes[pg].append((int(p[2]), int(p[3]), int(p[4]), r["value"][0], bb))
            elif '"quantity": "cell_box"' in line[:200]:
                r = json.loads(line)
                p = r["subject"].split("/")
                if int(p[1]) in want:
                    cells[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))] = r["value"]
    return boxes, cells


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def page_strokes(pws, cells):
    """Per cell: (page rect, bool 'a stroke stands here' in page px). Same stroke map call as claim_readout.build_page."""
    out = []
    for c in cells:
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        x0, y0, x1, y1 = (int(v) for v in c.bbox_page_px)
        if grid is None or img is None:
            out.append((c, (x0, y0, x1, y1), None))
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None))
        if not res or not res.strokes:
            out.append((c, (x0, y0, x1, y1), np.zeros((max(1, y1 - y0), max(1, x1 - x0)), bool)))
            continue
        s = res.scale
        hr, wr = int(round(img.shape[0] * s)), int(round(img.shape[1] * s))
        lab = np.zeros((hr, wr), np.int16)
        for i, (m, mx0, my0) in enumerate(res.masks):
            mh, mw = m.shape
            yy1, xx1 = min(hr, my0 + mh), min(wr, mx0 + mw)
            if yy1 > my0 and xx1 > mx0:
                sub = lab[my0:yy1, mx0:xx1]
                sub[m[:yy1 - my0, :xx1 - mx0]] = i + 1
        seen = CR.sample_to_rect(CR.fill_labels(lab), x1 - x0, y1 - y0) > 0
        out.append((c, (x0, y0, x1, y1), seen))
    return out


def measure_page(pdf, page, boxes, cell_rows):
    (pws, cells), = CM.load_prepared(pdf, [page], root=CM.ROOT_DEFAULT)
    ink = pws.page.binary == 0
    H, W = ink.shape
    staves = {s.staff_index: s for s in pws.staves}
    sys_of = {}
    for s in pws.staves:
        sys_of[s.staff_index] = getattr(s, "system_index", None)
    for c in cells:
        sys_of.setdefault(c.staff_index, c.system_index)
    r = collections.Counter()
    # ---------------- A. vertical overlap ----------------
    area_n = np.zeros((H, W), np.uint8)
    seen_n = np.zeros((H, W), np.uint8)
    st_lo = np.full((H, W), 255, np.uint8)
    st_hi = np.zeros((H, W), np.uint8)
    me_lo = np.full((H, W), 65535, np.uint16)
    me_hi = np.zeros((H, W), np.uint16)
    sy_lo = np.full((H, W), 255, np.uint8)
    sy_hi = np.zeros((H, W), np.uint8)
    stroke_sum = 0
    for c, (x0, y0, x1, y1), seen in page_strokes(pws, cells):
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        sl = (slice(cy0, cy1), slice(cx0, cx1))
        area_n[sl] = np.minimum(area_n[sl].astype(np.int16) + 1, 255).astype(np.uint8)
        si, mi, yi = int(c.staff_index), int(c.measure_index) + 1000 * int(c.system_index), int(c.system_index)
        st_lo[sl] = np.minimum(st_lo[sl], si)
        st_hi[sl] = np.maximum(st_hi[sl], si)
        me_lo[sl] = np.minimum(me_lo[sl], mi)
        me_hi[sl] = np.maximum(me_hi[sl], mi)
        sy_lo[sl] = np.minimum(sy_lo[sl], yi)
        sy_hi[sl] = np.maximum(sy_hi[sl], yi)
        if seen is not None:
            sv = seen[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0] & ink[sl]
            seen_n[sl] = np.minimum(seen_n[sl].astype(np.int16) + sv, 255).astype(np.uint8)
            stroke_sum += int(sv.sum())
    incell = area_n > 0
    r["ink_px"] = int(ink.sum())
    r["ink_in_cells_px"] = int((ink & incell).sum())
    r["area_in_cells_px"] = int(incell.sum())
    r["area_seen_twice_px"] = int((area_n >= 2).sum())
    r["ink_in_area_seen_twice_px"] = int((ink & (area_n >= 2)).sum())
    r["stroke_px_sum_over_cells"] = stroke_sum
    r["stroke_px_page"] = int((seen_n > 0).sum())
    dbl = seen_n >= 2
    r["stroke_px_seen_2plus"] = int(dbl.sum())
    r["stroke_px_extra_copies"] = int(seen_n[seen_n >= 2].astype(np.int64).sum() - dbl.sum())
    two_staves = dbl & (st_lo != st_hi)
    r["dbl_two_staves"] = int(two_staves.sum())
    r["dbl_two_systems"] = int((dbl & (sy_lo != sy_hi)).sum())
    r["dbl_same_staff_two_bars"] = int((dbl & (st_lo == st_hi) & (me_lo != me_hi)).sum())
    r["area_same_staff_two_bars"] = int(((area_n >= 2) & (st_lo == st_hi) & (me_lo != me_hi)).sum())
    # where the twice-seen ink stands: inside some staff's own five lines (+-0.5 sp), or in a gap
    band = np.zeros((H, W), bool)
    for s in pws.staves:
        sp = float(s.line_spacing_px)
        a, b = max(0, int(s.top_y - 0.5 * sp)), min(H, int(s.bottom_y + 0.5 * sp) + 1)
        band[a:b, max(0, int(s.x_start)):min(W, int(s.x_end) + 1)] = True
    r["dbl_inside_a_staff_band"] = int((dbl & band).sum())
    r["dbl_in_gap"] = int((dbl & ~band).sum())
    del area_n, seen_n, st_lo, st_hi, me_lo, me_hi, sy_lo, sy_hi, band, two_staves
    # ---------------- B. horizontal: the barline cut ----------------
    raw = ink
    from tools.omr.staged import arcs_system as AS
    er = AS.composite_ink(pws.page.binary, cells)       # staff lines removed wherever a cell covers (AND of the cells' erased ink)
    tilt_rows = []
    straddle_items = []
    for bl in pws.barlines:
        sys_staves = sorted([s for s in pws.staves if sys_of.get(s.staff_index) == bl.system_index], key=lambda s: s.top_y)
        if not sys_staves:
            continue
        x = int(bl.x)
        x_lo_sys = float(np.median([s.x_start for s in sys_staves]))
        if x - x_lo_sys < 4.0 * float(np.median([s.line_spacing_px for s in sys_staves])):
            continue                            # header column: no cut there
        cut_here = any(c.system_index == bl.system_index and int(c.bbox_page_px[0]) == x for c in cells)
        if not cut_here:
            continue
        for s in sys_staves:
            sp = float(s.line_spacing_px)
            rows = np.arange(int(s.top_y), int(s.bottom_y) + 1)
            line_rows = set()
            for ly in s.line_ys:
                for d in range(-3, 4):
                    line_rows.add(int(ly) + d)
            rows = np.array([y for y in rows if y not in line_rows])
            if rows.size < 5:
                continue
            w = int(round(1.5 * sp))
            a, b = max(0, x - w), min(W, x + w + 1)
            frac = raw[rows][:, a:b].mean(axis=0)
            rule_cols = np.where(frac >= 0.8)[0]
            r["staff_bar_pairs"] += 1
            if rule_cols.size == 0:
                r["staff_bar_no_local_rule"] += 1
                continue
            # the run of rule columns nearest x
            runs, start = [], rule_cols[0]
            for p_, q_ in zip(rule_cols[:-1], rule_cols[1:]):
                if q_ != p_ + 1:
                    runs.append((start, p_))
                    start = q_
            runs.append((start, rule_cols[-1]))
            lo, hi = min(runs, key=lambda ab: min(abs(ab[0] + a - x), abs(ab[1] + a - x)))
            L, R = lo + a, hi + a                        # inclusive page columns of the local rule on this staff
            centre = (L + R) / 2.0
            off = (centre - x) / sp
            tilt_rows.append(off)
            yy0, yy1 = int(s.top_y), int(s.bottom_y) + 1
            rule_ink = raw[yy0:yy1, L:R + 1]
            n_rule = int(rule_ink.sum())
            left_of_cut = int(raw[yy0:yy1, L:min(R + 1, x)].sum()) if L < x else 0
            r["rule_px"] += n_rule
            r["rule_px_left_of_cut"] += left_of_cut
            if 0 < left_of_cut < n_rule:
                r["staff_bar_rule_split_by_cut"] += 1
            elif left_of_cut == n_rule:
                r["staff_bar_rule_wholly_in_left_bar"] += 1
            # claim area +-0.45 sp at the system x
            ca, cb = int(round(x - 0.45 * sp)), int(round(x + 0.45 * sp))
            outside = int(raw[yy0:yy1, L:R + 1].sum() - raw[yy0:yy1, max(L, ca):min(R, cb) + 1].sum()) if cb >= L and ca <= R else n_rule
            r["rule_px_outside_claim"] += max(0, outside)
            if outside > 0:
                r["staff_bar_rule_partly_outside_claim"] += 1
            # non-rule ink between the cut and the rule (filed in the other bar by the tilt): staff band +-4 sp, staff lines excluded
            ya, yb = max(0, int(s.top_y - 4 * sp)), min(H, int(s.bottom_y + 4 * sp) + 1)
            keep = np.ones(yb - ya, bool)
            for y_ in line_rows:
                if ya <= y_ < yb:
                    keep[y_ - ya] = False
            if L > x:            # rule right of the cut: the sliver [x, L) is in the right cell, ink there that stands LEFT of the rule
                sliver = raw[ya:yb, x:L][keep]
            elif R < x - 1:      # rule left of the cut: the sliver (R, x) is in the left cell, ink there stands RIGHT of the rule
                sliver = raw[ya:yb, R + 1:x][keep]
            else:
                sliver = np.zeros((0,), bool)
            n_sl = int(sliver.sum())
            r["wrong_side_px"] += n_sl
            if n_sl >= 0.3 * sp * sp:
                r["staff_bar_wrong_side_ink"] += 1
            # straddle: rows in the staff +-4 sp band (off the staff lines) with ink both 2 px left of L and 2 px right of R
            # AND across the rule (continuous through it)
            la, ra = L - 3, R + 3
            if la < 0 or ra >= W:
                continue
            if frac[max(0, la - a)] >= 0.5 or frac[min(len(frac) - 1, ra - a)] >= 0.5:
                r["staff_bar_double_rule"] += 1       # a thick-thin / double barline: the next column is a rule too
                continue
            lft = er[ya:yb, la] & er[ya:yb, la + 1]
            rgt = er[ya:yb, ra] & er[ya:yb, ra - 1]
            thru = er[ya:yb, L:R + 1].all(axis=1)
            st = lft & rgt & thru & keep
            ys = np.where(st)[0]
            if ys.size:
                groups = np.split(ys, np.where(np.diff(ys) > 2)[0] + 1)
                for g in groups:
                    yc = ya + int(g.mean())
                    inside = s.top_y - 0.5 * sp <= yc <= s.bottom_y + 0.5 * sp
                    r["straddles_in_staff" if inside else "straddles_off_staff"] += 1
                    straddle_items.append({"page": page, "staff": int(s.staff_index), "system": int(bl.system_index), "x": x,
                                           "y": yc, "rows": int(len(g)), "inside": bool(inside), "sp": sp})
    if tilt_rows:
        t = np.abs(np.array(tilt_rows))
        r["tilt_n"] = len(t)
        r["tilt_ge_0.25sp"] = int((t >= 0.25).sum())
        r["tilt_ge_0.45sp"] = int((t >= 0.45).sum())
        r["tilt_max_x1000"] = int(1000 * t.max())
        r["tilt_med_x1000"] = int(1000 * np.median(t))
    # ---------------- C. detector boxes ----------------
    bx = boxes.get(page, [])
    by_cls = collections.defaultdict(list)
    for sy, st_, ce, cls, bb in bx:
        by_cls[cls].append((sy, st_, ce, bb))
    twin_cls = collections.Counter()
    for cls, lst in by_cls.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a_, b_ = lst[i], lst[j]
                if (a_[0], a_[1]) == (b_[0], b_[1]):
                    continue
                if iou(a_[3], b_[3]) >= 0.5:
                    twin_cls[cls] += 1
    edge_v = collections.Counter()
    edge_h = collections.Counter()
    for sy, st_, ce, cls, bb in bx:
        cb = cell_rows.get((page, sy, st_, ce))
        if cb is None:
            continue
        if bb[1] <= cb[1] + 1.5 or bb[3] >= cb[3] - 1.5:
            edge_v[cls] += 1
        if bb[0] <= cb[0] + 1.5 or bb[2] >= cb[2] - 1.5:
            edge_h[cls] += 1
    r["boxes"] = len(bx)
    r["box_twins_two_staves"] = sum(twin_cls.values())
    r["_straddles"] = straddle_items
    return r, twin_cls, edge_v, edge_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plate", choices=["litolff", "brahms"])
    ap.add_argument("--pages", default=None)
    ap.add_argument("--out", default=str(ROOT / "benchmarks/page-ledger-2026-10/out"))
    a = ap.parse_args()
    src = SLICES / a.plate
    pages = [int(p) for p in a.pages.split(",")] if a.pages else CR.slice_pages(src)
    rows = CR.read_rows(src, pages[:1])
    pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
    del rows
    boxes, cell_rows = glyph_rows(src, pages)
    tot = collections.Counter()
    twins = collections.Counter()
    ev = collections.Counter()
    eh = collections.Counter()
    per = {}
    per_straddles = []
    for pg in pages:
        t0 = time.time()
        r, tw, v, h = measure_page(pdf, pg, boxes, cell_rows)
        per[pg] = dict(r)
        strad = r.pop("_straddles")
        per_straddles.extend(strad)
        for k, val in r.items():
            if not k.startswith("tilt_m"):
                tot[k] += val
        tot["tilt_max_x1000"] = max(tot.get("tilt_max_x1000", 0), r.get("tilt_max_x1000", 0))
        twins.update(tw)
        ev.update(v)
        eh.update(h)
        print("page %d done %.0fs: dbl strokes %d of %d (%s)" % (pg, time.time() - t0, r["stroke_px_seen_2plus"], r["stroke_px_page"],
                                                                 {k: r[k] for k in ("dbl_two_staves", "dbl_same_staff_two_bars", "straddles_off_staff", "tilt_ge_0.45sp")}), flush=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = {"plate": a.plate, "pages": pages, "total": dict(tot), "per_page": per, "box_twins_by_class": dict(twins.most_common()),
           "boxes_flush_top_bottom_by_class": dict(ev.most_common()), "boxes_flush_left_right_by_class": dict(eh.most_common()), "straddles": per_straddles}
    (out / ("%s.json" % a.plate)).write_text(json.dumps(rep, indent=1))
    print(json.dumps({"total": dict(tot), "twins_top": twins.most_common(12), "edge_v_top": ev.most_common(12),
                      "edge_h_top": eh.most_common(12)}, indent=1))


if __name__ == "__main__":
    main()
